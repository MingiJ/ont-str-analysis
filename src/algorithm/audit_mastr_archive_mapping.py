#!/usr/bin/env python3
"""Audit raw UUID/sample assignments against public ENA read sequences."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path


FIELDS = [
    "sample",
    "selected_raw_uuids",
    "high_identity_archive_matches",
    "concordant_matches",
    "discordant_matches",
    "concordance",
    "status",
]


def load_assignments(path: Path) -> dict[str, str]:
    with path.open(newline="") as handle:
        return {
            row["read_id"]: row["sample"]
            for row in csv.DictReader(handle, delimiter="\t")
            if row.get("read_id") and row.get("sample")
        }


def best_paf_matches(
    path: Path,
    *,
    min_identity: float,
    min_query_coverage: float,
) -> dict[str, str]:
    best: dict[str, tuple[tuple[int, int, int], str]] = {}
    with path.open() as handle:
        for line in handle:
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 12:
                continue
            try:
                query_len = int(fields[1])
                query_start = int(fields[2])
                query_end = int(fields[3])
                matches = int(fields[9])
                block_len = int(fields[10])
                mapq = int(fields[11])
            except ValueError:
                continue
            identity = matches / max(block_len, 1)
            coverage = (query_end - query_start) / max(query_len, 1)
            if identity < min_identity or coverage < min_query_coverage:
                continue
            target_sample = fields[5].split("|", 1)[0]
            rank = (mapq, matches, block_len)
            if fields[0] not in best or rank > best[fields[0]][0]:
                best[fields[0]] = (rank, target_sample)
    return {read_id: sample for read_id, (_, sample) in best.items()}


def audit_rows(
    assignments: dict[str, str],
    matches: dict[str, str],
    *,
    min_matches_per_sample: int,
    min_concordance: float,
) -> tuple[list[dict[str, object]], bool]:
    selected: dict[str, set[str]] = defaultdict(set)
    for read_id, sample in assignments.items():
        selected[sample].add(read_id)

    rows: list[dict[str, object]] = []
    passed = True
    for sample in sorted(selected):
        matched = [read_id for read_id in selected[sample] if read_id in matches]
        concordant = sum(matches[read_id] == sample for read_id in matched)
        discordant = len(matched) - concordant
        concordance = concordant / len(matched) if matched else 0.0
        sample_pass = len(matched) >= min_matches_per_sample and concordance >= min_concordance
        passed = passed and sample_pass
        rows.append(
            {
                "sample": sample,
                "selected_raw_uuids": len(selected[sample]),
                "high_identity_archive_matches": len(matched),
                "concordant_matches": concordant,
                "discordant_matches": discordant,
                "concordance": f"{concordance:.6f}",
                "status": "pass" if sample_pass else "fail",
            }
        )
    return rows, passed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-map", type=Path, required=True)
    parser.add_argument("--paf", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-identity", type=float, default=0.85)
    parser.add_argument("--min-query-coverage", type=float, default=0.80)
    parser.add_argument("--min-matches-per-sample", type=int, default=3)
    parser.add_argument("--min-concordance", type=float, default=0.90)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    assignments = load_assignments(args.sample_map)
    matches = best_paf_matches(
        args.paf,
        min_identity=args.min_identity,
        min_query_coverage=args.min_query_coverage,
    )
    rows, passed = audit_rows(
        assignments,
        matches,
        min_matches_per_sample=args.min_matches_per_sample,
        min_concordance=args.min_concordance,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=FIELDS, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(" ".join(f"{field}={row[field]}" for field in FIELDS))
    if not passed:
        raise SystemExit("raw UUID/archive sample-identity audit failed")


if __name__ == "__main__":
    main()
