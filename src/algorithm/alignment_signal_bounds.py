#!/usr/bin/env python3
"""Derive raw-signal HTT windows from BAM alignments and native FAST5 events.

WarpSTR exposes signal boundaries only for reads whose flank extraction succeeds.
This utility provides an independent expansion path for older single-read FAST5
data: reference coordinates are mapped through the BAM CIGAR to basecalled read
coordinates, then through the FAST5 event/move table to raw-signal coordinates.
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from statistics import median

import h5py
import numpy as np


DEFAULT_BAM = Path("ont-str-runner/data/REL3/bam/chr4.sorted.htt_cag.bam")
DEFAULT_F5INDEX = Path("ont-str-runner/data/REL3/htt.f5index")
DEFAULT_DATA_ROOT = Path("ont-str-runner/data/REL3")
DEFAULT_OUTPUT = Path("ont-str-runner/work/rel3/rel3_alignment_signal_bounds.tsv")
DEFAULT_WARPSTR_OVERVIEW = Path(
    "ont-str-runner/work/warpstr/REL3_WARPSTR_OK/HTT_CAG/overview.csv"
)

# User-facing locus is 1-based inclusive: chr4:3074876-3074933.
LOCUS_START_0 = 3_074_875
LOCUS_END_0 = 3_074_933
DEFAULT_FLANK_BP = 112
CIGAR_RE = re.compile(r"(\d+)([MIDNSHP=X])")
READ_SUFFIX = "_Basecall_Alignment_template"

FIELDNAMES = [
    "sample",
    "read_id",
    "fast5_path",
    "truth_long",
    "truth_short",
    "group_label",
    "signal_window_start",
    "signal_repeat_start",
    "signal_repeat_end",
    "signal_window_end",
    "signal_len",
    "query_window_start",
    "query_repeat_start",
    "query_repeat_end",
    "query_window_end",
    "basecall_len",
    "query_repeat_span",
    "basecall_cag_longest",
    "basecall_cag_total",
    "locus_alignment_candidates",
    "raw_per_base_left",
    "raw_per_base_repeat",
    "raw_per_base_right",
    "repeat_to_flank_rate_ratio",
    "boundary_qc_pass",
    "boundary_qc_reason",
    "mapq",
    "strand",
    "alignment_flag",
    "secondary",
    "supplementary",
    "softclip",
    "hardclip",
    "boundary_source",
    "signal_boundary_source",
    "warpstr_validation",
    "warpstr_delta_window_start",
    "warpstr_delta_repeat_start",
    "warpstr_delta_repeat_end",
    "warpstr_delta_window_end",
]


@dataclass(frozen=True)
class Alignment:
    read_id: str
    flag: int
    reference_start: int
    mapq: int
    cigar: str

    @property
    def reverse(self) -> bool:
        return bool(self.flag & 16)

    @property
    def secondary(self) -> bool:
        return bool(self.flag & 256)

    @property
    def supplementary(self) -> bool:
        return bool(self.flag & 2048)


def canonical_read_id(value: str) -> str:
    return value.removesuffix(READ_SUFFIX)


def parse_cigar(cigar: str) -> list[tuple[int, str]]:
    parsed = [(int(length), operation) for length, operation in CIGAR_RE.findall(cigar)]
    if not parsed or "".join(f"{length}{operation}" for length, operation in parsed) != cigar:
        raise ValueError(f"invalid CIGAR: {cigar}")
    return parsed


def cigar_lengths(cigar: str) -> tuple[int, int, int, int, int]:
    parsed = parse_cigar(cigar)
    reference = sum(length for length, op in parsed if op in "MDN=X")
    query = sum(length for length, op in parsed if op in "MIS=X")
    hard_left = parsed[0][0] if parsed[0][1] == "H" else 0
    hard_total = sum(length for length, op in parsed if op == "H")
    soft_total = sum(length for length, op in parsed if op == "S")
    return reference, query, hard_left, hard_total, soft_total


def reference_boundary_to_query(
    reference_position: int, cigar: str, reference_start: int
) -> int | None:
    """Map a zero-based reference boundary to a SAM-oriented query boundary."""

    reference_cursor = reference_start
    query_cursor = 0
    for length, operation in parse_cigar(cigar):
        consumes_reference = operation in "MDN=X"
        consumes_query = operation in "MIS=X"
        if consumes_reference:
            reference_end = reference_cursor + length
            if reference_position <= reference_end:
                if reference_position < reference_cursor:
                    return None
                if operation in "M=X":
                    return query_cursor + min(length, reference_position - reference_cursor)
                return query_cursor
            reference_cursor = reference_end
        if consumes_query:
            query_cursor += length
    return query_cursor if reference_position == reference_cursor else None


def alignment_query_boundaries(alignment: Alignment, flank_bp: int) -> tuple[int, int, int, int] | None:
    targets = (
        LOCUS_START_0 - flank_bp,
        LOCUS_START_0,
        LOCUS_END_0,
        LOCUS_END_0 + flank_bp,
    )
    boundaries = [
        reference_boundary_to_query(target, alignment.cigar, alignment.reference_start)
        for target in targets
    ]
    if any(value is None for value in boundaries):
        return None

    _, query_len, hard_left, hard_total, _ = cigar_lengths(alignment.cigar)
    full_query_len = query_len + hard_total
    oriented = [hard_left + int(value) for value in boundaries if value is not None]
    if alignment.reverse:
        native = [full_query_len - value for value in reversed(oriented)]
    else:
        native = oriented
    if any(left > right for left, right in zip(native, native[1:])):
        return None
    return tuple(native)  # type: ignore[return-value]


def load_f5index(path: Path, data_root: Path) -> dict[str, Path]:
    mapping: dict[str, Path] = {}
    with path.open() as handle:
        for line in handle:
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 2:
                continue
            read_id = canonical_read_id(fields[0])
            candidate = data_root / fields[1]
            if read_id not in mapping or not fields[0].endswith(READ_SUFFIX):
                mapping[read_id] = candidate
    return mapping


def load_alignments(bam: Path) -> dict[str, list[Alignment]]:
    command = ["samtools", "view", str(bam), f"chr4:{LOCUS_START_0 + 1}-{LOCUS_END_0}"]
    result = subprocess.run(command, check=True, text=True, capture_output=True)
    grouped: dict[str, list[Alignment]] = {}
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        if len(fields) < 6:
            continue
        flag = int(fields[1])
        if flag & 4 or fields[5] == "*":
            continue
        read_id = canonical_read_id(fields[0])
        grouped.setdefault(read_id, []).append(
            Alignment(
                read_id=read_id,
                flag=flag,
                reference_start=int(fields[3]) - 1,
                mapq=int(fields[4]),
                cigar=fields[5],
            )
        )
    return grouped


def select_alignment(alignments: list[Alignment], flank_bp: int) -> tuple[Alignment, tuple[int, int, int, int]] | None:
    candidates = []
    for alignment in alignments:
        boundaries = alignment_query_boundaries(alignment, flank_bp)
        if boundaries is None:
            continue
        rank = (
            alignment.secondary or alignment.supplementary,
            -alignment.mapq,
            alignment.supplementary,
            alignment.secondary,
        )
        candidates.append((rank, alignment, boundaries))
    if not candidates:
        return None
    _, alignment, boundaries = min(candidates, key=lambda item: item[0])
    return alignment, boundaries


def find_basecall_events(handle: h5py.File) -> h5py.Dataset:
    analyses = handle.get("Analyses")
    if analyses is None:
        raise KeyError("Analyses group is missing")
    for analysis_name in sorted(analyses.keys(), reverse=True):
        path = f"Analyses/{analysis_name}/BaseCalled_template/Events"
        if analysis_name.startswith("Basecall_1D_") and path in handle:
            events = handle[path]
            if "move" in events.dtype.names and "start" in events.dtype.names:
                return events
    raise KeyError("no Basecall_1D event/move table found")


def basecall_sequence(handle: h5py.File, events: h5py.Dataset) -> str:
    fastq_path = f"{events.parent.name}/Fastq"
    if fastq_path not in handle:
        raise KeyError(f"basecall FASTQ is missing beside {events.name}")
    value = handle[fastq_path][()]
    text = value.decode() if isinstance(value, bytes) else str(value)
    lines = text.splitlines()
    if len(lines) < 2:
        raise ValueError("basecall FASTQ is malformed")
    return lines[1].upper()


def read_group(handle: h5py.File) -> h5py.Group:
    reads = handle.get("Raw/Reads")
    if reads is None or not reads.keys():
        raise KeyError("Raw/Reads group is missing or empty")
    return reads[next(iter(reads.keys()))]


def event_end_bases(moves: np.ndarray, sequence_length: int) -> np.ndarray:
    """Map events to basecall ends across Albacore k-mer offset variants."""
    moves = np.asarray(moves, dtype=np.int64)
    initial_bases = int(sequence_length - int(np.sum(moves)))
    if not 0 <= initial_bases <= 20:
        raise ValueError(
            f"implausible FASTQ/event initial offset: sequence={sequence_length} "
            f"move_sum={int(np.sum(moves))} offset={initial_bases}"
        )
    end_bases = initial_bases + np.cumsum(moves)
    if end_bases.size == 0 or int(end_bases[-1]) != sequence_length:
        raise ValueError("FASTQ/event basecall length mismatch after offset inference")
    return end_bases


def event_start_to_raw(
    event_start: int | float,
    *,
    integer_start: bool,
    sampling_rate: float,
    raw_start: int,
    raw_len: int,
) -> int:
    """Convert legacy sample-index or seconds-based event starts to read offsets."""
    if integer_start:
        position = int(event_start)
        if raw_start <= position <= raw_start + raw_len:
            position -= raw_start
    else:
        position = int(round(float(event_start) * sampling_rate)) - raw_start
    return max(0, min(raw_len, position))


def boundary_quality(
    query_boundaries: tuple[int, int, int, int],
    raw_boundaries: tuple[int, int, int, int],
    alignment_candidates: int,
) -> tuple[bool, str, tuple[float, float, float, float]]:
    """Apply tool-independent consistency checks to mapped raw boundaries."""
    query_spans = np.diff(np.asarray(query_boundaries, dtype=np.float64))
    raw_spans = np.diff(np.asarray(raw_boundaries, dtype=np.float64))
    safe_query = np.maximum(query_spans, 1.0)
    rates = raw_spans / safe_query
    left_rate, repeat_rate, right_rate = rates.tolist()
    flank_rate = max((left_rate + right_rate) / 2.0, 1e-8)
    repeat_ratio = repeat_rate / flank_rate

    reasons: list[str] = []
    if alignment_candidates != 1:
        reasons.append("multiple_full_flank_alignments")
    if np.any(query_spans <= 0.0) or np.any(raw_spans <= 0.0):
        reasons.append("nonpositive_segment_span")
    if np.any(rates < 3.0) or np.any(rates > 40.0):
        reasons.append("implausible_raw_samples_per_base")
    flank_min = max(min(left_rate, right_rate), 1e-8)
    if max(left_rate, right_rate) / flank_min > 2.0:
        reasons.append("discordant_flank_rates")
    if not 0.5 <= repeat_ratio <= 2.0:
        reasons.append("discordant_repeat_rate")
    return not reasons, ";".join(reasons) if reasons else "pass", (
        left_rate,
        repeat_rate,
        right_rate,
        repeat_ratio,
    )


def query_boundaries_to_raw(
    path: Path, query_boundaries: tuple[int, int, int, int]
) -> tuple[tuple[int, int, int, int], int, int, str]:
    with h5py.File(path, "r") as handle:
        events = find_basecall_events(handle)
        sequence = basecall_sequence(handle, events)
        moves = np.asarray(events["move"], dtype=np.int64)
        end_bases = event_end_bases(moves, len(sequence))
        basecall_len = int(end_bases[-1])
        if query_boundaries[0] < 0 or query_boundaries[-1] > basecall_len:
            raise ValueError(
                f"query boundaries {query_boundaries} exceed basecall length {basecall_len}"
            )

        channel = handle["UniqueGlobalKey/channel_id"]
        sampling_rate = float(channel.attrs["sampling_rate"])
        raw = read_group(handle)
        raw_start = int(raw.attrs["start_time"])
        raw_len = int(raw["Signal"].shape[0])
        integer_start = np.issubdtype(events.dtype["start"], np.integer)

        raw_boundaries = []
        for boundary in query_boundaries:
            event_index = int(np.searchsorted(end_bases, boundary, side="left"))
            event_index = min(event_index, len(events) - 1)
            raw_boundaries.append(
                event_start_to_raw(
                    events[event_index]["start"],
                    integer_start=integer_start,
                    sampling_rate=sampling_rate,
                    raw_start=raw_start,
                    raw_len=raw_len,
                )
            )
        if any(left > right for left, right in zip(raw_boundaries, raw_boundaries[1:])):
            raise ValueError(f"non-monotonic raw boundaries: {raw_boundaries}")
        repeat_sequence = sequence[query_boundaries[1] : query_boundaries[2]]
        return tuple(raw_boundaries), raw_len, basecall_len, repeat_sequence  # type: ignore[return-value]


def reverse_complement(sequence: str) -> str:
    return sequence.translate(str.maketrans("ACGTN", "TGCAN"))[::-1]


def longest_consecutive_motif(sequence: str, motif: str = "CAG") -> int:
    longest = 0
    for phase in range(len(motif)):
        current = 0
        for offset in range(phase, len(sequence) - len(motif) + 1, len(motif)):
            if sequence[offset : offset + len(motif)] == motif:
                current += 1
                longest = max(longest, current)
            else:
                current = 0
    return longest


def load_warpstr_validation(path: Path) -> dict[str, tuple[int, int, int, int]]:
    if not path.exists():
        return {}
    validation = {}
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                validation[row["read_name"]] = tuple(
                    int(row[field])
                    for field in ("l_start_raw", "l_end_raw", "r_start_raw", "r_end_raw")
                )
            except (KeyError, TypeError, ValueError):
                continue
    return validation


def derive_rows(args: argparse.Namespace) -> tuple[list[dict[str, object]], dict[str, int]]:
    f5index = load_f5index(args.f5index, args.data_root)
    alignments = load_alignments(args.bam)
    validation = load_warpstr_validation(args.warpstr_overview)
    rows = []
    stats = {
        "indexed_reads": len(f5index),
        "aligned_reads": len(alignments),
        "indexed_aligned_reads": len(set(f5index).intersection(alignments)),
        "missing_full_flanks": 0,
        "below_min_mapq": 0,
        "fast5_failures": 0,
    }
    for read_id in sorted(set(f5index).intersection(alignments)):
        if args.max_rows and len(rows) >= args.max_rows:
            break
        selected = select_alignment(alignments[read_id], args.flank_bp)
        if selected is None:
            stats["missing_full_flanks"] += 1
            continue
        alignment, query_boundaries = selected
        alignment_candidates = sum(
            alignment_query_boundaries(candidate, args.flank_bp) is not None
            for candidate in alignments[read_id]
        )
        if alignment.mapq < args.min_mapq:
            stats["below_min_mapq"] += 1
            continue
        try:
            raw_boundaries, raw_len, basecall_len, repeat_sequence = query_boundaries_to_raw(
                f5index[read_id], query_boundaries
            )
        except (OSError, KeyError, ValueError):
            stats["fast5_failures"] += 1
            continue

        qc_pass, qc_reason, rates = boundary_quality(
            query_boundaries, raw_boundaries, alignment_candidates
        )

        _, _, _, hardclip, softclip = cigar_lengths(alignment.cigar)
        if alignment.reverse:
            repeat_sequence = reverse_complement(repeat_sequence)
        expected = validation.get(read_id)
        deltas = [actual - target for actual, target in zip(raw_boundaries, expected)] if expected else [""] * 4
        rows.append(
            {
                "sample": args.sample,
                "read_id": read_id,
                "fast5_path": str(f5index[read_id]),
                "truth_long": "" if args.truth_long is None else args.truth_long,
                "truth_short": "" if args.truth_short is None else args.truth_short,
                # Intentionally blank: independent manifests must not carry
                # baseline-derived per-read allele assignments.
                "group_label": "",
                "signal_window_start": raw_boundaries[0],
                "signal_repeat_start": raw_boundaries[1],
                "signal_repeat_end": raw_boundaries[2],
                "signal_window_end": raw_boundaries[3],
                "signal_len": raw_len,
                "query_window_start": query_boundaries[0],
                "query_repeat_start": query_boundaries[1],
                "query_repeat_end": query_boundaries[2],
                "query_window_end": query_boundaries[3],
                "basecall_len": basecall_len,
                "query_repeat_span": query_boundaries[2] - query_boundaries[1],
                "basecall_cag_longest": longest_consecutive_motif(repeat_sequence),
                "basecall_cag_total": repeat_sequence.count("CAG"),
                "locus_alignment_candidates": alignment_candidates,
                "raw_per_base_left": f"{rates[0]:.6f}",
                "raw_per_base_repeat": f"{rates[1]:.6f}",
                "raw_per_base_right": f"{rates[2]:.6f}",
                "repeat_to_flank_rate_ratio": f"{rates[3]:.6f}",
                "boundary_qc_pass": int(qc_pass),
                "boundary_qc_reason": qc_reason,
                "mapq": alignment.mapq,
                "strand": "-" if alignment.reverse else "+",
                "alignment_flag": alignment.flag,
                "secondary": int(alignment.secondary),
                "supplementary": int(alignment.supplementary),
                "softclip": softclip,
                "hardclip": hardclip,
                "boundary_source": "bam_cigar_native_fast5_events",
                "signal_boundary_source": "bam_cigar_native_fast5_events",
                "warpstr_validation": int(expected is not None),
                "warpstr_delta_window_start": deltas[0],
                "warpstr_delta_repeat_start": deltas[1],
                "warpstr_delta_repeat_end": deltas[2],
                "warpstr_delta_window_end": deltas[3],
            }
        )
    return rows, stats


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def print_summary(rows: list[dict[str, object]], stats: dict[str, int]) -> None:
    print(" ".join(f"{name}={value}" for name, value in stats.items()))
    print(f"windows_derived={len(rows)}")
    high_quality = sum(int(row["mapq"]) >= 20 for row in rows)
    print(f"mapq_ge_20={high_quality}")
    validation_rows = [row for row in rows if row["warpstr_validation"]]
    print(f"warpstr_validation_rows={len(validation_rows)}")
    for field in (
        "warpstr_delta_window_start",
        "warpstr_delta_repeat_start",
        "warpstr_delta_repeat_end",
        "warpstr_delta_window_end",
    ):
        values = [abs(int(row[field])) for row in validation_rows]
        if values:
            print(f"{field}_median_abs={median(values):.1f}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bam", type=Path, default=DEFAULT_BAM)
    parser.add_argument("--f5index", type=Path, default=DEFAULT_F5INDEX)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--warpstr-overview", type=Path, default=DEFAULT_WARPSTR_OVERVIEW)
    parser.add_argument("--flank-bp", type=int, default=DEFAULT_FLANK_BP)
    parser.add_argument("--sample", default="REL3_EXPANDED")
    parser.add_argument("--truth-long", type=int)
    parser.add_argument("--truth-short", type=int)
    parser.add_argument("--min-mapq", type=int, default=0)
    parser.add_argument("--max-rows", type=int, default=0, help="Bound successful rows; 0 means all.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows, stats = derive_rows(args)
    write_rows(args.output, rows)
    print(f"Wrote {len(rows)} rows to {args.output}")
    print_summary(rows, stats)


if __name__ == "__main__":
    main()
