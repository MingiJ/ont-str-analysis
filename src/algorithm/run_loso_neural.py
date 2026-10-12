#!/usr/bin/env python3
"""Run leave-one-sample-out NumPy MLP allele evaluation."""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

import numpy as np


DEFAULT_SAMPLES = [
    "GM04723",
    "ND30015",
    "ND30016",
    "ND30047",
    "ND30422",
    "ND30626",
    "ND31551",
    "ND33392",
    "ND33947",
]
DEFAULT_OUT_DIR = Path("ont-str-runner/work/analysis/loso_neural")
DEFAULT_SUMMARY = Path("ont-str-runner/work/analysis/loso_neural_summary.tsv")
DEFAULT_CALLS = Path("ont-str-runner/work/analysis/loso_neural_allele_calls.tsv")
DEFAULT_INDEX = Path("ont-str-runner/work/analysis/signal_windows.index.tsv")
SUMMARY_FIELDS = ["metric", "value"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run leave-one-sample-out NumPy MLP allele evaluation.")
    parser.add_argument("--samples", nargs="+", default=DEFAULT_SAMPLES)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--calls", type=Path, default=DEFAULT_CALLS)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--epochs", type=int, default=250)
    parser.add_argument("--hidden-dim", type=int, default=32)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--no-tail-span-correction", action="store_true")
    return parser.parse_args()


def run_command(command: list[str]) -> None:
    print(" ".join(command), flush=True)
    subprocess.run(command, check=True)


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def mae(values: list[float]) -> float:
    return float(np.mean(np.abs(values))) if values else float("nan")


def kmeans_two(values: list[float]) -> tuple[float, float]:
    data = np.asarray(values, dtype=np.float64)
    centers = np.asarray([np.quantile(data, 0.25), np.quantile(data, 0.75)], dtype=np.float64)
    labels = np.zeros(data.shape[0], dtype=np.int8)
    for _ in range(100):
        new_labels = np.argmin(np.abs(data.reshape(-1, 1) - centers.reshape(1, -1)), axis=1).astype(np.int8)
        new_centers = centers.copy()
        for idx in (0, 1):
            if np.any(new_labels == idx):
                new_centers[idx] = float(np.median(data[new_labels == idx]))
        if np.array_equal(labels, new_labels) and np.allclose(centers, new_centers):
            break
        labels = new_labels
        centers = new_centers
    ordered = np.sort(centers)
    return float(ordered[1]), float(ordered[0])


def sample_span_truth(index_path: Path, samples: list[str]) -> tuple[dict[str, tuple[float, float]], dict[str, tuple[float, float]]]:
    rows = read_tsv(index_path)
    span: dict[str, tuple[float, float]] = {}
    truth: dict[str, tuple[float, float]] = {}
    for sample in samples:
        sample_rows = [row for row in rows if row.get("sample") == sample]
        if not sample_rows:
            continue
        span[sample] = kmeans_two([float(row["stored_len"]) for row in sample_rows])
        truth[sample] = (float(sample_rows[0]["truth_long"]), float(sample_rows[0]["truth_short"]))
    return span, truth


