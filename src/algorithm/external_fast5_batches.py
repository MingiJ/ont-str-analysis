#!/usr/bin/env python3
"""Map external HTT read timestamps to candidate chronological FAST5 batches.

The deposited multi-FAST5 files are numbered chronological groups of 4,000
reads. Pass and fail FASTQ headers provide a lightweight timestamp census of
the complete run. For each HTT read, this utility counts preceding timestamps,
estimates the central batch, and emits a small neighboring range for robust
selective retrieval. Exact read IDs must still be verified inside downloaded
candidate files.
"""

from __future__ import annotations

import argparse
from bisect import bisect_right
import csv
import gzip
import re
from pathlib import Path


START_TIME_RE = re.compile(r"(?:^|\s)start_time=([^\s]+)")
BATCH_RE = re.compile(r"_(\d+)\.fast5$")
OUTPUT_FIELDS = [
    "read_id",
    "start_time",
    "estimated_rank",
    "central_batch",
    "candidate_batch",
    "batch_distance",
    "member_name",
    "member_data_offset",
    "member_size",
]


def parse_header(value: str) -> tuple[str, str]:
    fields = value.strip().lstrip("@").split(maxsplit=1)
    if len(fields) != 2:
        raise ValueError(f"FASTQ header lacks a comment: {value[:80]!r}")
    match = START_TIME_RE.search(fields[1])
    if not match:
        raise ValueError(f"FASTQ header lacks start_time: {value[:80]!r}")
    return fields[0], match.group(1)


def load_targets(path: Path, header_paths: list[Path] | None = None) -> dict[str, str]:
    read_ids = set()
    targets = {}
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            read_id = row.get("read_id", "").strip()
            comment = row.get("fastq_comment", "").strip()
            if read_id:
                read_ids.add(read_id)
            match = START_TIME_RE.search(comment)
            if read_id and match:
                targets[read_id] = match.group(1)
    if not read_ids:
        raise ValueError(f"no HTT read IDs found in {path}")

    missing = read_ids - set(targets)
    for header_path in header_paths or []:
        if not missing:
            break
        opener = gzip.open if header_path.suffix == ".gz" else open
        with opener(header_path, "rt") as handle:
            for line in handle:
                read_id, start_time = parse_header(line)
                if read_id in missing:
                    targets[read_id] = start_time
                    missing.remove(read_id)
                    if not missing:
                        break
    if missing:
        raise ValueError(
            f"no acquisition timestamp found for {len(missing)} HTT reads in {path}: "
            + ", ".join(sorted(missing)[:5])
        )
    return targets


def estimate_ranks(targets: dict[str, str], header_paths: list[Path]) -> dict[str, int]:
    ordered_targets = sorted((start_time, read_id) for read_id, start_time in targets.items())
    increments = [0] * len(ordered_targets)
    for path in header_paths:
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt") as handle:
            for line in handle:
                read_id, start_time = parse_header(line)
                key = (start_time, read_id)
                first_later_target = bisect_right(ordered_targets, key)
                if first_later_target < len(increments):
                    increments[first_later_target] += 1

    ranks = {}
    preceding = 0
    for index, (_, read_id) in enumerate(ordered_targets):
        preceding += increments[index]
        ranks[read_id] = preceding
    return ranks


def load_fast5_members(path: Path) -> dict[int, dict[str, str]]:
    members = {}
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            name = row.get("name", "").rstrip("\r")
            match = BATCH_RE.search(name)
            if match:
                members[int(match.group(1))] = row | {"name": name}
    if not members:
        raise ValueError(f"no numbered FAST5 batches found in {path}")
    return members


def candidate_rows(
    targets: dict[str, str],
    ranks: dict[str, int],
    members: dict[int, dict[str, str]],
    *,
    batch_size: int = 4000,
    radius: int = 2,
) -> list[dict[str, object]]:
    rows = []
    for read_id in sorted(targets):
        rank = ranks[read_id]
        central = rank // batch_size
        for candidate in range(max(0, central - radius), central + radius + 1):
            member = members.get(candidate)
            if member is None:
                continue
            rows.append(
                {
                    "read_id": read_id,
                    "start_time": targets[read_id],
                    "estimated_rank": rank,
                    "central_batch": central,
                    "candidate_batch": candidate,
                    "batch_distance": candidate - central,
                    "member_name": member["name"],
                    "member_data_offset": member["data_offset"],
                    "member_size": member["size"],
                }
            )
    return rows


def write_tsv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=OUTPUT_FIELDS, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--htt-read-metadata", type=Path, required=True)
    parser.add_argument("--headers", type=Path, action="append", required=True)
    parser.add_argument("--fast5-member-index", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=4000)
    parser.add_argument("--radius", type=int, default=2)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    targets = load_targets(args.htt_read_metadata, args.headers)
    ranks = estimate_ranks(targets, args.headers)
    members = load_fast5_members(args.fast5_member_index)
    rows = candidate_rows(
        targets,
        ranks,
        members,
        batch_size=args.batch_size,
        radius=args.radius,
    )
    write_tsv(args.output, rows)
    unique_batches = len({row["candidate_batch"] for row in rows})
    print(
        f"Wrote {len(rows)} read/batch candidates for {len(targets)} HTT reads "
        f"across {unique_batches} unique FAST5 batches to {args.output}"
    )


if __name__ == "__main__":
    main()
