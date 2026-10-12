#!/usr/bin/env python3
"""Evaluate sample-level allele calls from per-read model predictions."""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path

import numpy as np


DEFAULT_PREDICTIONS = Path("ont-str-runner/work/analysis/torch_rnn_predictions.tsv")
DEFAULT_CALLS = Path("ont-str-runner/work/analysis/model_allele_calls.tsv")
DEFAULT_SUMMARY = Path("ont-str-runner/work/analysis/model_allele_summary.tsv")
CALL_FIELDS = [
    "sample",
    "split_scope",
    "truth_long",
    "truth_short",
    "raw_pred_long",
    "raw_pred_short",
    "pred_long",
    "pred_short",
    "long_error",
    "short_error",
    "support_long",
    "support_short",
    "rows_used",
    "method",
]
SUMMARY_FIELDS = ["metric", "value"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cluster per-read predictions into sample-level allele calls.")
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--calls", type=Path, default=DEFAULT_CALLS)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--method", choices=("kmeans", "label-oracle"), default="kmeans")
    parser.add_argument("--calibration", choices=("none", "train-affine"), default="none")
    parser.add_argument("--min-rows", type=int, default=20)
    parser.add_argument("--max-iterations", type=int, default=100)
    return parser.parse_args()


def to_float(value: str | None) -> float | None:
    if value in (None, "", "-"):
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    if math.isnan(parsed):
        return None
    return parsed


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def truth_for_rows(rows: list[dict[str, str]]) -> tuple[float | None, float | None]:
    targets = sorted({target for row in rows if (target := to_float(row.get("target"))) is not None})
    if len(targets) < 2:
        return None, None
    return float(targets[-1]), float(targets[0])


