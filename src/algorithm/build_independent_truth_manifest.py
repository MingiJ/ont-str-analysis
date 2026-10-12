#!/usr/bin/env python3
"""Build signal-window boundaries for truth samples without WarpSTR selection.

For each primary labelled sample, this driver maps the HTT reference interval
through BAM CIGAR operations and native FAST5 event/move tables. The resulting
TSV can be consumed directly by ``signal_windows.py`` and intentionally leaves
the per-read ``group_label`` blank.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from argparse import Namespace
from pathlib import Path
from statistics import median

try:
    from alignment_signal_bounds import DEFAULT_FLANK_BP, FIELDNAMES, derive_rows, write_rows
except ImportError:  # pragma: no cover
    from .alignment_signal_bounds import DEFAULT_FLANK_BP, FIELDNAMES, derive_rows, write_rows


DEFAULT_TRUTH = Path("ont-str-runner/configs/truth_samples.tsv")
DEFAULT_OUTPUT = Path("ont-str-runner/work/analysis/independent_truth_signal_bounds_dev.tsv")
DEFAULT_SUMMARY = Path("ont-str-runner/work/analysis/independent_truth_signal_bounds_dev_summary.tsv")
SUMMARY_FIELDS = [
    "sample",
    "truth_long",
    "truth_short",
    "rows_derived",
    "indexed_reads",
    "aligned_reads",
    "indexed_aligned_reads",
    "missing_full_flanks",
    "below_min_mapq",
    "fast5_failures",
    "boundary_qc_pass",
    "boundary_qc_fail",
    "boundary_qc_failure_reasons",
    "warpstr_validation_rows",
    "median_abs_delta_window_start",
    "median_abs_delta_repeat_start",
    "median_abs_delta_repeat_end",
    "median_abs_delta_window_end",
]


def to_int(value: str | None) -> int | None:
    if value in (None, "", "-"):
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def load_truth_samples(path: Path, requested: set[str] | None) -> list[tuple[str, int, int]]:
    samples: list[tuple[str, int, int]] = []
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            sample = row.get("sample", "")
            truth_long = to_int(row.get("truth_long"))
            truth_short = to_int(row.get("truth_short"))
            include = to_int(row.get("include_primary")) == 1
            if not sample or not include or truth_long is None or truth_short is None:
                continue
            if requested is not None and sample not in requested:
                continue
            samples.append((sample, truth_long, truth_short))
    if requested is not None:
        missing = sorted(requested - {sample for sample, _, _ in samples})
        if missing:
            raise ValueError(f"requested samples absent from primary truth manifest: {', '.join(missing)}")
    if not samples:
        raise ValueError("no primary labelled samples selected")
    return samples


def median_abs(rows: list[dict[str, object]], field: str) -> str:
    values = [abs(int(row[field])) for row in rows if row.get(field) not in (None, "")]
    return "" if not values else f"{median(values):.1f}"


def write_summary(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--truth-manifest", type=Path, default=DEFAULT_TRUTH)
    parser.add_argument("--samples", nargs="+")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--flank-bp", type=int, default=DEFAULT_FLANK_BP)
    parser.add_argument("--min-mapq", type=int, default=20)
    parser.add_argument(
        "--max-rows-per-sample",
        type=int,
        default=128,
        help="Bound successful rows per sample for development; 0 means all.",
    )
    return parser.parse_args()


def main() -> None:
    cli = parse_args()
    repo_root = cli.repo_root.resolve()
    truth_path = cli.truth_manifest if cli.truth_manifest.is_absolute() else repo_root / cli.truth_manifest
    output = cli.output if cli.output.is_absolute() else repo_root / cli.output
    summary_path = cli.summary if cli.summary.is_absolute() else repo_root / cli.summary
    selected = load_truth_samples(truth_path, set(cli.samples) if cli.samples else None)

    all_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    for sample, truth_long, truth_short in selected:
        data_dir = repo_root / "ont-str-runner" / "data" / sample
        work_dir = repo_root / "ont-str-runner" / "work"
        args = Namespace(
            sample=sample,
            truth_long=truth_long,
            truth_short=truth_short,
            bam=data_dir / f"{sample}.bam",
            f5index=data_dir / "htt.f5index",
            data_root=data_dir,
            warpstr_overview=work_dir / "warpstr" / sample / "HTT_CAG" / "overview.csv",
            flank_bp=cli.flank_bp,
            min_mapq=cli.min_mapq,
            max_rows=cli.max_rows_per_sample,
        )
        rows, stats = derive_rows(args)
        all_rows.extend(rows)
        validation_rows = [row for row in rows if row["warpstr_validation"]]
        qc_pass = sum(int(row["boundary_qc_pass"]) for row in rows)
        failure_reasons = Counter(
            reason
            for row in rows
            if not int(row["boundary_qc_pass"])
            for reason in str(row["boundary_qc_reason"]).split(";")
            if reason
        )
        summary_rows.append(
            {
                "sample": sample,
                "truth_long": truth_long,
                "truth_short": truth_short,
                "rows_derived": len(rows),
                **stats,
                "boundary_qc_pass": qc_pass,
                "boundary_qc_fail": len(rows) - qc_pass,
                "boundary_qc_failure_reasons": ";".join(
                    f"{reason}:{count}" for reason, count in sorted(failure_reasons.items())
                ),
                "warpstr_validation_rows": len(validation_rows),
                "median_abs_delta_window_start": median_abs(validation_rows, "warpstr_delta_window_start"),
                "median_abs_delta_repeat_start": median_abs(validation_rows, "warpstr_delta_repeat_start"),
                "median_abs_delta_repeat_end": median_abs(validation_rows, "warpstr_delta_repeat_end"),
                "median_abs_delta_window_end": median_abs(validation_rows, "warpstr_delta_window_end"),
            }
        )
        print(
            f"sample={sample} rows={len(rows)} indexed_aligned={stats['indexed_aligned_reads']} "
            f"fast5_failures={stats['fast5_failures']}",
            flush=True,
        )

    write_rows(output, all_rows)
    write_summary(summary_path, summary_rows)
    print(f"Wrote {len(all_rows)} independent boundary rows to {output}")
    print(f"Wrote summary to {summary_path}")


if __name__ == "__main__":
    main()
