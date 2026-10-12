#!/usr/bin/env python3
"""Train a PyTorch RNN repeat-count regressor on raw signal windows.

This is the first sequence-aware model in the new algorithm pipeline. It keeps
the same weak-label split and outputs as the NumPy baselines, but consumes the
padded raw signal directly instead of pooled hand-built features.
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np

try:
    import torch
    from torch import nn
    from torch.nn.utils.rnn import pack_padded_sequence
    from torch.utils.data import DataLoader, Dataset
except ImportError as exc:  # pragma: no cover - exercised when dependency is missing
    raise SystemExit(
        "PyTorch is not installed. Install it in the active environment, e.g. "
        "`.venv/bin/python -m pip install torch`, then rerun this script."
    ) from exc

try:
    from dataset import (
        DEFAULT_HOLDOUT_SAMPLE,
        DEFAULT_INDEX,
        DEFAULT_SIGNAL_ARCHIVE,
        SignalDataset,
        load_signal_dataset,
        split_dataset,
    )
    from neural_baseline import validation_split
except ImportError:  # pragma: no cover - allows module execution with -m
    from .dataset import (
        DEFAULT_HOLDOUT_SAMPLE,
        DEFAULT_INDEX,
        DEFAULT_SIGNAL_ARCHIVE,
        SignalDataset,
        load_signal_dataset,
        split_dataset,
    )
    from .neural_baseline import validation_split


DEFAULT_PREDICTIONS = Path("ont-str-runner/work/analysis/torch_rnn_predictions.tsv")
DEFAULT_SUMMARY = Path("ont-str-runner/work/analysis/torch_rnn_summary.tsv")
DEFAULT_CHECKPOINT = Path("ont-str-runner/work/analysis/torch_rnn.pt")
PREDICTION_FIELDS = ["sample", "read_id", "label", "target", "prediction", "confidence", "split"]
SUMMARY_FIELDS = ["metric", "value"]


@dataclass(frozen=True)
class Batch:
    signal: torch.Tensor
    length: torch.Tensor
    target: torch.Tensor
    weight: torch.Tensor
    index: torch.Tensor


class SignalWindowDataset(Dataset[Batch]):
    def __init__(self, dataset: SignalDataset, indices: np.ndarray, weights: np.ndarray | None = None) -> None:
        self.dataset = dataset
        self.indices = np.asarray(indices, dtype=np.int64)
        self.lengths = dataset.mask.sum(axis=1).astype(np.int64)
        self.weights = np.ones(self.indices.shape[0], dtype=np.float32) if weights is None else np.asarray(weights, dtype=np.float32)
        if self.weights.shape[0] != self.indices.shape[0]:
            raise ValueError("weights must match selected indices")

    def __len__(self) -> int:
        return int(self.indices.shape[0])

    def __getitem__(self, item: int) -> Batch:
        row_idx = int(self.indices[item])
        return Batch(
            signal=torch.from_numpy(self.dataset.signal[row_idx]),
            length=torch.tensor(max(1, int(self.lengths[row_idx])), dtype=torch.long),
            target=torch.tensor(float(self.dataset.target[row_idx]), dtype=torch.float32),
            weight=torch.tensor(float(self.weights[item]), dtype=torch.float32),
            index=torch.tensor(row_idx, dtype=torch.long),
        )


def collate_batches(rows: list[Batch]) -> Batch:
    return Batch(
        signal=torch.stack([row.signal for row in rows]),
        length=torch.stack([row.length for row in rows]),
        target=torch.stack([row.target for row in rows]),
        weight=torch.stack([row.weight for row in rows]),
        index=torch.stack([row.index for row in rows]),
    )


class RepeatCountRNN(nn.Module):
    def __init__(
        self,
        hidden_dim: int,
        rnn_type: str,
        conv_channels: int,
        dropout: float,
        conv_stride1: int,
        conv_stride2: int,
    ) -> None:
        super().__init__()
        self.conv_stride1 = conv_stride1
        self.conv_stride2 = conv_stride2
        self.conv1 = nn.Conv1d(1, conv_channels, kernel_size=9, stride=conv_stride1, padding=4)
        self.conv2 = nn.Conv1d(conv_channels, conv_channels, kernel_size=7, stride=conv_stride2, padding=3)
        self.activation = nn.ReLU()
        rnn_cls = nn.GRU if rnn_type == "gru" else nn.LSTM
        self.rnn = rnn_cls(
            input_size=conv_channels,
            hidden_size=hidden_dim,
            batch_first=True,
            bidirectional=True,
            dropout=0.0,
        )
        self.head = nn.Sequential(
            nn.LayerNorm(hidden_dim * 2),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 2),
        )

    @staticmethod
    def conv_length(length: torch.Tensor, kernel_size: int, stride: int, padding: int, dilation: int = 1) -> torch.Tensor:
        value = torch.div(length + 2 * padding - dilation * (kernel_size - 1) - 1, stride, rounding_mode="floor") + 1
        return torch.clamp(value, min=1)

    def encoded_lengths(self, length: torch.Tensor) -> torch.Tensor:
        length = self.conv_length(length, kernel_size=9, stride=self.conv_stride1, padding=4)
        return self.conv_length(length, kernel_size=7, stride=self.conv_stride2, padding=3)

    def forward(self, signal: torch.Tensor, length: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        x = signal.unsqueeze(1)
        x = self.activation(self.conv1(x))
        x = self.activation(self.conv2(x))
        x = x.transpose(1, 2)
        encoded_length = self.encoded_lengths(length.cpu())
        packed = pack_padded_sequence(x, encoded_length, batch_first=True, enforce_sorted=False)
        _, state = self.rnn(packed)
        if isinstance(state, tuple):
            state = state[0]
        features = torch.cat([state[-2], state[-1]], dim=1)
        output = self.head(features)
        count = output[:, 0]
        log_variance = torch.clamp(output[:, 1], min=-4.0, max=4.0)
        return count, log_variance


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train PyTorch RNN repeat-count regressor on signal windows.")
    parser.add_argument("--signal-archive", type=Path, default=DEFAULT_SIGNAL_ARCHIVE)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--split", choices=("heldout-sample", "random-read"), default="heldout-sample")
    parser.add_argument("--holdout-sample", default=DEFAULT_HOLDOUT_SAMPLE)
    parser.add_argument("--train-fraction", type=float, default=0.8)
    parser.add_argument("--validation-fraction", type=float, default=0.15)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--hidden-dim", type=int, default=32)
    parser.add_argument("--conv-channels", type=int, default=8)
    parser.add_argument("--conv-stride1", type=int, default=32)
    parser.add_argument("--conv-stride2", type=int, default=8)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--rnn-type", choices=("gru", "lstm"), default="gru")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--max-rows", type=int, default=0, help="Optional deterministic cap for smoke tests.")
    parser.add_argument("--no-balance", action="store_true", help="Disable inverse-label weighting.")
    return parser.parse_args()


def choose_device(requested: str) -> torch.device:
    if requested == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if requested == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA was requested, but torch.cuda.is_available() is false.")
    return torch.device(requested)


def selected_indices(mask: np.ndarray, max_rows: int) -> np.ndarray:
    idx = np.flatnonzero(mask)
    if max_rows > 0:
        idx = idx[:max_rows]
    return idx


def capped_split_masks(train: np.ndarray, test: np.ndarray, max_rows: int) -> tuple[np.ndarray, np.ndarray]:
    if max_rows <= 0 or int(train.sum() + test.sum()) <= max_rows:
        return train, test

    if not np.any(train) or not np.any(test):
        return train, test

    train_total = int(train.sum())
    test_total = int(test.sum())
    train_count = int(round(max_rows * train_total / (train_total + test_total)))
    train_count = min(max(1, train_count), train_total)
    test_count = min(max(1, max_rows - train_count), test_total)

    if train_count + test_count < max_rows and train_count < train_total:
        train_count = min(train_total, train_count + (max_rows - train_count - test_count))
    if train_count + test_count < max_rows and test_count < test_total:
        test_count = min(test_total, test_count + (max_rows - train_count - test_count))

    capped_train = np.zeros_like(train)
    capped_test = np.zeros_like(test)
    capped_train[np.flatnonzero(train)[:train_count]] = True
    capped_test[np.flatnonzero(test)[:test_count]] = True
    return capped_train, capped_test


def label_weights(labels: np.ndarray) -> np.ndarray:
    counts = Counter(labels)
    weights = np.asarray([1.0 / counts[label] for label in labels], dtype=np.float32)
    return weights / weights.mean()


def weighted_gaussian_loss(prediction: torch.Tensor, log_variance: torch.Tensor, target: torch.Tensor, weight: torch.Tensor) -> torch.Tensor:
    error = prediction - target
    loss = 0.5 * (torch.exp(-log_variance) * error * error + log_variance)
    return torch.mean(loss * weight)


def mae(errors: np.ndarray) -> float:
    return float(np.mean(np.abs(errors))) if errors.size else float("nan")


def train_one_epoch(model: RepeatCountRNN, loader: DataLoader[Batch], optimizer: torch.optim.Optimizer, device: torch.device) -> float:
    model.train()
    total_loss = 0.0
    total_rows = 0
    for batch in loader:
        signal = batch.signal.to(device, non_blocking=True)
        length = batch.length.to(device, non_blocking=True)
        target = batch.target.to(device, non_blocking=True)
        weight = batch.weight.to(device, non_blocking=True)
        optimizer.zero_grad(set_to_none=True)
        prediction, log_variance = model(signal, length)
        loss = weighted_gaussian_loss(prediction, log_variance, target, weight)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
        optimizer.step()
        total_loss += float(loss.detach().cpu()) * signal.shape[0]
        total_rows += signal.shape[0]
    return total_loss / max(1, total_rows)


@torch.no_grad()
def predict(model: RepeatCountRNN, loader: DataLoader[Batch], device: torch.device, rows_total: int) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    predictions = np.full(rows_total, np.nan, dtype=np.float32)
    confidence = np.full(rows_total, np.nan, dtype=np.float32)
    for batch in loader:
        signal = batch.signal.to(device, non_blocking=True)
        length = batch.length.to(device, non_blocking=True)
        count, log_variance = model(signal, length)
        idx = batch.index.cpu().numpy()
        predictions[idx] = count.detach().cpu().numpy().astype(np.float32)
        confidence[idx] = torch.exp(-log_variance).detach().cpu().numpy().astype(np.float32)
    return predictions, confidence


def make_loader(dataset: SignalDataset, indices: np.ndarray, batch_size: int, shuffle: bool, weights: np.ndarray | None, num_workers: int) -> DataLoader[Batch]:
    windows = SignalWindowDataset(dataset, indices, weights)
    return DataLoader(
        windows,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        collate_fn=collate_batches,
        pin_memory=torch.cuda.is_available(),
    )


def write_predictions(path: Path, metadata: list[dict[str, str]], labels: np.ndarray, targets: np.ndarray, predictions: np.ndarray, confidence: np.ndarray, train: np.ndarray, test: np.ndarray) -> None:
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
                    "prediction": "" if np.isnan(predictions[idx]) else f"{predictions[idx]:.3f}",
                    "confidence": "" if np.isnan(confidence[idx]) else f"{confidence[idx]:.6f}",
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


def add_group_metrics(metrics: dict[str, object], prefix: str, metadata: list[dict[str, str]], labels: np.ndarray, targets: np.ndarray, predictions: np.ndarray, mask: np.ndarray) -> None:
    for label in sorted(set(labels[mask])):
        idx = mask & (labels == label)
        metrics[f"{prefix}_mae_{label}"] = f"{mae(predictions[idx] - targets[idx]):.3f}"

    samples = np.asarray([row.get("sample", "") for row in metadata])
    for sample in sorted(set(samples[mask])):
        idx = mask & (samples == sample)
        metrics[f"{prefix}_sample_{sample}_mae"] = f"{mae(predictions[idx] - targets[idx]):.3f}"
        metrics[f"{prefix}_sample_{sample}_rows"] = int(idx.sum())


def summarize_by_sample(metadata: list[dict[str, str]], predictions: np.ndarray) -> dict[str, str]:
    grouped: dict[str, list[int]] = defaultdict(list)
    for row, pred in zip(metadata, predictions):
        if np.isnan(pred):
            continue
        grouped[row.get("sample", "")].append(int(round(float(pred))))
    return {
        f"sample_{sample}_top_rounded_predictions": ";".join(f"{value}:{count}" for value, count in Counter(calls).most_common(5))
        for sample, calls in grouped.items()
    }


def checkpoint_payload(model: RepeatCountRNN, args: argparse.Namespace, metrics: dict[str, object]) -> dict[str, object]:
    return {
        "model_state": model.state_dict(),
        "args": vars(args),
        "metrics": metrics,
        "model": {
            "hidden_dim": args.hidden_dim,
            "rnn_type": args.rnn_type,
            "conv_channels": args.conv_channels,
            "conv_stride1": args.conv_stride1,
            "conv_stride2": args.conv_stride2,
            "dropout": args.dropout,
        },
    }


def main() -> None:
    args = parse_args()
    if args.epochs < 1:
        raise SystemExit("--epochs must be at least 1")
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be at least 1")
    if args.hidden_dim < 1:
        raise SystemExit("--hidden-dim must be at least 1")
    if args.conv_channels < 1:
        raise SystemExit("--conv-channels must be at least 1")
    if args.conv_stride1 < 1 or args.conv_stride2 < 1:
        raise SystemExit("--conv-stride1 and --conv-stride2 must be at least 1")

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = choose_device(args.device)

    dataset = load_signal_dataset(args.signal_archive, args.index)
    lengths = dataset.mask.sum(axis=1)
    if not np.all(lengths[dataset.target_mask] > 0):
        raise SystemExit("Found labeled rows with empty signal masks.")

    train, test = split_dataset(dataset, args.split, args.train_fraction, args.holdout_sample)
    if args.max_rows > 0:
        train, test = capped_split_masks(train, test, args.max_rows)
    if not np.any(train):
        raise SystemExit("No labeled training rows found.")
    if not np.any(test):
        raise SystemExit("No labeled test rows found.")

    fit, validation = validation_split(dataset.label, train, args.validation_fraction)
    if not np.any(fit):
        raise SystemExit("No labeled fitting rows found after validation split.")
    if args.max_rows > 0:
        validation &= train

    fit_indices = np.flatnonzero(fit)
    train_indices = np.flatnonzero(train)
    validation_indices = np.flatnonzero(validation)
    test_indices = np.flatnonzero(test)
    all_eval_indices = np.flatnonzero(train | test)

    fit_weights = None if args.no_balance else label_weights(dataset.label[fit])
    train_loader = make_loader(dataset, fit_indices, args.batch_size, True, fit_weights, args.num_workers)
    validation_loader = make_loader(dataset, validation_indices, args.batch_size, False, None, args.num_workers) if validation_indices.size else None
    eval_loader = make_loader(dataset, all_eval_indices, args.batch_size, False, None, args.num_workers)

    model = RepeatCountRNN(
        args.hidden_dim,
        args.rnn_type,
        args.conv_channels,
        args.dropout,
        args.conv_stride1,
        args.conv_stride2,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)

    best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    best_epoch = 0
    best_validation_mae = math.inf
    losses = []
    for epoch in range(1, args.epochs + 1):
        loss = train_one_epoch(model, train_loader, optimizer, device)
        losses.append(loss)
        if validation_loader is not None:
            validation_predictions, _ = predict(model, validation_loader, device, dataset.signal.shape[0])
            current_mae = mae(validation_predictions[validation] - dataset.target[validation])
        else:
            current_mae = loss
        if current_mae < best_validation_mae:
            best_validation_mae = current_mae
            best_epoch = epoch
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
        print(f"epoch={epoch} train_loss={loss:.4f} validation_mae={current_mae:.3f}")

    model.load_state_dict(best_state)
    predictions, confidence = predict(model, eval_loader, device, dataset.signal.shape[0])
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
        "device": str(device),
        "rnn_type": args.rnn_type,
        "hidden_dim": args.hidden_dim,
        "conv_channels": args.conv_channels,
        "conv_stride1": args.conv_stride1,
        "conv_stride2": args.conv_stride2,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "weight_decay": args.weight_decay,
        "seed": args.seed,
        "initial_train_loss": f"{losses[0]:.3f}",
        "final_train_loss": f"{losses[-1]:.3f}",
        "best_epoch": best_epoch,
        "validation_mae_at_best_epoch": f"{best_validation_mae:.3f}",
        "train_mae": f"{mae(train_errors):.3f}",
        "test_mae": f"{mae(test_errors):.3f}",
        "test_vs_ridge_baseline_mae": "9.705",
        "test_vs_numpy_mlp_mae": "7.405",
        "label_counts": ";".join(f"{k}:{v}" for k, v in sorted(Counter(dataset.label[dataset.target_mask]).items())),
        "note": "PyTorch Conv1d plus bidirectional RNN over raw signal windows; weak-label prototype only.",
    }
    add_group_metrics(metrics, "train", dataset.metadata, dataset.label, dataset.target, predictions, train)
    add_group_metrics(metrics, "test", dataset.metadata, dataset.label, dataset.target, predictions, test)
    metrics.update(summarize_by_sample(dataset.metadata, predictions))

    write_predictions(args.predictions, dataset.metadata, dataset.label, dataset.target, predictions, confidence, train, test)
    write_summary(args.summary, metrics)
    args.checkpoint.parent.mkdir(parents=True, exist_ok=True)
    torch.save(checkpoint_payload(model, args, metrics), args.checkpoint)
    print(f"Wrote predictions to {args.predictions}")
    print(f"Wrote summary to {args.summary}")
    print(f"Wrote checkpoint to {args.checkpoint}")
    print(f"Test MAE: {metrics['test_mae']}")


if __name__ == "__main__":
    main()
