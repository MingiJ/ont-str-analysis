#!/usr/bin/env python3
"""Extract normalized fixed-width signal windows from POD5 reads.

The boundary manifest is truth-free and is normally produced by
``dorado_move_signal_bounds.py``.  POD5 is imported lazily so pure packing and
validation helpers remain testable without the optional reader dependency.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

try:
    from signal_windows import (
        bounded_window,
        normalize_signal,
        read_manifest,
        sanitize_key,
        source_boundaries,
    )
except ImportError:  # pragma: no cover
    from .signal_windows import (
        bounded_window,
        normalize_signal,
        read_manifest,
        sanitize_key,
        source_boundaries,
    )


DEFAULT_MANIFEST = Path("ont-str-runner/work/mastr/mastr_dorado_move_signal_bounds.tsv")
DEFAULT_OUTPUT = Path("ont-str-runner/work/mastr/mastr_signal_repeat_windows.npz")
DEFAULT_INDEX = Path("ont-str-runner/work/mastr/mastr_signal_repeat_windows.index.tsv")

INDEX_FIELDS = [
    "row_index",
    "sample",
    "read_id",
    "fast5_path",
    "raw_format",
    "sampling_rate",
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


def pack_window(
    raw_signal: np.ndarray,
    start: int,
    end: int,
    *,
    padding: int,
    max_signal_len: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    if max_signal_len <= 0:
        raise ValueError("max_signal_len must be positive")
    raw_signal = np.asarray(raw_signal, dtype=np.float32)
    raw_len = int(raw_signal.shape[0])
    window_start, window_end = bounded_window(start, end, raw_len, padding)
    if window_end <= window_start:
        raise ValueError(
            f"empty signal window after bounding: start={start}, end={end}, raw_len={raw_len}"
        )

    normalized = normalize_signal(raw_signal[window_start:window_end])
    window_span = int(normalized.shape[0])
    stored_len = min(window_span, max_signal_len)
    signal = np.zeros(max_signal_len, dtype=np.float32)
    mask = np.zeros(max_signal_len, dtype=np.bool_)
    signal[:stored_len] = normalized[:stored_len]
    mask[:stored_len] = True
    return signal, mask, {
        "raw_signal_len": raw_len,
        "window_start": window_start,
        "window_end": window_end,
        "window_span": window_span,
        "stored_len": stored_len,
        "truncated": int(window_span > max_signal_len),
    }


def load_selected_pod5_signals(
    rows: list[dict[str, str]],
) -> tuple[dict[tuple[str, str], np.ndarray], dict[tuple[str, str], int], set[tuple[str, str]]]:
    try:
        import pod5
    except ImportError as error:  # pragma: no cover - exercised in the runtime environment
        raise RuntimeError("POD5 extraction requires the 'pod5' Python package") from error

    by_path: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        path = row.get("fast5_path", "").strip()
        read_id = row.get("read_id", "").strip()
        if path and read_id:
            by_path[path].add(read_id)

    signals: dict[tuple[str, str], np.ndarray] = {}
    sample_rates: dict[tuple[str, str], int] = {}
    missing: set[tuple[str, str]] = set()
    for path_text, read_ids in sorted(by_path.items()):
        path = Path(path_text)
        if not path.exists():
            missing.update((path_text, read_id) for read_id in read_ids)
            continue
        found: set[str] = set()
        with pod5.Reader(path) as reader:
            for read in reader.reads(selection=sorted(read_ids)):
                read_id = str(read.read_id)
                key = (path_text, read_id)
                signals[key] = np.asarray(read.signal, dtype=np.float32)
                sample_rates[key] = int(read.run_info.sample_rate)
                found.add(read_id)
        missing.update((path_text, read_id) for read_id in read_ids - found)
    return signals, sample_rates, missing


def extract_windows(
    rows: list[dict[str, str]],
    *,
    padding: int,
    max_signal_len: int,
    boundary_kind: str,
    require_boundary_qc: bool,
    max_reads: int | None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict[str, object]], set[tuple[str, str]]]:
    usable_rows: list[dict[str, str]] = []
    for row in rows:
        start, end = source_boundaries(row, boundary_kind)
        if start is None or end is None:
            continue
        if require_boundary_qc and row.get("boundary_qc_pass") not in ("1", "True", "true"):
            continue
        usable_rows.append(row)
        if max_reads is not None and len(usable_rows) >= max_reads:
            break

    pod5_signals, sample_rates, missing = load_selected_pod5_signals(usable_rows)
    signals: list[np.ndarray] = []
    masks: list[np.ndarray] = []
    keys: list[str] = []
    index_rows: list[dict[str, object]] = []
    passthrough = [
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

    for row in usable_rows:
        sample = row.get("sample", "").strip()
        read_id = row.get("read_id", "").strip()
        path_text = row.get("fast5_path", "").strip()
        start, end = source_boundaries(row, boundary_kind)
        if not sample or not read_id or start is None or end is None:
            continue
        key = (path_text, read_id)
        if key not in pod5_signals:
            continue
        try:
            signal, mask, metrics = pack_window(
                pod5_signals[key],
                start,
                end,
                padding=padding,
                max_signal_len=max_signal_len,
            )
        except ValueError:
            continue

        signals.append(signal)
        masks.append(mask)
        keys.append(sanitize_key(sample, read_id))
        index_row: dict[str, object] = {
            "row_index": len(index_rows),
            "sample": sample,
            "read_id": read_id,
            "fast5_path": path_text,
            "raw_format": "POD5",
            "sampling_rate": sample_rates[key],
            "source_start": start,
            "source_end": end,
            "source_span_abs": abs(end - start),
            "boundary_kind": boundary_kind,
            **metrics,
        }
        index_row.update({field: row.get(field, "") for field in passthrough})
        index_rows.append(index_row)

    if not signals:
        return (
            np.empty((0, max_signal_len), dtype=np.float32),
            np.empty((0, max_signal_len), dtype=np.bool_),
            np.empty((0,), dtype="U1"),
            [],
            missing,
        )
    return np.vstack(signals), np.vstack(masks), np.asarray(keys), index_rows, missing


def write_index(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=INDEX_FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--samples", nargs="+", help="Optional sample filter.")
    parser.add_argument("--max-reads", type=int)
    parser.add_argument("--padding", type=int, default=1000)
    parser.add_argument("--max-signal-len", type=int, default=20000)
    parser.add_argument("--boundary-kind", choices=("window", "repeat"), default="repeat")
    parser.add_argument("--allow-failed-boundary-qc", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    samples = set(args.samples) if args.samples else None
    rows = read_manifest(args.manifest, samples)
    signals, masks, keys, index_rows, missing = extract_windows(
        rows,
        padding=args.padding,
        max_signal_len=args.max_signal_len,
        boundary_kind=args.boundary_kind,
        require_boundary_qc=not args.allow_failed_boundary_qc,
        max_reads=args.max_reads,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output, signal=signals, mask=masks, key=keys)
    write_index(index_rows, args.index)
    print(f"manifest_rows={len(rows)} extracted_windows={signals.shape[0]} missing_pod5_reads={len(missing)}")
    print(f"Wrote POD5 signal windows to {args.output}")
    print(f"Wrote POD5 signal index to {args.index}")


if __name__ == "__main__":
    main()
