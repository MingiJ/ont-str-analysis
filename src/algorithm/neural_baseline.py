#!/usr/bin/env python3
"""Train a small NumPy neural repeat-count regressor on signal windows.

This is the first neural prototype for the new algorithm pipeline. It avoids
large ML-framework dependencies for now and trains a one-hidden-layer MLP over
summary plus temporal pooled signal features.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np

try:
    from dataset import (
        DEFAULT_HOLDOUT_SAMPLE,
        DEFAULT_INDEX,
        DEFAULT_SIGNAL_ARCHIVE,
        combined_signal_features,
        load_signal_dataset,
        split_dataset,
    )
except ImportError:  # pragma: no cover - allows module execution with -m
    from .dataset import (
        DEFAULT_HOLDOUT_SAMPLE,
        DEFAULT_INDEX,
        DEFAULT_SIGNAL_ARCHIVE,
        combined_signal_features,
        load_signal_dataset,
        split_dataset,
    )


DEFAULT_PREDICTIONS = Path("ont-str-runner/work/analysis/neural_baseline_predictions.tsv")
DEFAULT_SUMMARY = Path("ont-str-runner/work/analysis/neural_baseline_summary.tsv")
PREDICTION_FIELDS = ["sample", "read_id", "label", "target", "prediction", "split"]
SUMMARY_FIELDS = ["metric", "value"]


@dataclass
class MLPParams:
    w1: np.ndarray
    b1: np.ndarray
    w2: np.ndarray
    b2: np.ndarray


@dataclass
class AdamState:
    mw1: np.ndarray
    vw1: np.ndarray
    mb1: np.ndarray
    vb1: np.ndarray
    mw2: np.ndarray
    vw2: np.ndarray
    mb2: np.ndarray
    vb2: np.ndarray


def validation_split(labels: np.ndarray, train: np.ndarray, validation_fraction: float) -> tuple[np.ndarray, np.ndarray]:
    fit = train.copy()
    validation = np.zeros(labels.shape[0], dtype=np.bool_)
    if validation_fraction <= 0.0:
        return fit, validation
    for label in sorted(set(labels[train])):
        idx = np.flatnonzero(train & (labels == label))
        if idx.size < 2:
            continue
        val_count = max(1, int(round(idx.size * validation_fraction)))
        val_count = min(val_count, idx.size - 1)
        chosen = idx[-val_count:]
        validation[chosen] = True
        fit[chosen] = False
    return fit, validation


def label_weights(labels: np.ndarray) -> np.ndarray:
    counts = Counter(labels)
    weights = np.asarray([1.0 / counts[label] for label in labels], dtype=np.float32)
    return weights / weights.mean()


def standardize(train: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mean = train.mean(axis=0)
    std = train.std(axis=0)
    std[std < 1e-6] = 1.0
    return (train - mean) / std, (values - mean) / std, mean, std


def init_params(input_dim: int, hidden_dim: int, rng: np.random.Generator) -> MLPParams:
    w1 = rng.normal(0.0, np.sqrt(2.0 / input_dim), size=(input_dim, hidden_dim)).astype(np.float32)
    b1 = np.zeros(hidden_dim, dtype=np.float32)
    w2 = rng.normal(0.0, np.sqrt(2.0 / hidden_dim), size=(hidden_dim, 1)).astype(np.float32)
    b2 = np.zeros(1, dtype=np.float32)
    return MLPParams(w1=w1, b1=b1, w2=w2, b2=b2)


def init_adam(params: MLPParams) -> AdamState:
    return AdamState(
        mw1=np.zeros_like(params.w1),
        vw1=np.zeros_like(params.w1),
        mb1=np.zeros_like(params.b1),
        vb1=np.zeros_like(params.b1),
        mw2=np.zeros_like(params.w2),
        vw2=np.zeros_like(params.w2),
        mb2=np.zeros_like(params.b2),
        vb2=np.zeros_like(params.b2),
    )


def copy_params(params: MLPParams) -> MLPParams:
    return MLPParams(w1=params.w1.copy(), b1=params.b1.copy(), w2=params.w2.copy(), b2=params.b2.copy())


def forward(params: MLPParams, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    hidden_pre = x @ params.w1 + params.b1
    hidden = np.maximum(hidden_pre, 0.0)
    pred = (hidden @ params.w2 + params.b2).ravel()
    return hidden, pred


def weighted_mse(pred: np.ndarray, target: np.ndarray, weights: np.ndarray) -> float:
    err = pred - target
    return float(np.mean(weights * err * err))


def train_epoch(params: MLPParams, state: AdamState, x: np.ndarray, y: np.ndarray, weights: np.ndarray, lr: float, step: int, weight_decay: float) -> float:
    hidden, pred = forward(params, x)
    err = pred - y
    scale = (2.0 * weights * err / x.shape[0]).astype(np.float32)

    grad_w2 = hidden.T @ scale.reshape(-1, 1) + weight_decay * params.w2
    grad_b2 = np.asarray([scale.sum()], dtype=np.float32)
    grad_hidden = scale.reshape(-1, 1) @ params.w2.T
    grad_hidden[hidden <= 0.0] = 0.0
    grad_w1 = x.T @ grad_hidden + weight_decay * params.w1
    grad_b1 = grad_hidden.sum(axis=0)

    adam_update(params, state, grad_w1, grad_b1, grad_w2, grad_b2, lr, step)
    return weighted_mse(pred, y, weights)


def adam_update(params: MLPParams, state: AdamState, grad_w1: np.ndarray, grad_b1: np.ndarray, grad_w2: np.ndarray, grad_b2: np.ndarray, lr: float, step: int) -> None:
    beta1 = 0.9
    beta2 = 0.999
    eps = 1e-8

    for name, grad in (("w1", grad_w1), ("b1", grad_b1), ("w2", grad_w2), ("b2", grad_b2)):
        param = getattr(params, name)
        m = getattr(state, f"m{name}")
        v = getattr(state, f"v{name}")
        m *= beta1
        m += (1.0 - beta1) * grad
        v *= beta2
        v += (1.0 - beta2) * grad * grad
        m_hat = m / (1.0 - beta1**step)
        v_hat = v / (1.0 - beta2**step)
        param -= lr * m_hat / (np.sqrt(v_hat) + eps)


def mae(values: np.ndarray) -> float:
    return float(np.mean(np.abs(values))) if values.size else float("nan")


def write_predictions(path: Path, metadata: list[dict[str, str]], labels: np.ndarray, targets: np.ndarray, predictions: np.ndarray, train: np.ndarray, test: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PREDICTION_FIELDS, delimiter="\t")
        writer.writeheader()
        for idx, row in enumerate(metadata):
            split = "train" if train[idx] else "test" if test[idx] else "unlabeled"
            writer.writerow(
                {
                    "sample": row.get("sample", ""),
                    "read_id": row.get("read_id", ""),
                    "label": labels[idx],
                    "target": "" if np.isnan(targets[idx]) else f"{targets[idx]:.3f}",
                    "prediction": f"{predictions[idx]:.3f}",
                    "split": split,
                }
            )


def write_summary(path: Path, metrics: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS, delimiter="\t")
        writer.writeheader()
        for key, value in metrics.items():
            writer.writerow({"metric": key, "value": value})


def summarize_by_sample(metadata: list[dict[str, str]], predictions: np.ndarray) -> dict[str, str]:
    grouped: dict[str, list[int]] = defaultdict(list)
    for row, pred in zip(metadata, predictions):
        grouped[row.get("sample", "")].append(int(round(float(pred))))
    return {
        f"sample_{sample}_top_rounded_predictions": ";".join(f"{value}:{count}" for value, count in Counter(calls).most_common(5))
        for sample, calls in grouped.items()
    }


def add_group_metrics(metrics: dict[str, object], prefix: str, metadata: list[dict[str, str]], labels: np.ndarray, targets: np.ndarray, predictions: np.ndarray, mask: np.ndarray) -> None:
    for label in sorted(set(labels[mask])):
        idx = mask & (labels == label)
        metrics[f"{prefix}_mae_{label}"] = f"{mae(predictions[idx] - targets[idx]):.3f}"

    samples = np.asarray([row.get("sample", "") for row in metadata])
    for sample in sorted(set(samples[mask])):
        idx = mask & (samples == sample)
        metrics[f"{prefix}_sample_{sample}_mae"] = f"{mae(predictions[idx] - targets[idx]):.3f}"
        metrics[f"{prefix}_sample_{sample}_rows"] = int(idx.sum())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train NumPy neural repeat-count baseline on signal windows.")
    parser.add_argument("--signal-archive", type=Path, default=DEFAULT_SIGNAL_ARCHIVE)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--bins", type=int, default=128)
    parser.add_argument("--hidden-dim", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=250)
    parser.add_argument("--learning-rate", type=float, default=0.01)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument(
        "--split",
        choices=("heldout-sample", "random-read"),
        default="heldout-sample",
        help="heldout-sample prevents same-sample reads from leaking into test.",
    )
    parser.add_argument("--holdout-sample", default=DEFAULT_HOLDOUT_SAMPLE)
    parser.add_argument("--train-fraction", type=float, default=0.8)
    parser.add_argument("--validation-fraction", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--no-balance", action="store_true", help="Disable inverse-label weighting.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.bins < 2:
        raise SystemExit("--bins must be at least 2")
    if args.hidden_dim < 1:
        raise SystemExit("--hidden-dim must be at least 1")

    dataset = load_signal_dataset(args.signal_archive, args.index)
    train, test = split_dataset(dataset, args.split, args.train_fraction, args.holdout_sample)
    if not np.any(train):
        raise SystemExit("No labeled training rows found.")
    if not np.any(test):
        raise SystemExit("No labeled test rows found.")
    fit, validation = validation_split(dataset.label, train, args.validation_fraction)
    if not np.any(fit):
        raise SystemExit("No labeled fitting rows found after validation split.")

    features, feature_names = combined_signal_features(dataset, args.bins)
    fit_features, all_features, _, _ = standardize(features[fit], features)
    fit_weights = np.ones(int(fit.sum()), dtype=np.float32) if args.no_balance else label_weights(dataset.label[fit])

    rng = np.random.default_rng(args.seed)
    params = init_params(features.shape[1], args.hidden_dim, rng)
    state = init_adam(params)
    losses = []
    best_params = copy_params(params)
    best_epoch = 0
    best_validation_mae = float("inf")
    for epoch in range(1, args.epochs + 1):
        loss = train_epoch(params, state, fit_features.astype(np.float32), dataset.target[fit], fit_weights, args.learning_rate, epoch, args.weight_decay)
        losses.append(loss)

        if np.any(validation):
            _, current_predictions = forward(params, all_features.astype(np.float32))
            current_validation_mae = mae(current_predictions[validation] - dataset.target[validation])
        else:
            current_validation_mae = loss
        if current_validation_mae < best_validation_mae:
            best_validation_mae = current_validation_mae
            best_epoch = epoch
            best_params = copy_params(params)

    _, predictions = forward(best_params, all_features.astype(np.float32))
    train_errors = predictions[train] - dataset.target[train]
    test_errors = predictions[test] - dataset.target[test]
    metrics: dict[str, object] = {
        "rows_total": dataset.signal.shape[0],
        "rows_labeled": int(dataset.target_mask.sum()),
        "rows_train": int(train.sum()),
        "rows_fit": int(fit.sum()),
        "rows_validation": int(validation.sum()),
        "rows_test": int(test.sum()),
        "split": args.split,
        "holdout_sample": args.holdout_sample if args.split == "heldout-sample" else "",
        "balanced_training": str(not args.no_balance),
        "bins": args.bins,
        "feature_dim": features.shape[1],
        "feature_names": ",".join(feature_names),
        "hidden_dim": args.hidden_dim,
        "epochs": args.epochs,
        "learning_rate": args.learning_rate,
        "weight_decay": args.weight_decay,
        "seed": args.seed,
        "initial_train_loss": f"{losses[0]:.3f}",
        "final_train_loss": f"{losses[-1]:.3f}",
        "best_epoch": best_epoch,
        "validation_mae_at_best_epoch": f"{best_validation_mae:.3f}",
        "train_mae": f"{mae(train_errors):.3f}",
        "test_mae": f"{mae(test_errors):.3f}",
        "label_counts": ";".join(f"{k}:{v}" for k, v in sorted(Counter(dataset.label).items())),
        "note": "NumPy one-hidden-layer MLP over summary plus temporal pooled signal features; weak-label prototype only.",
    }
    add_group_metrics(metrics, "train", dataset.metadata, dataset.label, dataset.target, predictions, train)
    add_group_metrics(metrics, "test", dataset.metadata, dataset.label, dataset.target, predictions, test)
    metrics.update(summarize_by_sample(dataset.metadata, predictions))

    write_predictions(args.predictions, dataset.metadata, dataset.label, dataset.target, predictions, train, test)
    write_summary(args.summary, metrics)
    print(f"Wrote predictions to {args.predictions}")
    print(f"Wrote summary to {args.summary}")
    print(f"Test MAE: {metrics['test_mae']}")


if __name__ == "__main__":
    main()
