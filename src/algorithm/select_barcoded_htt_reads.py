#!/usr/bin/env python3
"""Select a bounded truth-free set of barcoded HTT reads from a Dorado BAM."""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
from collections import defaultdict
from pathlib import Path

try:
    from alignment_signal_bounds import (
        DEFAULT_FLANK_BP,
        LOCUS_END_0,
        LOCUS_START_0,
        Alignment,
        canonical_read_id,
    )
    from select_external_htt_reads import eligible_read_ids
except ImportError:  # pragma: no cover
    from .alignment_signal_bounds import (
        DEFAULT_FLANK_BP,
        LOCUS_END_0,
        LOCUS_START_0,
        Alignment,
        canonical_read_id,
    )
    from .select_external_htt_reads import eligible_read_ids


BARCODE_RE = re.compile(r"(barcode\d+)$", re.IGNORECASE)


def normalize_barcode(value: str) -> str | None:
    match = BARCODE_RE.search(value.strip())
    if match is None:
        return None
    number = int(match.group(1).lower().removeprefix("barcode"))
    return f"barcode{number:02d}"


def sam_barcode(fields: list[str]) -> str | None:
    for field in fields[11:]:
        if field.startswith("BC:Z:"):
            return normalize_barcode(field.removeprefix("BC:Z:"))
    return None


def load_sample_barcodes(path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row.get("status") != "eligible_primary":
                continue
            sample = row.get("sample", "").strip()
            barcode = normalize_barcode(row.get("barcode", ""))
            if not sample or barcode is None:
                continue
            if barcode in mapping:
                raise ValueError(f"duplicate eligible barcode in acquisition manifest: {barcode}")
            mapping[barcode] = sample
    if not mapping:
        raise ValueError(f"no eligible sample/barcode rows in {path}")
    return mapping


def load_barcoded_alignments(
    bam: Path,
) -> tuple[dict[str, dict[str, list[Alignment]]], dict[str, int]]:
    command = ["samtools", "view", str(bam), f"chr4:{LOCUS_START_0 + 1}-{LOCUS_END_0}"]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    grouped: dict[str, dict[str, list[Alignment]]] = defaultdict(lambda: defaultdict(list))
    counts = {"locus_records": 0, "unclassified_locus_records": 0}
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        if len(fields) < 11:
            continue
        flag = int(fields[1])
        if flag & 4 or fields[5] == "*":
            continue
        counts["locus_records"] += 1
        barcode = sam_barcode(fields)
        if barcode is None:
            counts["unclassified_locus_records"] += 1
            continue
        read_id = canonical_read_id(fields[0])
        grouped[barcode][read_id].append(
            Alignment(
                read_id=read_id,
                flag=flag,
                reference_start=int(fields[3]) - 1,
                mapq=int(fields[4]),
                cigar=fields[5],
            )
        )
    return {barcode: dict(reads) for barcode, reads in grouped.items()}, counts


def select_rows(
    bam: Path,
    acquisition_manifest: Path,
    *,
    flank_bp: int,
    min_mapq: int,
    max_reads_per_sample: int,
    min_reads_per_sample: int,
    selection_seed: str,
) -> tuple[list[dict[str, str]], dict[str, int]]:
    sample_barcodes = load_sample_barcodes(acquisition_manifest)
    by_barcode, counts = load_barcoded_alignments(bam)
    rows: list[dict[str, str]] = []
    for barcode, sample in sample_barcodes.items():
        selected = eligible_read_ids(
            by_barcode.get(barcode, {}),
            flank_bp=flank_bp,
            min_mapq=min_mapq,
            max_reads=max_reads_per_sample,
            selection_seed=f"{selection_seed}:{sample}:{barcode}",
        )
        counts[f"{sample}_selected"] = len(selected)
        if len(selected) < min_reads_per_sample:
            raise ValueError(
                f"{sample} ({barcode}) has {len(selected)} eligible raw UUIDs; "
                f"frozen minimum is {min_reads_per_sample}"
            )
        rows.extend({"sample": sample, "read_id": read_id, "barcode": barcode} for read_id in selected)
    return rows, counts


def write_outputs(rows: list[dict[str, str]], sample_map: Path, read_ids: Path) -> None:
    sample_map.parent.mkdir(parents=True, exist_ok=True)
    with sample_map.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["sample", "read_id", "barcode"], delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    unique_ids = sorted({row["read_id"] for row in rows})
    if len(unique_ids) != len(rows):
        raise ValueError("one or more raw UUIDs were assigned to multiple eligible samples")
    read_ids.write_text("".join(f"{read_id}\n" for read_id in unique_ids))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bam", type=Path, required=True)
    parser.add_argument("--acquisition-manifest", type=Path, required=True)
    parser.add_argument("--sample-map", type=Path, required=True)
    parser.add_argument("--read-ids", type=Path, required=True)
    parser.add_argument("--flank-bp", type=int, default=DEFAULT_FLANK_BP)
    parser.add_argument("--min-mapq", type=int, default=20)
    parser.add_argument("--max-reads-per-sample", type=int, default=128)
    parser.add_argument("--min-reads-per-sample", type=int, default=6)
    parser.add_argument("--selection-seed", default="mastr-raw-selection-v1")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows, counts = select_rows(
        args.bam,
        args.acquisition_manifest,
        flank_bp=args.flank_bp,
        min_mapq=args.min_mapq,
        max_reads_per_sample=args.max_reads_per_sample,
        min_reads_per_sample=args.min_reads_per_sample,
        selection_seed=args.selection_seed,
    )
    write_outputs(rows, args.sample_map, args.read_ids)
    print(" ".join(f"{name}={value}" for name, value in counts.items()))
    print(f"selected_raw_uuids={len(rows)}")


if __name__ == "__main__":
    main()
