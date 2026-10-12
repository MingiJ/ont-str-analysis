#!/usr/bin/env python3
"""Run a simple baseline repeat-count regressor on extracted signal windows.

This is not the proposed RNN. It is a small, deterministic sanity check that
confirms the dataset can be loaded and gives a weak baseline to beat.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

try:
    from dataset import (
        DEFAULT_HOLDOUT_SAMPLE,
        DEFAULT_INDEX,
        DEFAULT_SIGNAL_ARCHIVE,
        combined_signal_features,
        load_signal_dataset,
        signal_summary_features,
        split_dataset,
    )
except ImportError:  # pragma: no cover - allows module execution with -m
    from .dataset import (
        DEFAULT_HOLDOUT_SAMPLE,
        DEFAULT_INDEX,
        DEFAULT_SIGNAL_ARCHIVE,
        combined_signal_features,
        load_signal_dataset,
        signal_summary_features,
        split_dataset,
    )


DEFAULT_PREDICTIONS = Path("ont-str-runner/work/analysis/baseline_predictions.tsv")
DEFAULT_SUMMARY = Path("ont-str-runner/work/analysis/baseline_summary.tsv")
PREDICTION_FIELDS = ["sample", "read_id", "label", "target", "prediction", "split"]
SUMMARY_FIELDS = ["metric", "value"]


def standardize(train: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = train.mean(axis=0)
    std = train.std(axis=0)
    std[std < 1e-6] = 1.0
    return (train - mean) / std, (values - mean) / std, mean


def label_weights(labels: np.ndarray) -> np.ndarray:
    counts = Counter(labels)
    weights = np.asarray([1.0 / counts[label] for label in labels], dtype=np.float32)
    return weights / weights.mean()


def fit_ridge(features: np.ndarray, target: np.ndarray, alpha: float, weights: np.ndarray | None = None) -> np.ndarray:
    design = np.column_stack([np.ones(features.shape[0], dtype=np.float32), features])
    if weights is not None:
        scale = np.sqrt(weights).reshape(-1, 1)
        design = design * scale
        target = target * scale.ravel()
    penalty = np.eye(design.shape[1], dtype=np.float32) * alpha
    penalty[0, 0] = 0.0
    return np.linalg.solve(design.T @ design + penalty, design.T @ target)


def predict_ridge(features: np.ndarray, weights: np.ndarray) -> np.ndarray:
    design = np.column_stack([np.ones(features.shape[0], dtype=np.float32), features])
    return design @ weights


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
    summary = {}
    for sample, calls in grouped.items():
        top = Counter(calls).most_common(5)
        summary[f"sample_{sample}_top_rounded_predictions"] = ";".join(f"{value}:{count}" for value, count in top)
    return summary


def add_group_metrics(metrics: dict[str, object], prefix: str, metadata: list[dict[str, str]], labels: np.ndarray, targets: np.ndarray, predictions: np.ndarray, mask: np.ndarray) -> None:
    for label in sorted(set(labels[mask])):
        idx = mask & (labels == label)
        metrics[f"{prefix}_mae_{label}"] = f"{mae(predictions[idx] - targets[idx]):.3f}"

    samples = sorted({row.get("sample", "") for row, selected in zip(metadata, mask) if selected})
    for sample in samples:
        idx = mask & np.asarray([row.get("sample", "") == sample for row in metadata])
        metrics[f"{prefix}_sample_{sample}_mae"] = f"{mae(predictions[idx] - targets[idx]):.3f}"
        metrics[f"{prefix}_sample_{sample}_rows"] = int(idx.sum())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run simple signal-window repeat-count baseline.")
    parser.add_argument("--signal-archive", type=Path, default=DEFAULT_SIGNAL_ARCHIVE)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--alpha", type=float, default=1.0)
    parser.add_argument("--bins", type=int, default=128, help="Temporal bins for combined signal features.")
    parser.add_argument(
        "--feature-set",
        choices=("combined", "summary"),
        default="combined",
        help="Use summary-only features or summary plus temporal pooled bins.",
    )
    parser.add_argument(
        "--split",
        choices=("heldout-sample", "random-read"),
        default="heldout-sample",
        help="heldout-sample prevents same-sample reads from leaking into test.",
    )
    parser.add_argument("--holdout-sample", default=DEFAULT_HOLDOUT_SAMPLE)
    parser.add_argument("--train-fraction", type=float, default=0.8)
    parser.add_argument("--no-balance", action="store_true", help="Disable inverse-label weighting.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset = load_signal_dataset(args.signal_archive, args.index)
    if args.feature_set == "summary":
        features, feature_names = signal_summary_features(dataset)
    else:
        features, feature_names = combined_signal_features(dataset, args.bins)
    train, test = split_dataset(dataset, args.split, args.train_fraction, args.holdout_sample)
    if not np.any(train):
        raise SystemExit("No labeled training rows found.")
    if not np.any(test):
        raise SystemExit("No labeled test rows found.")

    train_features, all_features, _ = standardize(features[train], features)
    row_weights = None if args.no_balance else label_weights(dataset.label[train])
    model_weights = fit_ridge(train_features, dataset.target[train], args.alpha, row_weights)
    predictions = predict_ridge(all_features, model_weights)

    train_errors = predictions[train] - dataset.target[train]
    test_errors = predictions[test] - dataset.target[test]
    metrics: dict[str, object] = {
        "rows_total": dataset.signal.shape[0],
        "rows_labeled": int(dataset.target_mask.sum()),
        "rows_train": int(train.sum()),
        "rows_test": int(test.sum()),
        "split": args.split,
        "holdout_sample": args.holdout_sample if args.split == "heldout-sample" else "",
        "balanced_training": str(not args.no_balance),
        "feature_set": args.feature_set,
        "bins": args.bins if args.feature_set == "combined" else "",
        "feature_names": ",".join(feature_names),
        "train_mae": f"{mae(train_errors):.3f}",
        "test_mae": f"{mae(test_errors):.3f}",
        "label_counts": ";".join(f"{k}:{v}" for k, v in sorted(Counter(dataset.label).items())),
        "note": "Weak-label baseline only; labels come from existing tool-derived group_label, not manual per-read truth.",
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
