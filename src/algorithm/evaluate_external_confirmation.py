#!/usr/bin/env python3
"""Predict, then separately score, the frozen external HTT confirmation set.

``predict`` refuses external metadata that contains genotype truth. It fits the
duration and fixed ACF-normalized calibrations on the nine development samples
and writes external calls. ``score`` is a separate operation that opens the
Coriell truth manifest and never refits a model. This split makes accidental
external-label leakage auditable.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

try:
    from evaluate_repeat_duration_loso import read_tsv, write_tsv
    from evaluate_repeat_periodicity_loso import FEATURES, feature_values
    from weak_supervised_rnn import fit_duration_prior, truth_pairs_from_metadata, two_cluster_medians
except ImportError:  # pragma: no cover
    from .evaluate_repeat_duration_loso import read_tsv, write_tsv
    from .evaluate_repeat_periodicity_loso import FEATURES, feature_values
    from .weak_supervised_rnn import fit_duration_prior, truth_pairs_from_metadata, two_cluster_medians


DEFAULT_DEVELOPMENT_INDEX = Path(
    "ont-str-runner/work/analysis/signal_repeat_windows_independent_qc_dev.index.tsv"
)
DEFAULT_DEVELOPMENT_ARCHIVE = Path(
    "ont-str-runner/work/analysis/signal_repeat_windows_independent_qc_dev.npz"
)
DEFAULT_TRUTH_MANIFEST = Path(
    "ont-str-runner/configs/external_confirmation_samples.tsv"
)
PREDICTION_FIELDS = [
    "sample",
    "feature",
    "pred_short",
    "pred_long",
    "low_feature_centre",
    "high_feature_centre",
    "calibration_intercept",
    "calibration_slope",
    "development_calibration_rmse",
    "development_samples",
    "external_rows",
    "status",
]
SCORE_FIELDS = [
    "sample",
    "feature",
    "truth_short",
    "truth_long",
    "pred_short",
    "pred_long",
    "short_abs_error",
    "long_abs_error",
    "allele_mae",
]


def assert_external_truth_is_hidden(metadata: list[dict[str, str]]) -> None:
    leaked = []
    for row in metadata:
        if row.get("truth_short", "").strip() or row.get("truth_long", "").strip():
            leaked.append(row.get("sample", "<unknown>"))
    if leaked:
        raise ValueError(
            "external prediction index contains genotype truth for: "
            + ", ".join(sorted(set(leaked)))
        )


def predict_from_features(
    development_features: dict[str, dict[str, np.ndarray]],
    development_truth: dict[str, tuple[float, float]],
    external_features: dict[str, dict[str, np.ndarray]],
) -> list[dict[str, object]]:
    train_samples = sorted(development_truth)
    rows = []
    external_samples = sorted(
        set.intersection(*(set(external_features[name]) for name in FEATURES))
    )
    if not external_samples:
        raise ValueError("no external sample has both frozen features")

    for feature in FEATURES:
        missing_development = sorted(set(train_samples) - set(development_features[feature]))
        if missing_development:
            raise ValueError(
                f"development feature {feature} is missing: {', '.join(missing_development)}"
            )
        intercept, slope, _, rmse = fit_duration_prior(
            development_features[feature], development_truth, train_samples
        )
        for sample in external_samples:
            values = external_features[feature][sample]
            low, high = two_cluster_medians(values)
            rows.append(
                {
                    "sample": sample,
                    "feature": feature,
                    "pred_short": f"{intercept + slope * low:.6f}",
                    "pred_long": f"{intercept + slope * high:.6f}",
                    "low_feature_centre": f"{low:.6f}",
                    "high_feature_centre": f"{high:.6f}",
                    "calibration_intercept": f"{intercept:.9f}",
                    "calibration_slope": f"{slope:.9f}",
                    "development_calibration_rmse": f"{rmse:.6f}",
                    "development_samples": len(train_samples),
                    "external_rows": int(values.size),
                    "status": (
                        "confirmatory_frozen_duration"
                        if feature == "duration"
                        else "confirmatory_frozen_acf_parameters"
                    ),
                }
            )
    return rows


def predict(
    development_metadata: list[dict[str, str]],
    development_signal: np.ndarray,
    external_metadata: list[dict[str, str]],
    external_signal: np.ndarray,
    *,
    expected_development_samples: int = 9,
) -> list[dict[str, object]]:
    assert_external_truth_is_hidden(external_metadata)
    development_truth = truth_pairs_from_metadata(development_metadata)
    if expected_development_samples and len(development_truth) != expected_development_samples:
        raise ValueError(
            f"expected {expected_development_samples} development samples, "
            f"found {len(development_truth)}"
        )
    development_features, _, _ = feature_values(development_metadata, development_signal)
    external_features, _, _ = feature_values(external_metadata, external_signal)
    return predict_from_features(development_features, development_truth, external_features)


def load_external_truth(path: Path) -> dict[str, tuple[float, float]]:
    grouped: dict[str, set[tuple[float, float]]] = defaultdict(set)
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            sample = row.get("sample", "").strip()
            if not sample:
                continue
            try:
                pair = tuple(sorted((float(row["truth_short"]), float(row["truth_long"]))))
            except (KeyError, TypeError, ValueError):
                continue
            grouped[sample].add(pair)
    inconsistent = sorted(sample for sample, pairs in grouped.items() if len(pairs) != 1)
    if inconsistent:
        raise ValueError(f"inconsistent truth rows for: {', '.join(inconsistent)}")
    return {sample: next(iter(pairs)) for sample, pairs in grouped.items()}


def score_predictions(
    predictions: list[dict[str, str]],
    truth: dict[str, tuple[float, float]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    scored = []
    by_feature: dict[str, list[float]] = defaultdict(list)
    for row in predictions:
        sample = row.get("sample", "")
        feature = row.get("feature", "")
        if sample not in truth:
            raise ValueError(f"missing external truth for prediction sample {sample}")
        truth_short, truth_long = truth[sample]
        predicted = sorted((float(row["pred_short"]), float(row["pred_long"])))
        short_error = abs(predicted[0] - truth_short)
        long_error = abs(predicted[1] - truth_long)
        allele_mae = float(np.mean([short_error, long_error]))
        by_feature[feature].append(allele_mae)
        scored.append(
            {
                "sample": sample,
                "feature": feature,
                "truth_short": f"{truth_short:.6f}",
                "truth_long": f"{truth_long:.6f}",
                "pred_short": f"{predicted[0]:.6f}",
                "pred_long": f"{predicted[1]:.6f}",
                "short_abs_error": f"{short_error:.6f}",
                "long_abs_error": f"{long_error:.6f}",
                "allele_mae": f"{allele_mae:.6f}",
            }
        )
    summary = [
        {"feature": feature, "external_samples": len(errors), "allele_mae": f"{np.mean(errors):.6f}"}
        for feature, errors in sorted(by_feature.items())
    ]
    return scored, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    predict_parser = subparsers.add_parser("predict")
    predict_parser.add_argument("--development-index", type=Path, default=DEFAULT_DEVELOPMENT_INDEX)
    predict_parser.add_argument("--development-archive", type=Path, default=DEFAULT_DEVELOPMENT_ARCHIVE)
    predict_parser.add_argument("--external-index", type=Path, required=True)
    predict_parser.add_argument("--external-archive", type=Path, required=True)
    predict_parser.add_argument("--output", type=Path, required=True)
    predict_parser.add_argument("--expected-development-samples", type=int, default=9)

    score_parser = subparsers.add_parser("score")
    score_parser.add_argument("--predictions", type=Path, required=True)
    score_parser.add_argument("--truth-manifest", type=Path, default=DEFAULT_TRUTH_MANIFEST)
    score_parser.add_argument("--output", type=Path, required=True)
    score_parser.add_argument("--summary", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "predict":
        development_metadata = read_tsv(args.development_index)
        external_metadata = read_tsv(args.external_index)
        with np.load(args.development_archive) as archive:
            development_signal = archive["signal"]
        with np.load(args.external_archive) as archive:
            external_signal = archive["signal"]
        rows = predict(
            development_metadata,
            development_signal,
            external_metadata,
            external_signal,
            expected_development_samples=args.expected_development_samples,
        )
        write_tsv(args.output, rows, PREDICTION_FIELDS)
        print(f"Wrote sealed external predictions to {args.output}")
        return

    predictions = read_tsv(args.predictions)
    truth = load_external_truth(args.truth_manifest)
    scored, summary = score_predictions(predictions, truth)
    write_tsv(args.output, scored, SCORE_FIELDS)
    write_tsv(args.summary, summary, ["feature", "external_samples", "allele_mae"])
    print(f"Wrote external scores to {args.output}")
    print(f"Wrote external score summary to {args.summary}")


if __name__ == "__main__":
    main()
