#!/usr/bin/env python3
"""Run nested leave-one-sample-out evaluation for the weak RNN experiment.

Every outer fold has one untouched test sample. ``weak_supervised_rnn.py``
then selects a different sample for validation, leaving the remaining labelled
samples for optimization. The default 64-read cap is a development screen;
pass ``--max-rows-per-sample 0`` for the full archive.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

import numpy as np

try:
    from dataset import DEFAULT_INDEX, DEFAULT_SIGNAL_ARCHIVE
    from weak_supervised_rnn import truth_pairs_from_metadata
except ImportError:  # pragma: no cover
    from .dataset import DEFAULT_INDEX, DEFAULT_SIGNAL_ARCHIVE
    from .weak_supervised_rnn import truth_pairs_from_metadata


DEFAULT_OUTPUT_DIR = Path("ont-str-runner/work/analysis/weak_supervised_rnn_loso_dev")
FOLD_FIELDS = [
    "holdout_sample",
    "validation_sample",
    "truth_short",
    "truth_long",
    "resolved",
    "pred_short",
    "pred_long",
    "candidate_short",
    "candidate_long",
    "candidate_short_error",
    "candidate_long_error",
    "candidate_allele_mae",
    "resolved_allele_mae",
    "mixture_confidence",
    "reason",
    "best_epoch",
]


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def read_metrics(path: Path) -> dict[str, str]:
    return {row["metric"]: row["value"] for row in read_tsv(path)}


def write_tsv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Nested LOSO evaluation for weak_supervised_rnn.py")
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--signal-archive", type=Path, default=DEFAULT_SIGNAL_ARCHIVE)
    parser.add_argument("--algorithm", type=Path, default=Path("src/algorithm/weak_supervised_rnn.py"))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--samples", nargs="*", default=None)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="cpu")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--bag-size", type=int, default=32)
    parser.add_argument("--bags-per-sample", type=int, default=2)
    parser.add_argument("--prediction-batch-size", type=int, default=64)
    parser.add_argument("--hidden-dim", type=int, default=16)
    parser.add_argument("--conv-channels", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=0.003)
    parser.add_argument("--min-component-fraction", type=float, default=0.30)
    parser.add_argument("--caller-min-component-fraction", type=float, default=0.20)
    parser.add_argument("--max-rows-per-sample", type=int, default=64)
    parser.add_argument("--skip-existing", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metadata = read_tsv(args.index)
    truth_pairs = truth_pairs_from_metadata(metadata)
    samples = sorted(args.samples or truth_pairs)
    unknown = sorted(set(samples) - set(truth_pairs))
    if unknown:
        raise SystemExit(f"samples without diploid truth: {', '.join(unknown)}")
    if len(samples) < 3:
        raise SystemExit("at least three labelled samples are required")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    fold_rows: list[dict[str, object]] = []
    for holdout in samples:
        prefix = args.output_dir / holdout
        predictions_path = prefix.with_suffix(".predictions.tsv")
        calls_path = prefix.with_suffix(".calls.tsv")
        summary_path = prefix.with_suffix(".summary.tsv")
        checkpoint_path = prefix.with_suffix(".pt")
        if not (args.skip_existing and calls_path.exists() and summary_path.exists()):
            command = [
                sys.executable,
                str(args.algorithm),
                "--index",
                str(args.index),
                "--signal-archive",
                str(args.signal_archive),
                "--holdout-sample",
                holdout,
                "--device",
                args.device,
                "--epochs",
                str(args.epochs),
                "--bag-size",
                str(args.bag_size),
                "--bags-per-sample",
                str(args.bags_per_sample),
                "--prediction-batch-size",
                str(args.prediction_batch_size),
                "--hidden-dim",
                str(args.hidden_dim),
                "--conv-channels",
                str(args.conv_channels),
                "--learning-rate",
                str(args.learning_rate),
                "--min-component-fraction",
                str(args.min_component_fraction),
                "--caller-min-component-fraction",
                str(args.caller_min_component_fraction),
                "--max-rows-per-sample",
                str(args.max_rows_per_sample),
                "--predictions",
                str(predictions_path),
                "--calls",
                str(calls_path),
                "--summary",
                str(summary_path),
                "--checkpoint",
                str(checkpoint_path),
            ]
            print(f"=== outer holdout {holdout} ===", flush=True)
            subprocess.run(command, check=True)

        metrics = read_metrics(summary_path)
        test_calls = [row for row in read_tsv(calls_path) if row["sample"] == holdout]
        if len(test_calls) != 1:
            raise RuntimeError(f"expected one test call for {holdout}, found {len(test_calls)}")
        call = test_calls[0]
        truth_short, truth_long = truth_pairs[holdout]
        candidate_short_error = float(call["candidate_short"]) - truth_short
        candidate_long_error = float(call["candidate_long"]) - truth_long
        resolved = call["resolved"] == "True"
        fold_rows.append(
            {
                "holdout_sample": holdout,
                "validation_sample": metrics.get("validation_sample", ""),
                "truth_short": truth_short,
                "truth_long": truth_long,
                "resolved": resolved,
                "pred_short": call["pred_short"],
                "pred_long": call["pred_long"],
                "candidate_short": call["candidate_short"],
                "candidate_long": call["candidate_long"],
                "candidate_short_error": f"{candidate_short_error:.6f}",
                "candidate_long_error": f"{candidate_long_error:.6f}",
                "candidate_allele_mae": f"{np.mean([abs(candidate_short_error), abs(candidate_long_error)]):.6f}",
                "resolved_allele_mae": metrics.get("test_allele_mae", "") if resolved else "",
                "mixture_confidence": call["mixture_confidence"],
                "reason": call["reason"],
                "best_epoch": metrics.get("best_epoch", ""),
            }
        )

    write_tsv(args.output_dir / "folds.tsv", fold_rows, FOLD_FIELDS)
    candidate_mae = float(np.mean([float(row["candidate_allele_mae"]) for row in fold_rows]))
    resolved_maes = [
        float(row["resolved_allele_mae"])
        for row in fold_rows
        if row["resolved_allele_mae"] != ""
    ]
    summary = [
        {"metric": "evaluation", "value": "nested_leave_one_sample_out"},
        {"metric": "development_read_cap", "value": args.max_rows_per_sample},
        {"metric": "folds", "value": len(fold_rows)},
        {"metric": "resolved_folds", "value": len(resolved_maes)},
        {"metric": "resolved_fraction", "value": f"{len(resolved_maes) / len(fold_rows):.6f}"},
        {"metric": "candidate_allele_mae", "value": f"{candidate_mae:.6f}"},
        {
            "metric": "resolved_allele_mae",
            "value": "" if not resolved_maes else f"{float(np.mean(resolved_maes)):.6f}",
        },
        {
            "metric": "note",
            "value": "Resolved MAE is conditional on non-abstention; candidate MAE includes all folds and is not a clinical call metric.",
        },
    ]
    write_tsv(args.output_dir / "summary.tsv", summary, ["metric", "value"])
    print(f"Wrote {args.output_dir / 'folds.tsv'}")
    print(f"Wrote {args.output_dir / 'summary.tsv'}")


if __name__ == "__main__":
    main()