def apply_tail_span_correction(
    row: dict[str, object],
    samples: list[str],
    span: dict[str, tuple[float, float]],
    truth: dict[str, tuple[float, float]],
) -> dict[str, object]:
    holdout = str(row["holdout_sample"])
    train = [sample for sample in samples if sample != holdout and sample in span and sample in truth]
    row["tail_span_applied"] = "False"
    row["tail_span_raw_long"] = row["pred_long"]
    row["tail_span_long_span"] = f"{span[holdout][0]:.3f}" if holdout in span else ""
    if holdout not in span or len(train) < 3:
        return row

    max_train_span = max(span[sample][0] for sample in train)
    if span[holdout][0] <= max_train_span:
        return row

    anchors = sorted(train, key=lambda sample: span[sample][0])[-3:]
    design = np.column_stack([np.ones(len(anchors)), [span[sample][0] for sample in anchors]])
    targets = np.asarray([truth[sample][0] for sample in anchors], dtype=np.float64)
    intercept, slope = np.linalg.lstsq(design, targets, rcond=None)[0]
    corrected = int(round(float(intercept + slope * span[holdout][0])))
    row["pred_long"] = corrected
    row["long_error"] = int(round(corrected - truth[holdout][0]))
    row["tail_span_applied"] = "True"
    row["tail_span_anchors"] = ";".join(f"{sample}:{span[sample][0]:.1f}:{truth[sample][0]:.0f}" for sample in anchors)
    return row


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    span, truth = sample_span_truth(args.index, args.samples)

    all_test_calls: list[dict[str, object]] = []
    long_errors: list[float] = []
    short_errors: list[float] = []
    per_sample_overall: list[float] = []

    for sample in args.samples:
        stem = args.out_dir / sample
        predictions = stem.with_suffix(".predictions.tsv")
        model_summary = stem.with_suffix(".model_summary.tsv")
        allele_calls = stem.with_suffix(".allele_calls.tsv")
        allele_summary = stem.with_suffix(".allele_summary.tsv")

        run_command(
            [
                sys.executable,
                "src/algorithm/neural_baseline.py",
                "--holdout-sample",
                sample,
                "--epochs",
                str(args.epochs),
                "--hidden-dim",
                str(args.hidden_dim),
                "--seed",
                str(args.seed),
                "--predictions",
                str(predictions),
                "--summary",
                str(model_summary),
            ]
        )
        run_command(
            [
                sys.executable,
                "src/algorithm/evaluate_allele_calls.py",
                "--predictions",
                str(predictions),
                "--calls",
                str(allele_calls),
                "--summary",
                str(allele_summary),
                "--calibration",
                "train-affine",
            ]
        )

        test_rows = [row for row in read_tsv(allele_calls) if row.get("split_scope") == "test"]
        if len(test_rows) != 1:
            raise SystemExit(f"Expected exactly one test call for {sample}, found {len(test_rows)}")
        row = dict(test_rows[0])
        row["holdout_sample"] = sample
        if not args.no_tail_span_correction:
            row = apply_tail_span_correction(row, args.samples, span, truth)
        all_test_calls.append(row)
        long_error = float(row["long_error"])
        short_error = float(row["short_error"])
        long_errors.append(long_error)
        short_errors.append(short_error)
        per_sample_overall.append((abs(long_error) + abs(short_error)) / 2.0)

    fields = ["holdout_sample"] + [field for field in all_test_calls[0] if field != "holdout_sample"]
    write_tsv(args.calls, all_test_calls, fields)

    metrics: dict[str, object] = {
        "samples": len(all_test_calls),
        "epochs": args.epochs,
        "hidden_dim": args.hidden_dim,
        "seed": args.seed,
        "tail_span_correction": str(not args.no_tail_span_correction),
        "long_mae": f"{mae(long_errors):.3f}",
        "short_mae": f"{mae(short_errors):.3f}",
        "overall_allele_mae": f"{mae(long_errors + short_errors):.3f}",
        "mean_sample_allele_mae": f"{float(np.mean(per_sample_overall)):.3f}",
        "benchmark_warpstr_overall_mae": "0.722",
        "benchmark_strique_overall_mae": "1.667",
        "note": "Leave-one-sample-out NumPy MLP with train-affine allele calibration and optional tail-span correction.",
    }
    write_tsv(args.summary, [{"metric": key, "value": value} for key, value in metrics.items()], SUMMARY_FIELDS)
    print(f"Wrote LOSO calls to {args.calls}")
    print(f"Wrote LOSO summary to {args.summary}")
    print(f"LOSO overall allele MAE: {metrics['overall_allele_mae']}")


if __name__ == "__main__":
    main()
