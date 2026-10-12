#!/usr/bin/env python3
"""Dataset helpers for extracted HTT CAG signal windows."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np


DEFAULT_SIGNAL_ARCHIVE = Path("ont-str-runner/work/analysis/signal_windows.npz")
DEFAULT_INDEX = Path("ont-str-runner/work/analysis/signal_windows.index.tsv")
DEFAULT_HOLDOUT_SAMPLE = "ND33392"


@dataclass(frozen=True)
class SignalDataset:
    signal: np.ndarray
    mask: np.ndarray
    key: np.ndarray
    metadata: list[dict[str, str]]
    target: np.ndarray
    target_mask: np.ndarray
    label: np.ndarray


def to_float(value: str | None) -> float | None:
    if value in (None, "", "-"):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def load_index(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def target_from_row(row: dict[str, str]) -> tuple[float, bool, str]:
    label = row.get("group_label", "")
    truth_long = to_float(row.get("truth_long"))
    truth_short = to_float(row.get("truth_short"))
    if label == "long_like" and truth_long is not None:
        return truth_long, True, label
    if label == "short_like" and truth_short is not None:
        return truth_short, True, label
    return np.nan, False, label


def load_signal_dataset(signal_archive: Path = DEFAULT_SIGNAL_ARCHIVE, index: Path = DEFAULT_INDEX) -> SignalDataset:
    metadata = load_index(index)
    with np.load(signal_archive) as arrays:
        signal = np.asarray(arrays["signal"], dtype=np.float32)
        mask = np.asarray(arrays["mask"], dtype=np.bool_)
        key = np.asarray(arrays["key"])

    if len(metadata) != signal.shape[0]:
        raise ValueError(f"index rows ({len(metadata)}) do not match signal rows ({signal.shape[0]})")

    targets = []
    target_mask = []
    labels = []
    for row in metadata:
        target, usable, label = target_from_row(row)
        targets.append(target)
        target_mask.append(usable)
        labels.append(label)

    return SignalDataset(
        signal=signal,
        mask=mask,
        key=key,
        metadata=metadata,
        target=np.asarray(targets, dtype=np.float32),
        target_mask=np.asarray(target_mask, dtype=np.bool_),
        label=np.asarray(labels),
    )


def deterministic_read_split(labels: np.ndarray, usable: np.ndarray, train_fraction: float) -> tuple[np.ndarray, np.ndarray]:
    train = np.zeros(labels.shape[0], dtype=np.bool_)
    test = np.zeros(labels.shape[0], dtype=np.bool_)
    for label in sorted(set(labels[usable])):
        idx = np.flatnonzero(usable & (labels == label))
        if idx.size == 0:
            continue
        train_count = max(1, int(round(idx.size * train_fraction)))
        if idx.size > 1:
            train_count = min(train_count, idx.size - 1)
        train[idx[:train_count]] = True
        test[idx[train_count:]] = True
    return train, test


def heldout_sample_split(
    metadata: list[dict[str, str]],
    usable: np.ndarray,
    holdout_sample: str = DEFAULT_HOLDOUT_SAMPLE,
) -> tuple[np.ndarray, np.ndarray]:
    samples = np.asarray([row.get("sample", "") for row in metadata])
    train = usable & (samples != holdout_sample)
    test = usable & (samples == holdout_sample)
    return train, test


def split_dataset(
    dataset: SignalDataset,
    split: str,
    train_fraction: float,
    holdout_sample: str = DEFAULT_HOLDOUT_SAMPLE,
) -> tuple[np.ndarray, np.ndarray]:
    if split == "heldout-sample":
        return heldout_sample_split(dataset.metadata, dataset.target_mask, holdout_sample)
    if split == "random-read":
        return deterministic_read_split(dataset.label, dataset.target_mask, train_fraction)
    raise ValueError(f"unknown split mode: {split}")


def signal_summary_features(dataset: SignalDataset) -> tuple[np.ndarray, list[str]]:
    """Return compact baseline features without depending on a neural framework."""
    signal = dataset.signal
    mask = dataset.mask
    lengths = mask.sum(axis=1).astype(np.float32)
    features = []

    for row_idx in range(signal.shape[0]):
        values = signal[row_idx, mask[row_idx]]
        if values.size == 0:
            stats = [0.0] * 8
        else:
            stats = [
                float(lengths[row_idx]),
                float(values.mean()),
                float(values.std()),
                float(np.mean(np.abs(values))),
                float(np.quantile(values, 0.10)),
                float(np.quantile(values, 0.25)),
                float(np.quantile(values, 0.75)),
                float(np.quantile(values, 0.90)),
            ]
        features.append(stats)

    names = ["stored_len", "mean", "std", "mean_abs", "q10", "q25", "q75", "q90"]
    return np.asarray(features, dtype=np.float32), names


def temporal_pooled_features(dataset: SignalDataset, bins: int) -> tuple[np.ndarray, list[str]]:
    """Return mean signal in fixed temporal bins for each read."""
    features = np.zeros((dataset.signal.shape[0], bins), dtype=np.float32)
    for row_idx in range(dataset.signal.shape[0]):
        values = dataset.signal[row_idx, dataset.mask[row_idx]]
        if values.size == 0:
            continue
        edges = np.linspace(0, values.size, bins + 1, dtype=np.int64)
        for bin_idx in range(bins):
            start = edges[bin_idx]
            end = edges[bin_idx + 1]
            if end <= start:
                features[row_idx, bin_idx] = values[min(start, values.size - 1)]
            else:
                features[row_idx, bin_idx] = float(values[start:end].mean())
    names = [f"bin_mean_{idx:03d}" for idx in range(bins)]
    return features, names


def combined_signal_features(dataset: SignalDataset, bins: int) -> tuple[np.ndarray, list[str]]:
    summary, summary_names = signal_summary_features(dataset)
    pooled, pooled_names = temporal_pooled_features(dataset, bins)
    return np.column_stack([summary, pooled]).astype(np.float32), summary_names + pooled_names
