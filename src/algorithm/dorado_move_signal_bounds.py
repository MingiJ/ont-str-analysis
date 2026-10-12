#!/usr/bin/env python3
"""Build truth-free HTT raw-signal boundaries from Dorado move-table tags.

Dorado emits a stride followed by one move value per signal block in the
``mv:B:c`` SAM tag.  ``ts`` and ``ns`` delimit the basecalled interval in the
original raw signal.  This module maps reference locus boundaries through the
alignment CIGAR and then through that move table without consulting genotype
truth.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

try:
    from alignment_signal_bounds import (
        DEFAULT_FLANK_BP,
        FIELDNAMES,
        LOCUS_END_0,
        LOCUS_START_0,
        Alignment,
        alignment_query_boundaries,
        canonical_read_id,
        cigar_lengths,
        longest_consecutive_motif,
        reverse_complement,
        select_alignment,
        write_rows,
    )
    from f5c_signal_bounds import boundary_qc
except ImportError:  # pragma: no cover
    from .alignment_signal_bounds import (
        DEFAULT_FLANK_BP,
        FIELDNAMES,
        LOCUS_END_0,
        LOCUS_START_0,
        Alignment,
        alignment_query_boundaries,
        canonical_read_id,
        cigar_lengths,
        longest_consecutive_motif,
        reverse_complement,
        select_alignment,
        write_rows,
    )
    from .f5c_signal_bounds import boundary_qc


DEFAULT_OUTPUT = Path("ont-str-runner/work/mastr/mastr_dorado_move_signal_bounds.tsv")


@dataclass(frozen=True)
class DoradoRecord:
    alignment: Alignment
    sequence: str
    move_tag: tuple[int, ...] | None
    trim_start: int | None
    signal_end: int | None


def decode_move_values(values: list[int] | tuple[int, ...]) -> list[int]:
    """Decode SAM signed-byte overflow runs used by Dorado move tags."""

    decoded: list[int] = []
    accumulator = 0
    for value in values:
        if not -128 <= value <= 127:
            raise ValueError(f"move-table byte is outside int8 range: {value}")
        accumulator += value
        if value not in (-128, 127):
            decoded.append(accumulator)
            accumulator = 0
    if accumulator:
        raise ValueError("move-table overflow run has no terminating value")
    return decoded


def parse_move_tag(value: str) -> tuple[int, ...]:
    """Parse the value portion of ``mv:B:c,...`` into signed integers."""

    fields = value.split(",")
    if len(fields) < 2 or fields[0] != "c":
        raise ValueError(f"unsupported mv tag encoding: {value}")
    try:
        return tuple(int(item) for item in fields[1:])
    except ValueError as error:
        raise ValueError(f"malformed mv tag: {value}") from error


def move_table_base_boundaries(
    move_tag: tuple[int, ...] | list[int],
    trim_start: int,
    signal_end: int,
    sequence_len: int,
) -> tuple[int, ...]:
    """Return one raw-signal boundary for every base boundary in a read.

    Boundary zero is ``ts`` and the final boundary is the exclusive ``ns``.
    Interior boundary *q* is the signal block in which base *q* is emitted.
    Multiple emissions in one block therefore produce equal base boundaries,
    which downstream QC rejects if they collapse a complete HTT segment.
    """

    if sequence_len <= 0:
        raise ValueError("sequence length must be positive")
    if len(move_tag) < 2:
        raise ValueError("move tag must contain a stride and at least one block")
    stride = int(move_tag[0])
    if stride <= 0:
        raise ValueError(f"move-table stride must be positive, got {stride}")
    if trim_start < 0 or signal_end <= trim_start:
        raise ValueError(f"invalid signal interval: ts={trim_start}, ns={signal_end}")

    moves = decode_move_values(tuple(int(value) for value in move_tag[1:]))
    if any(value < 0 for value in moves):
        raise ValueError("decoded move table contains a negative move")
    if sum(moves) != sequence_len:
        raise ValueError(
            f"move/sequence length mismatch: move_sum={sum(moves)} sequence={sequence_len}"
        )

    emission_blocks: list[int] = []
    for block_index, move in enumerate(moves):
        emission_blocks.extend([block_index] * move)
    if len(emission_blocks) != sequence_len:  # defensive; sum check above is authoritative
        raise ValueError("could not expand move table to the basecalled sequence")

    boundaries = [trim_start]
    boundaries.extend(trim_start + emission_blocks[index] * stride for index in range(1, sequence_len))
    boundaries.append(signal_end)
    if boundaries[-2] > signal_end:
        raise ValueError(
            f"move table extends beyond ns: last interior={boundaries[-2]}, ns={signal_end}"
        )
    if any(left > right for left, right in zip(boundaries, boundaries[1:])):
        raise ValueError("move-derived base boundaries are not monotonic")
    return tuple(boundaries)


def parse_sam_line(line: str) -> DoradoRecord | None:
    fields = line.rstrip("\n").split("\t")
    if len(fields) < 11:
        return None
    flag = int(fields[1])
    if flag & 4 or fields[5] == "*" or fields[9] == "*":
        return None
    tags: dict[str, tuple[str, str]] = {}
    for field in fields[11:]:
        parts = field.split(":", 2)
        if len(parts) == 3:
            tags[parts[0]] = (parts[1], parts[2])

    move_tag = None
    if "mv" in tags:
        tag_type, value = tags["mv"]
        if tag_type != "B":
            raise ValueError(f"mv tag has unsupported SAM type: {tag_type}")
        move_tag = parse_move_tag(value)

    def integer_tag(name: str) -> int | None:
        if name not in tags:
            return None
        tag_type, value = tags[name]
        if tag_type != "i":
            raise ValueError(f"{name} tag has unsupported SAM type: {tag_type}")
        return int(value)

    read_id = canonical_read_id(fields[0])
    return DoradoRecord(
        alignment=Alignment(
            read_id=read_id,
            flag=flag,
            reference_start=int(fields[3]) - 1,
            mapq=int(fields[4]),
            cigar=fields[5],
        ),
        sequence=fields[9].upper(),
        move_tag=move_tag,
        trim_start=integer_tag("ts"),
        signal_end=integer_tag("ns"),
    )


def load_sample_map(path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            read_id = canonical_read_id(row.get("read_id", "").strip())
            sample = row.get("sample", "").strip()
            if not read_id or not sample:
                continue
            previous = mapping.setdefault(read_id, sample)
            if previous != sample:
                raise ValueError(f"read {read_id} is assigned to both {previous} and {sample}")
    if not mapping:
        raise ValueError(f"sample map contains no usable rows: {path}")
    return mapping


def load_dorado_records(bam: Path) -> dict[str, list[DoradoRecord]]:
    command = ["samtools", "view", str(bam), f"chr4:{LOCUS_START_0 + 1}-{LOCUS_END_0}"]
    result = subprocess.run(command, check=True, text=True, capture_output=True)
    grouped: dict[str, list[DoradoRecord]] = defaultdict(list)
    for line in result.stdout.splitlines():
        record = parse_sam_line(line)
        if record is not None:
            grouped[record.alignment.read_id].append(record)
    return dict(grouped)


def selected_record(
    records: list[DoradoRecord], flank_bp: int
) -> tuple[DoradoRecord, tuple[int, int, int, int]] | None:
    selected = select_alignment([record.alignment for record in records], flank_bp)
    if selected is None:
        return None
    alignment, boundaries = selected
    for record in records:
        if record.alignment is alignment:
            return record, boundaries
    raise AssertionError("selected alignment record disappeared")


def derive_rows(
    bam: Path,
    pod5: Path,
    sample_map: Path,
    *,
    flank_bp: int,
    min_mapq: int,
) -> tuple[list[dict[str, object]], dict[str, int]]:
    samples = load_sample_map(sample_map)
    records = load_dorado_records(bam)
    rows: list[dict[str, object]] = []
    stats = {
        "sample_map_reads": len(samples),
        "locus_aligned_reads": len(records),
        "mapped_sample_reads": len(set(samples).intersection(records)),
        "missing_full_flanks": 0,
        "below_min_mapq": 0,
        "hardclip_rejected": 0,
        "missing_move_tags": 0,
        "move_mapping_failures": 0,
    }

    for read_id in sorted(set(samples).intersection(records)):
        selected = selected_record(records[read_id], flank_bp)
        if selected is None:
            stats["missing_full_flanks"] += 1
            continue
        record, query_boundaries = selected
        alignment = record.alignment
        alignment_candidates = sum(
            alignment_query_boundaries(candidate.alignment, flank_bp) is not None
            for candidate in records[read_id]
        )
        if alignment.mapq < min_mapq:
            stats["below_min_mapq"] += 1
            continue

        _, query_len, _, hardclip, softclip = cigar_lengths(alignment.cigar)
        if hardclip:
            stats["hardclip_rejected"] += 1
            continue
        if record.move_tag is None or record.trim_start is None or record.signal_end is None:
            stats["missing_move_tags"] += 1
            continue
        if query_len != len(record.sequence):
            stats["move_mapping_failures"] += 1
            continue

        try:
            base_boundaries = move_table_base_boundaries(
                record.move_tag,
                record.trim_start,
                record.signal_end,
                len(record.sequence),
            )
            raw_boundaries = tuple(base_boundaries[index] for index in query_boundaries)
        except (IndexError, ValueError):
            stats["move_mapping_failures"] += 1
            continue

        query_spans = tuple(
            right - left for left, right in zip(query_boundaries, query_boundaries[1:])
        )
        raw_spans = tuple(
            right - left for left, right in zip(raw_boundaries, raw_boundaries[1:])
        )
        qc_pass, qc_reason, rates = boundary_qc(
            raw_spans[0], raw_spans[1], raw_spans[2], query_spans, alignment_candidates
        )

        native_sequence = (
            reverse_complement(record.sequence) if alignment.reverse else record.sequence
        )
        repeat_sequence = native_sequence[query_boundaries[1] : query_boundaries[2]]
        if alignment.reverse:
            repeat_sequence = reverse_complement(repeat_sequence)

        rows.append(
            {
                "sample": samples[read_id],
                "read_id": read_id,
                "fast5_path": str(pod5),
                "truth_long": "",
                "truth_short": "",
                "group_label": "",
                "signal_window_start": raw_boundaries[0],
                "signal_repeat_start": raw_boundaries[1],
                "signal_repeat_end": raw_boundaries[2],
                "signal_window_end": raw_boundaries[3],
                "signal_len": record.signal_end,
                "query_window_start": query_boundaries[0],
                "query_repeat_start": query_boundaries[1],
                "query_repeat_end": query_boundaries[2],
                "query_window_end": query_boundaries[3],
                "basecall_len": len(record.sequence),
                "query_repeat_span": query_spans[1],
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
                "boundary_source": "bam_cigar_dorado_move_table",
                "signal_boundary_source": "dorado_0.7.3_mv_r9.4.1_4khz",
                "warpstr_validation": "",
                "warpstr_delta_window_start": "",
                "warpstr_delta_repeat_start": "",
                "warpstr_delta_repeat_end": "",
                "warpstr_delta_window_end": "",
            }
        )
    return rows, stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bam", type=Path, required=True)
    parser.add_argument("--pod5", type=Path, required=True)
    parser.add_argument("--sample-map", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--flank-bp", type=int, default=DEFAULT_FLANK_BP)
    parser.add_argument("--min-mapq", type=int, default=20)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows, stats = derive_rows(
        args.bam,
        args.pod5,
        args.sample_map,
        flank_bp=args.flank_bp,
        min_mapq=args.min_mapq,
    )
    write_rows(args.output, rows)
    print(" ".join(f"{name}={value}" for name, value in stats.items()))
    print(f"windows_derived={len(rows)}")
    print(f"boundary_qc_pass={sum(int(row['boundary_qc_pass']) for row in rows)}")
    print(f"Wrote truth-free Dorado move-table boundaries to {args.output}")


if __name__ == "__main__":
    main()
