#!/usr/bin/env python3
"""Verify and copy target read groups from downloaded multi-FAST5 batches."""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

import h5py


MAPPING_FIELDS = ["read_id", "status", "source_fast5", "root_group"]


def canonical_read_id(value: str) -> str:
    return value[5:] if value.startswith("read_") else value


def load_targets(path: Path) -> set[str]:
    with path.open(newline="") as handle:
        targets = {
            row.get("read_id", "").strip()
            for row in csv.DictReader(handle, delimiter="\t")
            if row.get("read_id", "").strip()
        }
    if not targets:
        raise ValueError(f"no read IDs found in {path}")
    return targets


def locate_targets(batch_dir: Path, targets: set[str]) -> dict[str, tuple[Path, str]]:
    found = {}
    for path in sorted(batch_dir.glob("*.fast5")):
        with h5py.File(path, "r") as handle:
            for root_group in handle.keys():
                read_id = canonical_read_id(root_group)
                if read_id in targets:
                    found[read_id] = (path, root_group)
        if len(found) == len(targets):
            break
    return found


def copy_groups(
    output: Path,
    found: dict[str, tuple[Path, str]],
    *,
    overwrite: bool,
) -> None:
    if output.exists() and not overwrite:
        raise FileExistsError(f"output already exists: {output}; use --overwrite")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    if temporary.exists():
        temporary.unlink()
    try:
        with h5py.File(temporary, "w") as destination:
            copied_root_attributes = False
            for read_id in sorted(found):
                source_path, root_group = found[read_id]
                with h5py.File(source_path, "r") as source:
                    if not copied_root_attributes:
                        for name, value in source.attrs.items():
                            destination.attrs[name] = value
                        copied_root_attributes = True
                    source.copy(root_group, destination)
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_mapping(
    path: Path,
    targets: set[str],
    found: dict[str, tuple[Path, str]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MAPPING_FIELDS, delimiter="\t")
        writer.writeheader()
        for read_id in sorted(targets):
            match = found.get(read_id)
            if match is None:
                writer.writerow({"read_id": read_id, "status": "not_found"})
            else:
                source, root_group = match
                writer.writerow(
                    {
                        "read_id": read_id,
                        "status": "found",
                        "source_fast5": source,
                        "root_group": root_group,
                    }
                )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-dir", type=Path, required=True)
    parser.add_argument("--htt-read-metadata", type=Path, required=True)
    parser.add_argument("--output-fast5", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    targets = load_targets(args.htt_read_metadata)
    found = locate_targets(args.batch_dir, targets)
    write_mapping(args.mapping, targets, found)
    copy_groups(args.output_fast5, found, overwrite=args.overwrite)
    print(f"Copied {len(found)}/{len(targets)} target reads to {args.output_fast5}")
    if len(found) != len(targets):
        missing = sorted(targets - set(found))
        raise SystemExit("Missing target reads: " + ", ".join(missing))


if __name__ == "__main__":
    main()
