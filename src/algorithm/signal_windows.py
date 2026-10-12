#!/usr/bin/env python3
"""Extract normalized raw-signal windows from single- or multi-FAST5 files.

This script consumes the evidence table produced by ``evidence_table.py``.
It uses existing raw-signal boundaries when available, pads the interval, and
writes a fixed-width NumPy archive suitable for early model prototyping.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import h5py
import numpy as np


DEFAULT_MANIFEST = Path("ont-str-runner/work/analysis/evidence_table.tsv")
DEFAULT_OUTPUT = Path("ont-str-runner/work/analysis/signal_windows.npz")
DEFAULT_INDEX = Path("ont-str-runner/work/analysis/signal_windows.index.tsv")
FIELDNAMES = [
    "row_index",
    "sample",
    "read_id",
    "fast5_path",
    "raw_signal_len",
    "window_start",
    "window_end",
    "source_start",
    "source_end",
    "source_span_abs",
    "boundary_kind",
    "window_span",
    "stored_len",
    "truncated",
    "truth_long",
    "truth_short",
    "group_label",
    "mapq",
    "strand",
    "softclip",
    "signal_boundary_source",
    "alignment_flag",
    "secondary",
    "supplementary",
    "basecall_len",
    "locus_alignment_candidates",
    "raw_per_base_left",
    "raw_per_base_repeat",
    "raw_per_base_right",
    "repeat_to_flank_rate_ratio",
    "boundary_qc_pass",
    "boundary_qc_reason",
]


def to_int(value: str | None) -> int | None:
    if value in (None, "", "-"):
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def read_manifest(path: Path, samples: set[str] | None) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if samples is None:
        return rows
    return [row for row in rows if row.get("sample") in samples]


def read_fast5_signal(path: Path, read_id: str) -> np.ndarray:
    with h5py.File(path, "r") as handle:
        raw_reads = handle.get("Raw/Reads")
        if raw_reads is not None:
            read_groups = list(raw_reads.keys())
            if not read_groups:
                raise KeyError("Raw/Reads contains no read groups")
            if len(read_groups) == 1:
                signal_path = f"Raw/Reads/{read_groups[0]}/Signal"
            else:
                matching = [name for name in read_groups if read_id in name]
                if not matching:
                    raise KeyError(f"no Raw/Reads group matched {read_id}")
                signal_path = f"Raw/Reads/{matching[0]}/Signal"
        else:
            candidates = (f"read_{read_id}", read_id)
            root_group = next((name for name in candidates if name in handle), None)
            if root_group is None:
                raise KeyError(f"no multi-FAST5 root group matched {read_id}")
            signal_path = f"{root_group}/Raw/Signal"
            if signal_path not in handle:
                raise KeyError(f"raw Signal is missing for multi-FAST5 read {read_id}")

        return np.asarray(handle[signal_path], dtype=np.float32)


def normalize_signal(signal: np.ndarray) -> np.ndarray:
    median = float(np.median(signal))
    mad = float(np.median(np.abs(signal - median)))
    scale = 1.4826 * mad
    if scale < 1e-6:
        scale = float(np.std(signal))
    if scale < 1e-6:
        scale = 1.0
    return ((signal - median) / scale).astype(np.float32, copy=False)


def bounded_window(start: int, end: int, signal_len: int, padding: int) -> tuple[int, int]:
    left = max(0, min(start, end) - padding)
    right = min(signal_len, max(start, end) + padding)
    return left, right


def sanitize_key(sample: str, read_id: str) -> str:
    safe_sample = re.sub(r"[^A-Za-z0-9_.-]+", "_", sample)
    safe_read = re.sub(r"[^A-Za-z0-9_.-]+", "_", read_id)
    return f"{safe_sample}__{safe_read}"


def source_boundaries(row: dict[str, str], boundary_kind: str) -> tuple[int | None, int | None]:
    if boundary_kind == "window":
        return to_int(row.get("signal_window_start")), to_int(row.get("signal_window_end"))
    if boundary_kind == "repeat":
        return to_int(row.get("signal_repeat_start")), to_int(row.get("signal_repeat_end"))
    raise ValueError(f"unknown boundary kind: {boundary_kind}")


def extract_windows(
    rows: list[dict[str, str]],
    max_reads: int | None,
    padding: int,
    max_signal_len: int,
    require_bounds: bool,
    require_boundary_qc: bool = False,
    boundary_kind: str = "window",
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict[str, object]]]:
    signals: list[np.ndarray] = []
    masks: list[np.ndarray] = []
    keys: list[str] = []
    index_rows: list[dict[str, object]] = []

    for row in rows:
        if max_reads is not None and len(signals) >= max_reads:
            break

        read_id = row.get("read_id", "")
        sample = row.get("sample", "")
        fast5_text = row.get("fast5_path", "")
        start, end = source_boundaries(row, boundary_kind)
        if not read_id or not sample or not fast5_text:
            continue
        if require_bounds and (start is None or end is None):
            continue
        if require_boundary_qc and row.get("boundary_qc_pass") not in ("1", "True", "true"):
            continue

        fast5_path = Path(fast5_text)
        if not fast5_path.exists():
            continue

        try:
            raw_signal = read_fast5_signal(fast5_path, read_id)
        except (OSError, KeyError):
            continue

        raw_len = int(raw_signal.shape[0])
        if start is None or end is None:
            window_start, window_end = 0, raw_len
            source_span_abs = ""
        else:
            window_start, window_end = bounded_window(start, end, raw_len, padding)
            source_span_abs = abs(end - start)
        if window_end <= window_start:
            continue

        window = normalize_signal(raw_signal[window_start:window_end])
        window_span = int(window.shape[0])
        stored_len = min(int(window.shape[0]), max_signal_len)
        padded = np.zeros(max_signal_len, dtype=np.float32)
        mask = np.zeros(max_signal_len, dtype=np.bool_)
        padded[:stored_len] = window[:stored_len]
        mask[:stored_len] = True

        signals.append(padded)
        masks.append(mask)
        keys.append(sanitize_key(sample, read_id))
        index_rows.append(
            {
                "row_index": len(index_rows),
                "sample": sample,
                "read_id": read_id,
                "fast5_path": fast5_text,
                "raw_signal_len": raw_len,
                "window_start": window_start,
                "window_end": window_end,
                "source_start": start,
                "source_end": end,
                "source_span_abs": source_span_abs,
                "boundary_kind": boundary_kind,
                "window_span": window_span,
                "stored_len": stored_len,
                "truncated": int(window_span > max_signal_len),
                "truth_long": row.get("truth_long", ""),
                "truth_short": row.get("truth_short", ""),
                "group_label": row.get("group_label", ""),
                "mapq": row.get("mapq", ""),
                "strand": row.get("strand", ""),
                "softclip": row.get("softclip", ""),
                "signal_boundary_source": row.get("signal_boundary_source", ""),
                "alignment_flag": row.get("alignment_flag", ""),
                "secondary": row.get("secondary", ""),
                "supplementary": row.get("supplementary", ""),
                "basecall_len": row.get("basecall_len", ""),
                "locus_alignment_candidates": row.get("locus_alignment_candidates", ""),
                "raw_per_base_left": row.get("raw_per_base_left", ""),
                "raw_per_base_repeat": row.get("raw_per_base_repeat", ""),
                "raw_per_base_right": row.get("raw_per_base_right", ""),
                "repeat_to_flank_rate_ratio": row.get("repeat_to_flank_rate_ratio", ""),
                "boundary_qc_pass": row.get("boundary_qc_pass", ""),
                "boundary_qc_reason": row.get("boundary_qc_reason", ""),
            }
        )

    if not signals:
        return (
            np.empty((0, max_signal_len), dtype=np.float32),
            np.empty((0, max_signal_len), dtype=np.bool_),
            np.empty((0,), dtype="U1"),
            [],
        )
    return np.vstack(signals), np.vstack(masks), np.asarray(keys), index_rows


def write_index(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract normalized FAST5 signal windows.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--samples", nargs="+", help="Optional sample filter.")
    parser.add_argument("--max-reads", type=int, help="Stop after this many extracted reads.")
    parser.add_argument("--padding", type=int, default=1000, help="Raw-signal samples added to both sides.")
    parser.add_argument("--max-signal-len", type=int, default=20000, help="Fixed stored window length.")
    parser.add_argument(
        "--boundary-kind",
        choices=("window", "repeat"),
        default="window",
        help="Extract the full mapped flank window or the mapped repeat interval.",
    )
    parser.add_argument(
        "--allow-missing-bounds",
        action="store_true",
        help="Use full raw signal when signal_window_start/end are unavailable.",
    )
    parser.add_argument(
        "--require-boundary-qc",
        action="store_true",
        help="Keep only rows marked as passing independent boundary consistency checks.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    samples = set(args.samples) if args.samples else None
    rows = read_manifest(args.manifest, samples)
    signals, masks, keys, index_rows = extract_windows(
        rows=rows,
        max_reads=args.max_reads,
        padding=args.padding,
        max_signal_len=args.max_signal_len,
        require_bounds=not args.allow_missing_bounds,
        require_boundary_qc=args.require_boundary_qc,
        boundary_kind=args.boundary_kind,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output, signal=signals, mask=masks, key=keys)
    write_index(index_rows, args.index)
    print(f"Wrote {signals.shape[0]} windows to {args.output}")
    print(f"Wrote index to {args.index}")


if __name__ == "__main__":
    main()
