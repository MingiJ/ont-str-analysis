#!/usr/bin/env python3
"""Evaluate a repeat-local autocorrelation feature under nested LOSO.

This development ablation estimates a local raw-signal period without using
per-read allele labels.  The exact independently mapped repeat span is divided
by that period and calibrated to CAG count using training samples only.  Since
the autocorrelation feature was devised on the current nine samples, its fixed
feature LOSO score is exploratory.  A nested duration-versus-autocorrelation
selector is also reported to avoid choosing the feature with outer-test truth.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

try:
    from evaluate_repeat_duration_loso import read_tsv, write_tsv
    from weak_supervised_rnn import fit_duration_prior, truth_pairs_from_metadata, two_cluster_medians
except ImportError:  # pragma: no cover - allows module execution with -m
    from .evaluate_repeat_duration_loso import read_tsv, write_tsv
    from .weak_supervised_rnn import fit_duration_prior, truth_pairs_from_metadata, two_cluster_medians


DEFAULT_INDEX = Path(
    "ont-str-runner/work/analysis/signal_repeat_windows_independent_qc_dev.index.tsv"
)
DEFAULT_ARCHIVE = Path(
    "ont-str-runner/work/analysis/signal_repeat_windows_independent_qc_dev.npz"
)
DEFAULT_OUTPUT_DIR = Path(
    "ont-str-runner/work/analysis/repeat_periodicity_independent_loso_dev"
)
FEATURES = ("duration", "acf_period_normalized")
FOLD_FIELDS = [
    "holdout_sample",
    "truth_short",
    "truth_long",
    "duration_pred_short",
    "duration_pred_long",
    "duration_allele_mae",
    "acf_pred_short",
    "acf_pred_long",
    "acf_allele_mae",
    "nested_selected_feature",
    "nested_inner_mae",
    "nested_pred_short",
    "nested_pred_long",
    "nested_allele_mae",
    "rows_used",
]


def autocorrelation_period(signal: np.ndarray, expected_period: float) -> tuple[float, float]:
    """Return a local ACF peak and its correlation near the expected CAG dwell."""
    values = np.asarray(signal, dtype=np.float64)
    if values.size < 100 or not np.isfinite(expected_period) or expected_period <= 0.0:
        return np.nan, np.nan
    values = values - np.mean(values)
    scale = float(np.std(values))
    if not np.isfinite(scale) or scale < 1e-8:
        return np.nan, np.nan
    values /= scale
    low = max(9, int(round(expected_period * 0.55)))
    high = min(150, int(round(expected_period * 1.65)), values.size // 3)
    if high <= low:
        return np.nan, np.nan

    lags = np.arange(low, high + 1)
    fft_size = 1 << (2 * values.size - 1).bit_length()
    spectrum = np.fft.rfft(values, fft_size)
    autocovariance = np.fft.irfft(spectrum * np.conj(spectrum), fft_size)[: high + 1]
    autocovariance /= np.arange(values.size, values.size - high - 1, -1)
    scores = autocovariance[lags]
    local_peak = np.r_[
        False,
        (scores[1:-1] >= scores[:-2]) & (scores[1:-1] >= scores[2:]),
        False,
    ]
    candidates = np.flatnonzero(local_peak)
    if candidates.size == 0:
        candidates = np.arange(scores.size)
    distance_weight = np.exp(
        -0.5 * ((lags[candidates] - expected_period) / (0.35 * expected_period)) ** 2
    )
    chosen = candidates[int(np.argmax(scores[candidates] * distance_weight))]
    return float(lags[chosen]), float(scores[chosen])


def feature_values(
    metadata: list[dict[str, str]],
    signal: np.ndarray,
) -> tuple[dict[str, dict[str, np.ndarray]], np.ndarray, np.ndarray]:
    """Extract duration and ACF-normalized proxies from exact repeat slices."""
    if signal.shape[0] != len(metadata):
        raise ValueError("signal rows and index rows differ")
    grouped: dict[str, dict[str, list[float]]] = {
        name: defaultdict(list) for name in FEATURES
    }
    periods: list[float] = []
    strengths: list[float] = []
    for row_index, row in enumerate(metadata):
        sample = row.get("sample", "")
        if not sample:
            continue
        try:
            source_start = int(row["source_start"])
            source_end = int(row["source_end"])
            window_start = int(row["window_start"])
            left_rate = float(row["raw_per_base_left"])
            right_rate = float(row["raw_per_base_right"])
        except (KeyError, TypeError, ValueError):
            continue
        span = abs(source_end - source_start)
        left_pad = min(source_start, source_end) - window_start
        if span <= 0 or left_pad < 0 or left_pad + span > signal.shape[1]:
            continue
        repeat_signal = signal[row_index, left_pad : left_pad + span]
        expected_period = 3.0 * float(np.median([left_rate, right_rate]))
        period, strength = autocorrelation_period(repeat_signal, expected_period)
        if not np.isfinite(period) or period <= 0.0:
            continue
        grouped["duration"][sample].append(float(span))
        grouped["acf_period_normalized"][sample].append(float(span) / period)
        periods.append(period)
        strengths.append(strength)
    arrays = {
        name: {sample: np.asarray(values, dtype=np.float64) for sample, values in by_sample.items()}
        for name, by_sample in grouped.items()
    }
    return arrays, np.asarray(periods), np.asarray(strengths)


def predict_feature(
    values_by_sample: dict[str, np.ndarray],
    truth_pairs: dict[str, tuple[float, float]],
    train_samples: list[str],
    holdout_sample: str,
) -> tuple[float, float]:
    intercept, slope, _, _ = fit_duration_prior(values_by_sample, truth_pairs, train_samples)
    low, high = two_cluster_medians(values_by_sample[holdout_sample])
    return intercept + slope * low, intercept + slope * high


def inner_loso_mae(
    values_by_sample: dict[str, np.ndarray],
    truth_pairs: dict[str, tuple[float, float]],
    outer_train: list[str],
) -> float:
    errors = []
    for validation in outer_train:
        inner_train = [sample for sample in outer_train if sample != validation]
        prediction = predict_feature(values_by_sample, truth_pairs, inner_train, validation)
        errors.append(np.mean(np.abs(np.asarray(prediction) - np.asarray(truth_pairs[validation]))))
    return float(np.mean(errors))


def evaluate(
    metadata: list[dict[str, str]],
    signal: np.ndarray,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    truth_pairs = truth_pairs_from_metadata(metadata)
    features, periods, strengths = feature_values(metadata, signal)
    samples = sorted(truth_pairs)
    for name in FEATURES:
        missing = sorted(set(samples) - set(features[name]))
        if missing:
            raise ValueError(f"feature {name} is missing samples: {', '.join(missing)}")

    folds: list[dict[str, object]] = []
    selected = Counter()
    for holdout in samples:
        outer_train = [sample for sample in samples if sample != holdout]
        predictions = {
            name: predict_feature(features[name], truth_pairs, outer_train, holdout)
            for name in FEATURES
        }
        inner_scores = {
            name: inner_loso_mae(features[name], truth_pairs, outer_train)
            for name in FEATURES
        }
        chosen = min(FEATURES, key=lambda name: (inner_scores[name], name))
        selected[chosen] += 1
        truth = np.asarray(truth_pairs[holdout])
        duration_error = float(np.mean(np.abs(np.asarray(predictions["duration"]) - truth)))
        acf_error = float(
            np.mean(np.abs(np.asarray(predictions["acf_period_normalized"]) - truth))
        )
        nested_error = float(np.mean(np.abs(np.asarray(predictions[chosen]) - truth)))
        folds.append(
            {
                "holdout_sample": holdout,
                "truth_short": f"{truth[0]:.6f}",
                "truth_long": f"{truth[1]:.6f}",
                "duration_pred_short": f"{predictions['duration'][0]:.6f}",
                "duration_pred_long": f"{predictions['duration'][1]:.6f}",
                "duration_allele_mae": f"{duration_error:.6f}",
                "acf_pred_short": f"{predictions['acf_period_normalized'][0]:.6f}",
                "acf_pred_long": f"{predictions['acf_period_normalized'][1]:.6f}",
                "acf_allele_mae": f"{acf_error:.6f}",
                "nested_selected_feature": chosen,
                "nested_inner_mae": f"{inner_scores[chosen]:.6f}",
                "nested_pred_short": f"{predictions[chosen][0]:.6f}",
                "nested_pred_long": f"{predictions[chosen][1]:.6f}",
                "nested_allele_mae": f"{nested_error:.6f}",
                "rows_used": int(features[chosen][holdout].size),
            }
        )

    summary = {
        "folds": len(folds),
        "duration_allele_mae": float(np.mean([float(row["duration_allele_mae"]) for row in folds])),
        "fixed_acf_allele_mae": float(np.mean([float(row["acf_allele_mae"]) for row in folds])),
        "nested_selected_allele_mae": float(
            np.mean([float(row["nested_allele_mae"]) for row in folds])
        ),
        "selected_duration_folds": selected["duration"],
        "selected_acf_folds": selected["acf_period_normalized"],
        "acf_period_median": float(np.nanmedian(periods)),
        "acf_strength_median": float(np.nanmedian(strengths)),
    }
    return folds, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--signal-archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metadata = read_tsv(args.index)
    with np.load(args.signal_archive) as archive:
        signal = archive["signal"]
    folds, metrics = evaluate(metadata, signal)
    write_tsv(args.output_dir / "folds.tsv", folds, FOLD_FIELDS)
    summary_rows = [
        {"metric": "evaluation", "value": "nested_leave_one_sample_out_feature_selection"},
        *({"metric": key, "value": f"{value:.6f}" if isinstance(value, float) else value} for key, value in metrics.items()),
        {
            "metric": "fixed_acf_status",
            "value": "exploratory; feature and parameters were developed on these nine samples",
        },
        {
            "metric": "nested_selection_status",
            "value": "outer holdout truth excluded from feature choice and calibration",
        },
    ]
    write_tsv(args.output_dir / "summary.tsv", summary_rows, ["metric", "value"])
    print(f"Wrote {args.output_dir / 'folds.tsv'}")
    print(f"Wrote {args.output_dir / 'summary.tsv'}")


if __name__ == "__main__":
    main()