def split_scopes(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    scopes = {"all": rows}
    for split in sorted({row.get("split", "") for row in rows}):
        if split:
            scopes[split] = [row for row in rows if row.get("split", "") == split]
    return scopes


def kmeans_two(values: np.ndarray, max_iterations: int) -> tuple[float, float, int, int]:
    if values.size < 2:
        raise ValueError("at least two values are required")
    centers = np.asarray([np.quantile(values, 0.25), np.quantile(values, 0.75)], dtype=np.float64)
    if abs(float(centers[1] - centers[0])) < 1e-6:
        centers = np.asarray([float(values.min()), float(values.max())], dtype=np.float64)

    labels = np.zeros(values.shape[0], dtype=np.int8)
    for _ in range(max_iterations):
        distances = np.abs(values.reshape(-1, 1) - centers.reshape(1, -1))
        new_labels = np.argmin(distances, axis=1).astype(np.int8)
        new_centers = centers.copy()
        for idx in (0, 1):
            if np.any(new_labels == idx):
                new_centers[idx] = float(np.median(values[new_labels == idx]))
        if np.array_equal(labels, new_labels) and np.allclose(centers, new_centers):
            break
        labels = new_labels
        centers = new_centers

    order = np.argsort(centers)
    short_idx = int(order[0])
    long_idx = int(order[1])
    short = float(centers[short_idx])
    long = float(centers[long_idx])
    return long, short, int(np.sum(labels == long_idx)), int(np.sum(labels == short_idx))


def label_oracle(rows: list[dict[str, str]]) -> tuple[float, float, int, int]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        prediction = to_float(row.get("prediction"))
        label = row.get("label", "")
        if prediction is not None and label:
            grouped[label].append(prediction)
    if not grouped.get("long_like") or not grouped.get("short_like"):
        raise ValueError("label-oracle requires long_like and short_like predictions")
    long_values = np.asarray(grouped["long_like"], dtype=np.float64)
    short_values = np.asarray(grouped["short_like"], dtype=np.float64)
    return float(np.median(long_values)), float(np.median(short_values)), int(long_values.size), int(short_values.size)


def call_alleles(rows: list[dict[str, str]], method: str, max_iterations: int) -> tuple[float, float, int, int]:
    if method == "label-oracle":
        return label_oracle(rows)
    values = np.asarray([value for row in rows if (value := to_float(row.get("prediction"))) is not None], dtype=np.float64)
    return kmeans_two(values, max_iterations)


def round_call(value: float) -> int:
    return int(round(value))


def fit_affine(raw_calls: list[dict[str, object]], allele: str) -> tuple[float, float]:
    train = [row for row in raw_calls if row["split_scope"] == "train"]
    if len(train) < 2:
        return 0.0, 1.0
    x = np.asarray([float(row[f"raw_pred_{allele}"]) for row in train], dtype=np.float64)
    y = np.asarray([float(row[f"truth_{allele}"]) for row in train], dtype=np.float64)
    if np.unique(x).size < 2:
        return 0.0, 1.0
    design = np.column_stack([np.ones(x.shape[0]), x])
    intercept, slope = np.linalg.lstsq(design, y, rcond=None)[0]
    return float(intercept), float(slope)


def apply_calibration(value: float, coef: tuple[float, float]) -> float:
    intercept, slope = coef
    return intercept + slope * value


def mae(errors: list[float]) -> float:
    return float(np.mean(np.abs(errors))) if errors else float("nan")


def write_calls(path: Path, calls: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CALL_FIELDS, delimiter="\t")
        writer.writeheader()
        for row in calls:
            writer.writerow(row)


def write_summary(path: Path, metrics: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS, delimiter="\t")
        writer.writeheader()
        for key, value in metrics.items():
            writer.writerow({"metric": key, "value": value})


def main() -> None:
    args = parse_args()
    rows = load_rows(args.predictions)
    by_sample: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if to_float(row.get("prediction")) is not None:
            by_sample[row.get("sample", "")].append(row)

    raw_calls = []
    skipped = 0
    for sample in sorted(by_sample):
        for scope, scope_rows in split_scopes(by_sample[sample]).items():
            if len(scope_rows) < args.min_rows:
                continue
            truth_long, truth_short = truth_for_rows(scope_rows)
            if truth_long is None or truth_short is None:
                skipped += 1
                continue
            try:
                pred_long_raw, pred_short_raw, support_long, support_short = call_alleles(
                    scope_rows, args.method, args.max_iterations
                )
            except ValueError:
                skipped += 1
                continue
            pred_long = round_call(pred_long_raw)
            pred_short = round_call(pred_short_raw)
            long_error = pred_long - truth_long
            short_error = pred_short - truth_short
            raw_calls.append(
                {
                    "sample": sample,
                    "split_scope": scope,
                    "truth_long": int(round(truth_long)),
                    "truth_short": int(round(truth_short)),
                    "raw_pred_long": f"{pred_long_raw:.3f}",
                    "raw_pred_short": f"{pred_short_raw:.3f}",
                    "pred_long": pred_long,
                    "pred_short": pred_short,
                    "long_error": int(round(long_error)),
                    "short_error": int(round(short_error)),
                    "support_long": support_long,
                    "support_short": support_short,
                    "rows_used": len(scope_rows),
                    "method": args.method,
                }
            )

    if args.calibration == "train-affine":
        long_coef = fit_affine(raw_calls, "long")
        short_coef = fit_affine(raw_calls, "short")
    else:
        long_coef = (0.0, 1.0)
        short_coef = (0.0, 1.0)

    calls = []
    errors_by_scope: dict[str, dict[str, list[float]]] = defaultdict(lambda: {"long": [], "short": [], "overall": []})
    for row in raw_calls:
        truth_long = float(row["truth_long"])
        truth_short = float(row["truth_short"])
        pred_long = round_call(apply_calibration(float(row["raw_pred_long"]), long_coef))
        pred_short = round_call(apply_calibration(float(row["raw_pred_short"]), short_coef))
        long_error = pred_long - truth_long
        short_error = pred_short - truth_short
        row = dict(row)
        row["pred_long"] = pred_long
        row["pred_short"] = pred_short
        row["long_error"] = int(round(long_error))
        row["short_error"] = int(round(short_error))
        calls.append(row)
        scope = str(row["split_scope"])
        errors_by_scope[scope]["long"].append(float(long_error))
        errors_by_scope[scope]["short"].append(float(short_error))
        errors_by_scope[scope]["overall"].extend([float(long_error), float(short_error)])

    metrics: dict[str, object] = {
        "predictions": str(args.predictions),
        "method": args.method,
        "calibration": args.calibration,
        "long_calibration_intercept": f"{long_coef[0]:.6f}",
        "long_calibration_slope": f"{long_coef[1]:.6f}",
        "short_calibration_intercept": f"{short_coef[0]:.6f}",
        "short_calibration_slope": f"{short_coef[1]:.6f}",
        "sample_scopes_called": len(calls),
        "sample_scopes_skipped": skipped,
        "min_rows": args.min_rows,
    }
    for scope in sorted(errors_by_scope):
        metrics[f"{scope}_samples"] = len(errors_by_scope[scope]["long"])
        metrics[f"{scope}_long_mae"] = f"{mae(errors_by_scope[scope]['long']):.3f}"
        metrics[f"{scope}_short_mae"] = f"{mae(errors_by_scope[scope]['short']):.3f}"
        metrics[f"{scope}_overall_allele_mae"] = f"{mae(errors_by_scope[scope]['overall']):.3f}"

    write_calls(args.calls, calls)
    write_summary(args.summary, metrics)
    print(f"Wrote allele calls to {args.calls}")
    print(f"Wrote summary to {args.summary}")
    if "test" in errors_by_scope:
        print(f"Test allele MAE: {metrics['test_overall_allele_mae']}")
    if "all" in errors_by_scope:
        print(f"All-sample allele MAE: {metrics['all_overall_allele_mae']}")


if __name__ == "__main__":
    main()
