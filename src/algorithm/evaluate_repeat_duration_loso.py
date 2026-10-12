#!/usr/bin/env python3
"""Evaluate the independent repeat-duration ablation with strict LOSO.

The input is the index produced for repeat-focused signal windows.  Per-read
allele labels and tool-derived counts are deliberately ignored.  For each
outer holdout, two robust duration centres are estimated independently within
every sample, and an affine duration-to-CAG calibration is fitted using only
the other samples' unordered diploid truths.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

try:
    from weak_supervised_rnn import fit_duration_prior, truth_pairs_from_metadata, two_cluster_medians
except ImportError:  # pragma: no cover - allows module execution with -m
    from .weak_supervised_rnn import fit_duration_prior, truth_pairs_from_metadata, two_cluster_medians


DEFAULT_INDEX = Path(
    "ont-str-runner/work/analysis/signal_repeat_windows_independent_qc_dev.index.tsv"
)
DEFAULT_OUTPUT_DIR = Path(
    "ont-str-runner/work/analysis/repeat_duration_independent_loso_dev"
)
FOLD_FIELDS = [
    "holdout_sample",
    "truth_short",
    "truth_long",
    "duration_short_centre",
    "duration_long_centre",
    "calibration_intercept",
    "calibration_slope",
    "train_calibration_rmse",
    "pred_short",
    "pred_long",
    "short_error",
    "long_error",
    "allele_mae",
    "rows_used",
]


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def durations_from_metadata(
    metadata: list[dict[str, str]],
    duration_field: str,
) -> dict[str, np.ndarray]:
    """Collect finite positive durations without reading per-read labels."""
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in metadata:
        sample = row.get("sample", "")
        raw_value = row.get(duration_field, "")
        if not sample or raw_value in (None, ""):
            continue
        try:
            value = float(raw_value)
        except ValueError:
            continue
        if np.isfinite(value) and value > 0.0:
            grouped[sample].append(value)
    return {
        sample: np.asarray(values, dtype=np.float64)
        for sample, values in grouped.items()
        if len(values) >= 2
    }


def predict_holdout(
    lengths_by_sample: dict[str, np.ndarray],
    truth_pairs: dict[str, tuple[float, float]],
    train_samples: list[str],
    holdout_sample: str,
) -> dict[str, float]:
    """Predict one holdout using only train truths and holdout durations."""
    if holdout_sample not in lengths_by_sample:
        raise ValueError(f"missing duration data for holdout sample {holdout_sample}")
    intercept, slope, _, calibration_rmse = fit_duration_prior(
        lengths_by_sample,
        truth_pairs,
        train_samples,
    )
    low_duration, high_duration = two_cluster_medians(lengths_by_sample[holdout_sample])
    return {
        "duration_short_centre": low_duration,
        "duration_long_centre": high_duration,
        "calibration_intercept": intercept,
        "calibration_slope": slope,
        "train_calibration_rmse": calibration_rmse,
        "pred_short": intercept + slope * low_duration,
        "pred_long": intercept + slope * high_duration,
    }


def evaluate_loso(
    metadata: list[dict[str, str]],
    *,
    duration_field: str = "source_span_abs",
    samples: list[str] | None = None,
) -> list[dict[str, object]]:
    truth_pairs = truth_pairs_from_metadata(metadata)
    lengths_by_sample = durations_from_metadata(metadata, duration_field)
    selected = sorted(samples or truth_pairs)
    unknown = sorted(set(selected) - set(truth_pairs))
    missing_duration = sorted(set(selected) - set(lengths_by_sample))
    if unknown:
        raise ValueError(f"samples without diploid truth: {', '.join(unknown)}")
    if missing_duration:
        raise ValueError(f"samples without usable durations: {', '.join(missing_duration)}")
    if len(selected) < 3:
        raise ValueError("at least three labelled samples are required")

    fold_rows: list[dict[str, object]] = []
    for holdout in selected:
        train_samples = [sample for sample in selected if sample != holdout]
        prediction = predict_holdout(
            lengths_by_sample,
            truth_pairs,
            train_samples,
            holdout,
        )
        truth_short, truth_long = truth_pairs[holdout]
        short_error = prediction["pred_short"] - truth_short
        long_error = prediction["pred_long"] - truth_long
        fold_rows.append(
            {
                "holdout_sample": holdout,
                "truth_short": f"{truth_short:.6f}",
                "truth_long": f"{truth_long:.6f}",
                "duration_short_centre": f"{prediction['duration_short_centre']:.6f}",
                "duration_long_centre": f"{prediction['duration_long_centre']:.6f}",
                "calibration_intercept": f"{prediction['calibration_intercept']:.9f}",
                "calibration_slope": f"{prediction['calibration_slope']:.9f}",
                "train_calibration_rmse": f"{prediction['train_calibration_rmse']:.6f}",
                "pred_short": f"{prediction['pred_short']:.6f}",
                "pred_long": f"{prediction['pred_long']:.6f}",
                "short_error": f"{short_error:.6f}",
                "long_error": f"{long_error:.6f}",
                "allele_mae": f"{np.mean([abs(short_error), abs(long_error)]):.6f}",
                "rows_used": int(lengths_by_sample[holdout].size),
            }
        )
    return fold_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Strict LOSO evaluation of independently mapped repeat duration"
    )
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--duration-field", default="source_span_abs")
    parser.add_argument("--samples", nargs="*", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metadata = read_tsv(args.index)
    boundary_kinds = {row.get("boundary_kind", "") for row in metadata}
    if boundary_kinds - {"repeat", ""}:
        raise SystemExit(
            "repeat-duration evaluation requires a repeat-focused index; "
            f"found boundary kinds: {', '.join(sorted(boundary_kinds))}"
        )
    fold_rows = evaluate_loso(
        metadata,
        duration_field=args.duration_field,
        samples=args.samples,
    )
    allele_mae = float(np.mean([float(row["allele_mae"]) for row in fold_rows]))
    write_tsv(args.output_dir / "folds.tsv", fold_rows, FOLD_FIELDS)
    summary = [
        {"metric": "evaluation", "value": "leave_one_sample_out"},
        {"metric": "boundary_kind", "value": "repeat"},
        {"metric": "duration_field", "value": args.duration_field},
        {"metric": "folds", "value": len(fold_rows)},
        {"metric": "allele_mae", "value": f"{allele_mae:.6f}"},
        {
            "metric": "supervision",
            "value": "train-sample unordered diploid truth only; no per-read labels",
        },
        {
            "metric": "note",
            "value": "Forced duration-only ablation without uncertainty or abstention.",
        },
    ]
    write_tsv(args.output_dir / "summary.tsv", summary, ["metric", "value"])
    print(f"Wrote {args.output_dir / 'folds.tsv'}")
    print(f"Wrote {args.output_dir / 'summary.tsv'}")


if __name__ == "__main__":
    main()
