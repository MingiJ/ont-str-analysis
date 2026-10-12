#!/usr/bin/env python3
"""Train the current algorithm and emit sample-level allele calls.

This is the reusable caller for the thesis algorithm checkpoint. It trains the
NumPy MLP on all labeled truth windows in an input signal archive, predicts
repeat counts for every read, clusters per-read predictions into two alleles
per sample, calibrates allele calls from labeled samples, and applies the
tail-span correction for out-of-range long alleles.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

try:
    from dataset import DEFAULT_INDEX, DEFAULT_SIGNAL_ARCHIVE, combined_signal_features, load_signal_dataset
    from evaluate_allele_calls import kmeans_two as cluster_two_predictions
    from neural_baseline import (
        add_group_metrics,
        copy_params,
        forward,
        init_adam,
        init_params,
        label_weights,
        mae,
        standardize,
        train_epoch,
        validation_split,
        write_predictions,
        write_summary,
    )
except ImportError:  # pragma: no cover
    from .dataset import DEFAULT_INDEX, DEFAULT_SIGNAL_ARCHIVE, combined_signal_features, load_signal_dataset
    from .evaluate_allele_calls import kmeans_two as cluster_two_predictions
    from .neural_baseline import (
        add_group_metrics,
        copy_params,
        forward,
        init_adam,
        init_params,
        label_weights,
        mae,
        standardize,
        train_epoch,
        validation_split,
        write_predictions,
        write_summary,
    )


DEFAULT_PREDICTIONS = Path("ont-str-runner/work/analysis/algorithm_predictions.tsv")
DEFAULT_CALLS = Path("ont-str-runner/work/analysis/algorithm_allele_calls.tsv")
DEFAULT_SUMMARY = Path("ont-str-runner/work/analysis/algorithm_summary.tsv")
CALL_FIELDS = [
    "sample",
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
    "support_long_fraction",
    "support_short_fraction",
    "confidence",
    "confidence_reason",
    "rows_available",
    "rows_used",
    "rows_quality_filtered",
    "median_mapq",
    "unresolved_alleles",
    "consensus_raw",
    "tail_span_applied",
    "tail_span_raw_long",
    "tail_span_long_span",
    "tail_span_anchors",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train current STR algorithm and call sample-level alleles.")
    parser.add_argument("--signal-archive", type=Path, default=DEFAULT_SIGNAL_ARCHIVE)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--calls", type=Path, default=DEFAULT_CALLS)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--bins", type=int, default=128)
    parser.add_argument("--hidden-dim", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=250)
    parser.add_argument("--learning-rate", type=float, default=0.01)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--validation-fraction", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--min-rows", type=int, default=20)
    parser.add_argument(
        "--external-min-mapq",
        type=int,
        default=20,
        help="Exclude lower-MAPQ reads from unlabeled external samples when MAPQ is available.",
    )
    parser.add_argument(
        "--external-min-raw-separation",
        type=float,
        default=5.0,
        help="Report an unresolved consensus when external raw clusters are closer than this.",
    )
    parser.add_argument("--no-balance", action="store_true")
    parser.add_argument("--no-tail-span-correction", action="store_true")
    return parser.parse_args()


def to_float(value: str | None) -> float | None:
    if value in (None, "", "-"):
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    if np.isnan(parsed):
        return None
    return parsed


def write_calls(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CALL_FIELDS, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def index_spans(metadata: list[dict[str, str]]) -> dict[str, tuple[float, float]]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in metadata:
        span = to_float(row.get("stored_len"))
        if span is not None:
            grouped[row.get("sample", "")].append(span)
    spans: dict[str, tuple[float, float]] = {}
    for sample, values in grouped.items():
        if len(values) >= 2:
            long_span, short_span, _, _ = cluster_two_predictions(np.asarray(values, dtype=np.float64), 100)
            spans[sample] = (long_span, short_span)
    return spans


def sample_truth(metadata: list[dict[str, str]]) -> dict[str, tuple[float, float]]:
    truth: dict[str, tuple[float, float]] = {}
    for row in metadata:
        long_value = to_float(row.get("truth_long"))
        short_value = to_float(row.get("truth_short"))
        sample = row.get("sample", "")
        if long_value is not None and short_value is not None:
            truth[sample] = (long_value, short_value)
    return truth


def split_for_full_training(labels: np.ndarray, train: np.ndarray, validation_fraction: float) -> tuple[np.ndarray, np.ndarray]:
    return validation_split(labels, train, validation_fraction)


def fit_affine(calls: list[dict[str, object]], truth: dict[str, tuple[float, float]], allele: str) -> tuple[float, float]:
    idx = 0 if allele == "long" else 1
    rows = [row for row in calls if row["sample"] in truth]
    if len(rows) < 2:
        return (0.0, 1.0)
    x = np.asarray([float(row[f"raw_pred_{allele}"]) for row in rows], dtype=np.float64)
    y = np.asarray([truth[str(row["sample"])][idx] for row in rows], dtype=np.float64)
    if np.unique(x).size < 2:
        return (0.0, 1.0)
    design = np.column_stack([np.ones(x.shape[0]), x])
    intercept, slope = np.linalg.lstsq(design, y, rcond=None)[0]
    return float(intercept), float(slope)


def calibrated(value: float, coef: tuple[float, float]) -> int:
    intercept, slope = coef
    return int(round(intercept + slope * value))


def apply_tail_span(
    row: dict[str, object],
    spans: dict[str, tuple[float, float]],
    truth: dict[str, tuple[float, float]],
) -> dict[str, object]:
    sample = str(row["sample"])
    row["tail_span_applied"] = "False"
    row["tail_span_raw_long"] = row["pred_long"]
    row["tail_span_long_span"] = f"{spans[sample][0]:.3f}" if sample in spans else ""
    row["tail_span_anchors"] = ""
    if sample not in truth:
        return row
    train = [name for name in truth if name != sample and name in spans]
    if sample not in spans or len(train) < 3:
        return row
    if spans[sample][0] <= max(spans[name][0] for name in train):
        return row

    anchors = sorted(train, key=lambda name: spans[name][0])[-3:]
    design = np.column_stack([np.ones(len(anchors)), [spans[name][0] for name in anchors]])
    target = np.asarray([truth[name][0] for name in anchors], dtype=np.float64)
    intercept, slope = np.linalg.lstsq(design, target, rcond=None)[0]
    corrected = int(round(float(intercept + slope * spans[sample][0])))
    row["pred_long"] = corrected
    row["tail_span_applied"] = "True"
    row["tail_span_anchors"] = ";".join(f"{name}:{spans[name][0]:.1f}:{truth[name][0]:.0f}" for name in anchors)
    return row


def add_confidence(row: dict[str, object]) -> dict[str, object]:
    rows_used = int(row["rows_used"])
    support_long = int(row["support_long"])
    support_short = int(row["support_short"])
    long_fraction = support_long / rows_used if rows_used else 0.0
    short_fraction = support_short / rows_used if rows_used else 0.0
    row["support_long_fraction"] = f"{long_fraction:.3f}"
    row["support_short_fraction"] = f"{short_fraction:.3f}"

    reasons = []
    confidence = "high"
    if rows_used < 100:
        confidence = "moderate"
        reasons.append("small_read_count")
    if min(long_fraction, short_fraction) < 0.20:
        confidence = "low"
        reasons.append("low_minor_allele_support")
    elif min(long_fraction, short_fraction) < 0.30 and confidence == "high":
        confidence = "moderate"
        reasons.append("moderate_minor_allele_support")
    if abs(int(row["pred_long"]) - int(row["pred_short"])) < 3:
        confidence = "low"
        reasons.append("unresolved_allele_separation")
    if int(row.get("rows_quality_filtered", 0)):
        reasons.append("mapping_quality_filtering")
    row["confidence"] = confidence
    row["confidence_reason"] = ";".join(reasons) if reasons else "balanced_support"
    return row


def call_samples(
    metadata: list[dict[str, str]],
    predictions: np.ndarray,
    truth: dict[str, tuple[float, float]],
    spans: dict[str, tuple[float, float]],
    min_rows: int,
    use_tail_span: bool,
    external_min_mapq: int | None = 20,
    external_min_raw_separation: float = 5.0,
) -> list[dict[str, object]]:
    grouped: dict[str, list[float]] = defaultdict(list)
    rows_available: Counter[str] = Counter()
    rows_quality_filtered: Counter[str] = Counter()
    included_mapq: dict[str, list[float]] = defaultdict(list)
    for row, prediction in zip(metadata, predictions):
        if np.isnan(prediction):
            continue
        sample = row.get("sample", "")
        rows_available[sample] += 1
        mapq = to_float(row.get("mapq"))
        if (
            sample not in truth
            and external_min_mapq is not None
            and mapq is not None
            and mapq < external_min_mapq
        ):
            rows_quality_filtered[sample] += 1
            continue
        grouped[sample].append(float(prediction))
        if mapq is not None:
            included_mapq[sample].append(mapq)

    raw_calls = []
    for sample in sorted(grouped):
        if len(grouped[sample]) < min_rows:
            continue
        long_raw, short_raw, support_long, support_short = cluster_two_predictions(
            np.asarray(grouped[sample], dtype=np.float64), 100
        )
        raw_calls.append(
            {
                "sample": sample,
                "truth_long": "" if sample not in truth else int(round(truth[sample][0])),
                "truth_short": "" if sample not in truth else int(round(truth[sample][1])),
                "raw_pred_long": f"{long_raw:.3f}",
                "raw_pred_short": f"{short_raw:.3f}",
                "support_long": support_long,
                "support_short": support_short,
                "rows_available": rows_available[sample],
                "rows_used": len(grouped[sample]),
                "rows_quality_filtered": rows_quality_filtered[sample],
                "median_mapq": (
                    f"{float(np.median(included_mapq[sample])):.1f}"
                    if included_mapq[sample]
                    else ""
                ),
            }
        )

    long_coef = fit_affine(raw_calls, truth, "long")
    short_coef = fit_affine(raw_calls, truth, "short")
    calls = []
    for row in raw_calls:
        sample = str(row["sample"])
        pred_long = calibrated(float(row["raw_pred_long"]), long_coef)
        pred_short = calibrated(float(row["raw_pred_short"]), short_coef)
        row["unresolved_alleles"] = "False"
        row["consensus_raw"] = ""
        raw_separation = float(row["raw_pred_long"]) - float(row["raw_pred_short"])
        if sample not in truth and raw_separation < external_min_raw_separation:
            consensus_raw = float(np.median(grouped[sample]))
            consensus = calibrated(consensus_raw, short_coef)
            pred_long = consensus
            pred_short = consensus
            row["unresolved_alleles"] = "True"
            row["consensus_raw"] = f"{consensus_raw:.3f}"
        row["pred_long"] = pred_long
        row["pred_short"] = pred_short
        if sample in truth:
            row["long_error"] = int(round(pred_long - truth[sample][0]))
            row["short_error"] = int(round(pred_short - truth[sample][1]))
        else:
            row["long_error"] = ""
            row["short_error"] = ""
        row = apply_tail_span(row, spans, truth) if use_tail_span else row
        if sample in truth:
            row["long_error"] = int(round(int(row["pred_long"]) - truth[sample][0]))
            row["short_error"] = int(round(int(row["pred_short"]) - truth[sample][1]))
        calls.append(add_confidence(row))
    return calls


def allele_mae_metrics(calls: list[dict[str, object]]) -> dict[str, object]:
    long_errors = []
    short_errors = []
    for row in calls:
        long_error = to_float(str(row.get("long_error", "")))
        short_error = to_float(str(row.get("short_error", "")))
        if long_error is not None:
            long_errors.append(long_error)
        if short_error is not None:
            short_errors.append(short_error)
    overall = long_errors + short_errors
    return {
        "allele_samples_evaluated": len(long_errors),
        "allele_long_mae": f"{mae(np.asarray(long_errors, dtype=np.float32)):.3f}",
        "allele_short_mae": f"{mae(np.asarray(short_errors, dtype=np.float32)):.3f}",
        "allele_overall_mae": f"{mae(np.asarray(overall, dtype=np.float32)):.3f}",
    }


def main() -> None:
    args = parse_args()
    if args.bins < 2:
        raise SystemExit("--bins must be at least 2")
    if args.hidden_dim < 1:
        raise SystemExit("--hidden-dim must be at least 1")

    dataset = load_signal_dataset(args.signal_archive, args.index)
    train = dataset.target_mask.copy()
    fit, validation = split_for_full_training(dataset.label, train, args.validation_fraction)
    if not np.any(fit):
        raise SystemExit("No labeled fitting rows found.")

    features, feature_names = combined_signal_features(dataset, args.bins)
    fit_features, all_features, _, _ = standardize(features[fit], features)
    weights = np.ones(int(fit.sum()), dtype=np.float32) if args.no_balance else label_weights(dataset.label[fit])

    rng = np.random.default_rng(args.seed)
    params = init_params(features.shape[1], args.hidden_dim, rng)
    state = init_adam(params)
    best_params = copy_params(params)
    best_epoch = 0
    best_validation_mae = float("inf")
    losses = []
    for epoch in range(1, args.epochs + 1):
        loss = train_epoch(
            params,
            state,
            fit_features.astype(np.float32),
            dataset.target[fit],
            weights,
            args.learning_rate,
            epoch,
            args.weight_decay,
        )
        losses.append(loss)
        if np.any(validation):
            _, current = forward(params, all_features.astype(np.float32))
            validation_mae = mae(current[validation] - dataset.target[validation])
        else:
            validation_mae = loss
        if validation_mae < best_validation_mae:
            best_validation_mae = validation_mae
            best_epoch = epoch
            best_params = copy_params(params)

    _, predictions = forward(best_params, all_features.astype(np.float32))
    not_train = ~train
    write_predictions(args.predictions, dataset.metadata, dataset.label, dataset.target, predictions, train, not_train)

    truth = sample_truth(dataset.metadata)
    spans = index_spans(dataset.metadata)
    calls = call_samples(
        dataset.metadata,
        predictions,
        truth,
        spans,
        args.min_rows,
        use_tail_span=not args.no_tail_span_correction,
        external_min_mapq=args.external_min_mapq,
        external_min_raw_separation=args.external_min_raw_separation,
    )
    write_calls(args.calls, calls)

    train_errors = predictions[train] - dataset.target[train]
    metrics: dict[str, object] = {
        "rows_total": dataset.signal.shape[0],
        "rows_labeled": int(train.sum()),
        "rows_unlabeled": int((~train).sum()),
        "rows_fit": int(fit.sum()),
        "rows_validation": int(validation.sum()),
        "bins": args.bins,
        "feature_dim": features.shape[1],
        "feature_names": ",".join(feature_names),
        "hidden_dim": args.hidden_dim,
        "epochs": args.epochs,
        "learning_rate": args.learning_rate,
        "weight_decay": args.weight_decay,
        "seed": args.seed,
        "balanced_training": str(not args.no_balance),
        "tail_span_correction": str(not args.no_tail_span_correction),
        "external_min_mapq": args.external_min_mapq,
        "external_min_raw_separation": args.external_min_raw_separation,
        "initial_train_loss": f"{losses[0]:.3f}",
        "final_train_loss": f"{losses[-1]:.3f}",
        "best_epoch": best_epoch,
        "validation_mae_at_best_epoch": f"{best_validation_mae:.3f}",
        "train_mae": f"{mae(train_errors):.3f}",
        "label_counts": ";".join(f"{k}:{v}" for k, v in sorted(Counter(dataset.label[train]).items())),
        "samples_called": len(calls),
        "note": "Current algorithm caller: NumPy MLP, allele clustering, train-sample calibration, optional tail-span correction.",
    }
    metrics.update(allele_mae_metrics(calls))
    add_group_metrics(metrics, "train", dataset.metadata, dataset.label, dataset.target, predictions, train)
    write_summary(args.summary, metrics)
    print(f"Wrote predictions to {args.predictions}")
    print(f"Wrote allele calls to {args.calls}")
    print(f"Wrote summary to {args.summary}")


if __name__ == "__main__":
    main()
