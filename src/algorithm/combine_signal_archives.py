#!/usr/bin/env python3
"""Combine compatible signal-window NPZ archives and their TSV indexes."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np


def read_index(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return list(reader), list(reader.fieldnames or [])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        action="append",
        nargs=2,
        metavar=("ARCHIVE", "INDEX"),
        required=True,
        help="Input NPZ archive and matching index TSV. Repeat for each pair.",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    signal_parts = []
    mask_parts = []
    key_parts = []
    all_rows: list[dict[str, str]] = []
    fields: list[str] = []
    width: int | None = None

    for archive_text, index_text in args.input:
        archive_path = Path(archive_text)
        index_path = Path(index_text)
        with np.load(archive_path, allow_pickle=False) as archive:
            signal = np.asarray(archive["signal"], dtype=np.float32)
            mask = np.asarray(archive["mask"], dtype=np.bool_)
            key = np.asarray(archive["key"])
        rows, current_fields = read_index(index_path)
        if signal.ndim != 2 or mask.shape != signal.shape or key.shape[0] != signal.shape[0]:
            raise SystemExit(f"incompatible array shapes in {archive_path}")
        if len(rows) != signal.shape[0]:
            raise SystemExit(
                f"row mismatch for {archive_path}: archive={signal.shape[0]} index={len(rows)}"
            )
        if width is None:
            width = signal.shape[1]
        elif signal.shape[1] != width:
            raise SystemExit(
                f"signal width mismatch for {archive_path}: expected={width} actual={signal.shape[1]}"
            )
        for field in current_fields:
            if field not in fields:
                fields.append(field)
        signal_parts.append(signal)
        mask_parts.append(mask)
        key_parts.append(key.astype(str))
        all_rows.extend(rows)

    if "row_index" not in fields:
        fields.insert(0, "row_index")
    for row_index, row in enumerate(all_rows):
        row["row_index"] = str(row_index)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output,
        signal=np.concatenate(signal_parts),
        mask=np.concatenate(mask_parts),
        key=np.concatenate(key_parts),
    )
    args.index.parent.mkdir(parents=True, exist_ok=True)
    with args.index.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"Wrote {len(all_rows)} windows to {args.output}")
    print(f"Wrote index to {args.index}")


if __name__ == "__main__":
    main()
