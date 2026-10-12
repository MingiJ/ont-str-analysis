#!/usr/bin/env python3
"""Select a bounded, truth-free set of full-flank external HTT alignments."""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

try:
    from alignment_signal_bounds import DEFAULT_FLANK_BP, Alignment, load_alignments, select_alignment
except ImportError:  # pragma: no cover
    from .alignment_signal_bounds import (
        DEFAULT_FLANK_BP,
        Alignment,
        load_alignments,
        select_alignment,
    )


def eligible_read_ids(
    alignments: dict[str, list[Alignment]],
    *,
    flank_bp: int,
    min_mapq: int,
    max_reads: int,
    selection_seed: str,
) -> list[str]:
    eligible = []
    for read_id, read_alignments in alignments.items():
        selected = select_alignment(read_alignments, flank_bp)
        if selected is None or len(read_alignments) != 1:
            continue
        alignment, _ = selected
        if alignment.mapq < min_mapq:
            continue
        rank = hashlib.sha256(f"{selection_seed}\0{read_id}".encode()).digest()
        eligible.append((rank, read_id))
    eligible.sort()
    if max_reads > 0:
        eligible = eligible[:max_reads]
    return sorted(read_id for _, read_id in eligible)


def filter_bam(input_bam: Path, output_bam: Path, read_ids: list[str]) -> None:
    if not read_ids:
        raise ValueError("no full-flank HTT reads passed the selection criteria")
    output_bam.parent.mkdir(parents=True, exist_ok=True)
    temporary_bam = output_bam.with_name(output_bam.name + ".tmp")
    temporary_index = Path(str(temporary_bam) + ".bai")
    output_index = Path(str(output_bam) + ".bai")
    with tempfile.NamedTemporaryFile(
        mode="w", prefix="external-htt-read-names.", suffix=".txt", dir=output_bam.parent, delete=False
    ) as handle:
        names_path = Path(handle.name)
        for read_id in read_ids:
            handle.write(read_id + "\n")
    try:
        subprocess.run(
            ["samtools", "view", "-N", str(names_path), "-b", "-o", str(temporary_bam), str(input_bam)],
            check=True,
        )
        subprocess.run(["samtools", "index", str(temporary_bam)], check=True)
        os.replace(temporary_bam, output_bam)
        os.replace(temporary_index, output_index)
    finally:
        names_path.unlink(missing_ok=True)
        temporary_bam.unlink(missing_ok=True)
        temporary_index.unlink(missing_ok=True)


def write_metadata(bam: Path, output: Path) -> None:
    result = subprocess.run(
        ["samtools", "view", str(bam)],
        check=True,
        capture_output=True,
        text=True,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["read_id", "fastq_comment"], delimiter="\t")
        writer.writeheader()
        for line in result.stdout.splitlines():
            fields = line.split("\t")
            comment = next(
                (field.removeprefix("CO:Z:") for field in fields[11:] if field.startswith("CO:Z:")),
                "",
            )
            writer.writerow({"read_id": fields[0], "fastq_comment": comment})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-bam", type=Path, required=True)
    parser.add_argument("--output-bam", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--flank-bp", type=int, default=DEFAULT_FLANK_BP)
    parser.add_argument("--min-mapq", type=int, default=20)
    parser.add_argument("--max-reads", type=int, default=128, help="0 keeps every eligible read")
    parser.add_argument("--selection-seed", default="external-htt-confirmation-v1")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    alignments = load_alignments(args.input_bam)
    read_ids = eligible_read_ids(
        alignments,
        flank_bp=args.flank_bp,
        min_mapq=args.min_mapq,
        max_reads=args.max_reads,
        selection_seed=args.selection_seed,
    )
    filter_bam(args.input_bam, args.output_bam, read_ids)
    write_metadata(args.output_bam, args.metadata)
    timestamped = 0
    with args.metadata.open(newline="") as handle:
        timestamped = sum(bool(row["fastq_comment"].strip()) for row in csv.DictReader(handle, delimiter="\t"))
    print(
        f"Selected {len(read_ids)} full-flank reads into {args.output_bam}; "
        f"FASTQ comments retained={timestamped}"
    )


if __name__ == "__main__":
    main()
