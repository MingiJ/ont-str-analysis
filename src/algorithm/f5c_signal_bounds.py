#!/usr/bin/env python3
"""Build truth-free HTT raw-signal boundaries from f5c eventalign output."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

try:
    from alignment_signal_bounds import (
        DEFAULT_FLANK_BP,
        FIELDNAMES,
        LOCUS_END_0,
        LOCUS_START_0,
        cigar_lengths,
        load_alignments,
        select_alignment,
        write_rows,
    )
except ImportError:  # pragma: no cover
    from .alignment_signal_bounds import (
        DEFAULT_FLANK_BP,
        FIELDNAMES,
        LOCUS_END_0,
        LOCUS_START_0,
        cigar_lengths,
        load_alignments,
        select_alignment,
        write_rows,
    )


def choose_field(fieldnames: list[str], candidates: tuple[str, ...]) -> str:
    for candidate in candidates:
        if candidate in fieldnames:
            return candidate
    raise ValueError(f"eventalign output lacks any of: {', '.join(candidates)}")


def load_event_intervals(path: Path) -> dict[str, list[tuple[int, int, int]]]:
    grouped: dict[str, list[tuple[int, int, int]]] = defaultdict(list)
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = list(reader.fieldnames or [])
        read_field = choose_field(fieldnames, ("read_name", "read_id", "read_index"))
        position_field = choose_field(fieldnames, ("position", "reference_position"))
        start_field = choose_field(fieldnames, ("start_idx", "start_index", "start_raw"))
        end_field = choose_field(fieldnames, ("end_idx", "end_index", "end_raw"))
        contig_field = choose_field(fieldnames, ("contig", "reference_name"))
        for row in reader:
            if row.get(contig_field) != "chr4":
                continue
            try:
                position = int(row[position_field])
                raw_start = int(row[start_field])
                raw_end = int(row[end_field])
            except (KeyError, TypeError, ValueError):
                continue
            read_id = row.get(read_field, "")
            if read_id:
                grouped[read_id].append((position, min(raw_start, raw_end), max(raw_start, raw_end)))
    return grouped


def segment_span(
    events: list[tuple[int, int, int]],
    start: int,
    end: int,
    *,
    min_events: int = 5,
) -> tuple[int, int, int] | None:
    selected = [(raw_start, raw_end) for position, raw_start, raw_end in events if start <= position < end]
    if len(selected) < min_events:
        return None
    return min(item[0] for item in selected), max(item[1] for item in selected), len(selected)


def boundary_qc(
    left_span: int,
    repeat_span: int,
    right_span: int,
    query_spans: tuple[int, int, int],
    alignment_candidates: int,
) -> tuple[bool, str, tuple[float, float, float, float]]:
    query = np.asarray(query_spans, dtype=np.float64)
    raw = np.asarray([left_span, repeat_span, right_span], dtype=np.float64)
    rates = raw / np.maximum(query, 1.0)
    left_rate, repeat_rate, right_rate = rates.tolist()
    flank_rate = max((left_rate + right_rate) / 2.0, 1e-8)
    repeat_ratio = repeat_rate / flank_rate
    reasons = []
    if alignment_candidates != 1:
        reasons.append("multiple_full_flank_alignments")
    if np.any(query <= 0.0) or np.any(raw <= 0.0):
        reasons.append("nonpositive_segment_span")
    if np.any(rates < 3.0) or np.any(rates > 40.0):
        reasons.append("implausible_raw_samples_per_base")
    if max(left_rate, right_rate) / max(min(left_rate, right_rate), 1e-8) > 2.0:
        reasons.append("discordant_flank_rates")
    if not 0.5 <= repeat_ratio <= 2.0:
        reasons.append("discordant_repeat_rate")
    return not reasons, ";".join(reasons) if reasons else "pass", (
        left_rate,
        repeat_rate,
        right_rate,
        repeat_ratio,
    )


def derive_rows(
    sample: str,
    fast5: Path,
    bam: Path,
    eventalign: Path,
    *,
    flank_bp: int,
    min_events: int,
) -> list[dict[str, object]]:
    event_intervals = load_event_intervals(eventalign)
    alignments = load_alignments(bam)
    rows = []
    for read_id in sorted(set(event_intervals).intersection(alignments)):
        selected_alignment = select_alignment(alignments[read_id], flank_bp)
        if selected_alignment is None:
            continue
        alignment, query_boundaries = selected_alignment
        events = event_intervals[read_id]
        left = segment_span(events, LOCUS_START_0 - flank_bp, LOCUS_START_0, min_events=min_events)
        repeat = segment_span(events, LOCUS_START_0, LOCUS_END_0, min_events=min_events)
        right = segment_span(events, LOCUS_END_0, LOCUS_END_0 + flank_bp, min_events=min_events)
        if left is None or repeat is None or right is None:
            continue
        left_span = left[1] - left[0]
        repeat_span = repeat[1] - repeat[0]
        right_span = right[1] - right[0]
        query_spans = tuple(
            right_boundary - left_boundary
            for left_boundary, right_boundary in zip(query_boundaries, query_boundaries[1:])
        )
        qc_pass, qc_reason, rates = boundary_qc(
            left_span,
            repeat_span,
            right_span,
            query_spans,
            len(alignments[read_id]),
        )
        reference_len, query_len, _, hard_total, soft_total = cigar_lengths(alignment.cigar)
        _ = reference_len
        rows.append(
            {
                "sample": sample,
                "read_id": read_id,
                "fast5_path": str(fast5),
                "truth_long": "",
                "truth_short": "",
                "group_label": "",
                "signal_window_start": min(left[0], repeat[0], right[0]),
                "signal_repeat_start": repeat[0],
                "signal_repeat_end": repeat[1],
                "signal_window_end": max(left[1], repeat[1], right[1]),
                "signal_len": "",
                "query_window_start": query_boundaries[0],
                "query_repeat_start": query_boundaries[1],
                "query_repeat_end": query_boundaries[2],
                "query_window_end": query_boundaries[3],
                "basecall_len": query_len + hard_total,
                "query_repeat_span": query_spans[1],
                "basecall_cag_longest": "",
                "basecall_cag_total": "",
                "locus_alignment_candidates": len(alignments[read_id]),
                "raw_per_base_left": f"{rates[0]:.6f}",
                "raw_per_base_repeat": f"{rates[1]:.6f}",
                "raw_per_base_right": f"{rates[2]:.6f}",
                "repeat_to_flank_rate_ratio": f"{rates[3]:.6f}",
                "boundary_qc_pass": int(qc_pass),
                "boundary_qc_reason": qc_reason,
                "mapq": alignment.mapq,
                "strand": "reverse" if alignment.reverse else "forward",
                "alignment_flag": alignment.flag,
                "secondary": int(alignment.secondary),
                "supplementary": int(alignment.supplementary),
                "softclip": soft_total,
                "hardclip": hard_total,
                "boundary_source": "bam_cigar_f5c_eventalign",
                "signal_boundary_source": "f5c_eventalign_r9.4.1",
                "warpstr_validation": "",
                "warpstr_delta_window_start": "",
                "warpstr_delta_repeat_start": "",
                "warpstr_delta_repeat_end": "",
                "warpstr_delta_window_end": "",
            }
        )
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", required=True)
    parser.add_argument("--fast5", type=Path, required=True)
    parser.add_argument("--bam", type=Path, required=True)
    parser.add_argument("--eventalign", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--flank-bp", type=int, default=DEFAULT_FLANK_BP)
    parser.add_argument("--min-events", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = derive_rows(
        args.sample,
        args.fast5,
        args.bam,
        args.eventalign,
        flank_bp=args.flank_bp,
        min_events=args.min_events,
    )
    write_rows(args.output, rows)
    qc_pass = sum(int(row["boundary_qc_pass"]) for row in rows)
    print(f"Wrote {len(rows)} truth-free f5c boundary rows to {args.output}; QC pass={qc_pass}")


if __name__ == "__main__":
    main()
