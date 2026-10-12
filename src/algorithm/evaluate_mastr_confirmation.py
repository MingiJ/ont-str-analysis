#!/usr/bin/env python3
"""Run the frozen independent MASTR-seq HTT confirmation gate.

Prediction and scoring are separate subcommands.  Prediction refuses embedded
truth, requires the predeclared four-sample cohort, and requires at least six
QC-passing raw-signal rows per sample.  Only the fixed normalized ACF feature
can pass or fail the gate; raw duration is reported as a diagnostic only.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import numpy as np

try:
    from evaluate_external_confirmation import (
        PREDICTION_FIELDS,
        SCORE_FIELDS,
        load_external_truth,
        predict,
        score_predictions,
    )
    from evaluate_repeat_duration_loso import read_tsv, write_tsv
except ImportError:  # pragma: no cover
    from .evaluate_external_confirmation import (
        PREDICTION_FIELDS,
        SCORE_FIELDS,
        load_external_truth,
        predict,
        score_predictions,
    )
    from .evaluate_repeat_duration_loso import read_tsv, write_tsv


EXPECTED_SAMPLES = ("MASTR_P", "MASTR_N", "MASTR_E1", "MASTR_E2")
EXPANDED_SAMPLES = ("MASTR_E1", "MASTR_E2")
PRIMARY_FEATURE = "acf_period_normalized"
DIAGNOSTIC_FEATURE = "duration"
MIN_ROWS_PER_SAMPLE = 6
POOLED_ALLELE_MAE_MAX = 3.0
EXPANDED_LONG_ABS_ERROR_MAX = 5.0

DEFAULT_DEVELOPMENT_INDEX = Path(
    "ont-str-runner/work/analysis/signal_repeat_windows_independent_qc_dev.index.tsv"
)
DEFAULT_DEVELOPMENT_ARCHIVE = Path(
    "ont-str-runner/work/analysis/signal_repeat_windows_independent_qc_dev.npz"
)
DEFAULT_TRUTH_MANIFEST = Path("ont-str-runner/configs/mastr_confirmation_truth.tsv")
DECISION_FIELDS = ["metric", "role", "value", "threshold", "pass"]


def validate_external_cohort(
    metadata: list[dict[str, str]],
    *,
    expected_samples: tuple[str, ...] = EXPECTED_SAMPLES,
    min_rows_per_sample: int = MIN_ROWS_PER_SAMPLE,
) -> None:
    counts = Counter(row.get("sample", "").strip() for row in metadata)
    counts.pop("", None)
    expected = set(expected_samples)
    actual = set(counts)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(f"external cohort mismatch: missing={missing}, extra={extra}")
    below = {sample: counts[sample] for sample in expected_samples if counts[sample] < min_rows_per_sample}
    if below:
        raise ValueError(
            f"external samples below frozen minimum of {min_rows_per_sample} QC rows: {below}"
        )


def _one_row_per_sample_feature(
    scored: list[dict[str, str]], feature: str
) -> dict[str, dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in scored:
        if row.get("feature") == feature:
            grouped.setdefault(row.get("sample", ""), []).append(row)
    duplicates = sorted(sample for sample, rows in grouped.items() if len(rows) != 1)
    if duplicates:
        raise ValueError(f"duplicate {feature} score rows for: {', '.join(duplicates)}")
    return {sample: rows[0] for sample, rows in grouped.items()}


def build_mastr_decision(scored: list[dict[str, str]]) -> tuple[list[dict[str, object]], bool]:
    primary = _one_row_per_sample_feature(scored, PRIMARY_FEATURE)
    if set(primary) != set(EXPECTED_SAMPLES):
        raise ValueError(
            f"primary score cohort mismatch: expected={list(EXPECTED_SAMPLES)}, "
            f"found={sorted(primary)}"
        )

    pooled_mae = float(np.mean([float(primary[sample]["allele_mae"]) for sample in EXPECTED_SAMPLES]))
    expanded_mae = float(
        np.mean([float(primary[sample]["allele_mae"]) for sample in EXPANDED_SAMPLES])
    )
    expanded_long_errors = [
        float(primary[sample]["long_abs_error"]) for sample in EXPANDED_SAMPLES
    ]
    max_expanded_long_error = max(expanded_long_errors)

    control_calls = []
    for sample in ("MASTR_P", "MASTR_N"):
        control_calls.append(
            sorted(
                (
                    float(primary[sample]["pred_short"]),
                    float(primary[sample]["pred_long"]),
                )
            )
        )
    control_prediction_delta = float(
        np.mean(np.abs(np.asarray(control_calls[0]) - np.asarray(control_calls[1])))
    )

    diagnostic = _one_row_per_sample_feature(scored, DIAGNOSTIC_FEATURE)
    diagnostic_pooled_mae = (
        float(np.mean([float(diagnostic[sample]["allele_mae"]) for sample in EXPECTED_SAMPLES]))
        if set(diagnostic) == set(EXPECTED_SAMPLES)
        else float("nan")
    )

    pooled_pass = pooled_mae <= POOLED_ALLELE_MAE_MAX
    expanded_pass = max_expanded_long_error <= EXPANDED_LONG_ABS_ERROR_MAX
    gate_pass = pooled_pass and expanded_pass
    rows: list[dict[str, object]] = [
        {
            "metric": "acf_all_sample_pooled_allele_mae",
            "role": "primary_gate",
            "value": f"{pooled_mae:.6f}",
            "threshold": f"<= {POOLED_ALLELE_MAE_MAX:.6f}",
            "pass": int(pooled_pass),
        },
        {
            "metric": "acf_max_expanded_long_abs_error",
            "role": "primary_gate",
            "value": f"{max_expanded_long_error:.6f}",
            "threshold": f"<= {EXPANDED_LONG_ABS_ERROR_MAX:.6f}",
            "pass": int(expanded_pass),
        },
        {
            "metric": "acf_expanded_only_allele_mae",
            "role": "supporting",
            "value": f"{expanded_mae:.6f}",
            "threshold": "",
            "pass": "",
        },
        {
            "metric": "acf_parental_normal_prediction_delta",
            "role": "control_reproducibility",
            "value": f"{control_prediction_delta:.6f}",
            "threshold": "",
            "pass": "",
        },
        {
            "metric": "duration_all_sample_pooled_allele_mae",
            "role": "diagnostic_only",
            "value": "" if np.isnan(diagnostic_pooled_mae) else f"{diagnostic_pooled_mae:.6f}",
            "threshold": "not_gating",
            "pass": "",
        },
        {
            "metric": "frozen_independent_mastr_gate",
            "role": "decision",
            "value": "pass" if gate_pass else "fail",
            "threshold": "both_primary_gates_pass",
            "pass": int(gate_pass),
        },
    ]
    return rows, gate_pass


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
    score_parser.add_argument("--decision", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "predict":
        development_metadata = read_tsv(args.development_index)
        external_metadata = read_tsv(args.external_index)
        validate_external_cohort(external_metadata)
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
        for row in rows:
            if int(row["external_rows"]) < MIN_ROWS_PER_SAMPLE:
                raise ValueError(
                    f"{row['sample']} {row['feature']} has fewer than {MIN_ROWS_PER_SAMPLE} usable rows"
                )
            row["status"] = (
                "primary_frozen_independent_mastr"
                if row["feature"] == PRIMARY_FEATURE
                else "diagnostic_independent_mastr_not_gating"
            )
        write_tsv(args.output, rows, PREDICTION_FIELDS)
        print(f"Wrote sealed MASTR predictions to {args.output}")
        return

    predictions = read_tsv(args.predictions)
    truth = load_external_truth(args.truth_manifest)
    if set(truth) != set(EXPECTED_SAMPLES):
        raise ValueError(
            f"truth cohort mismatch: expected={list(EXPECTED_SAMPLES)}, found={sorted(truth)}"
        )
    scored, summary = score_predictions(predictions, truth)
    decision, gate_pass = build_mastr_decision(scored)
    write_tsv(args.output, scored, SCORE_FIELDS)
    write_tsv(args.summary, summary, ["feature", "external_samples", "allele_mae"])
    write_tsv(args.decision, decision, DECISION_FIELDS)
    print(f"Wrote MASTR scores to {args.output}")
    print(f"Wrote MASTR score summary to {args.summary}")
    print(f"Wrote frozen decision to {args.decision}; gate={'pass' if gate_pass else 'fail'}")


if __name__ == "__main__":
    main()
