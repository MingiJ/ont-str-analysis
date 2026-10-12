#!/usr/bin/env python3
"""Build a per-read evidence table for HTT CAG algorithm development.

The table joins whatever evidence is already available from baseline tools.
It deliberately avoids raw-signal extraction; this is the stable metadata layer
that the future signal-window code can extend.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import median


GROUND_TRUTH = {
    "GM04723": (72, 17),
    "GM04767": (47, 18),
    "ND30015": (41, 20),
    "ND30016": (41, 21),
    "ND30047": (41, 18),
    "ND30422": (40, 18),
    "ND30626": (41, 21),
    "ND31038": (44, 19),
    "ND31551": (39, 18),
    "ND33392": (57, 17),
    "ND33392_WARPSTR_SMALL": (57, 17),
    "ND33947": (40, 18),
}

DEFAULT_SAMPLES = (
    "GM04723",
    "ND30015",
    "ND30016",
    "ND30047",
    "ND30422",
    "ND30626",
    "ND31551",
    "ND33392",
    "ND33947",
)
LOCUS = "chr4:3074876-3074933"
MOTIF = "CAG"
MOTIF_LEN = len(MOTIF)
READ_SUFFIX = "_Basecall_Alignment_template"

FIELDNAMES = [
    "sample",
    "read_id",
    "truth_long",
    "truth_short",
    "locus",
    "motif",
    "fast5_path",
    "in_warpstr",
    "warpstr_saved",
    "warpstr_count",
    "warpstr_raw_value",
    "warpstr_basecall_count",
    "warpstr_basecall_raw_value",
    "warpstr_reverse",
    "warpstr_dtw_cost1",
    "warpstr_dtw_cost2",
    "signal_window_start",
    "signal_window_end",
    "signal_len",
    "signal_boundary_source",
    "alignment_flag",
    "secondary",
    "supplementary",
    "basecall_len",
    "in_strique",
    "strique_count",
    "strique_counts_all",
    "strique_strand",
    "strique_duplicate_rows",
    "in_deeprepeat",
    "deeprepeat_strand_flag",
    "deeprepeat_allocation",
    "mapq",
    "strand",
    "softclip",
    "locus_ref_overlap_bp",
    "locus_inserted_bp",
    "locus_deleted_bp",
    "group_label",
]


def read_csv_dicts(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def to_int(value: str | None) -> int | None:
    if value in (None, "", "-"):
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def to_float(value: str | None) -> float | None:
    if value in (None, "", "-"):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def as_text(value: object) -> str:
    return "" if value is None else str(value)


def raw_to_repeats(raw_value: int | None) -> int | None:
    if raw_value is None:
        return None
    return round(raw_value / MOTIF_LEN)


def canonical_read_id(value: str) -> str:
    return value.removesuffix(READ_SUFFIX)


def load_f5index(data_root: Path, sample: str) -> dict[str, str]:
    data_dir = data_root / sample
    candidates = [data_dir / "htt.f5index", data_dir / "HTT_CAG.f5index"]
    mapping: dict[str, str] = {}
    for path in candidates:
        if not path.exists():
            continue
        with path.open() as handle:
            for line in handle:
                fields = line.rstrip("\n").split("\t")
                if len(fields) >= 2:
                    read_id = canonical_read_id(fields[0])
                    if read_id not in mapping or not fields[0].endswith(READ_SUFFIX):
                        mapping[read_id] = str(data_dir / fields[1])
        break
    return mapping


def load_warpstr_fast5_index(work_root: Path, sample: str) -> dict[str, str]:
    fast5_dir = work_root / "warpstr" / sample / "HTT_CAG" / "fast5" / sample
    mapping: dict[str, str] = {}
    if not fast5_dir.exists():
        return mapping
    for path in sorted(fast5_dir.glob("*.fast5")):
        mapping[path.stem] = str(path)
    return mapping


def load_warpstr(work_root: Path, sample: str) -> dict[str, dict[str, object]]:
    overview = work_root / "warpstr" / sample / "HTT_CAG" / "overview.csv"
    rows: dict[str, dict[str, object]] = {}
    for row in read_csv_dicts(overview):
        read_id = row.get("read_name")
        if not read_id:
            continue
        result_raw = to_int(row.get("results"))
        orig_raw = to_int(row.get("orig"))
        start = to_int(row.get("l_start_raw"))
        end = to_int(row.get("r_end_raw"))
        signal_len = abs(end - start) if start is not None and end is not None else None
        rows[read_id] = {
            "in_warpstr": 1,
            "warpstr_saved": to_int(row.get("saved")),
            "warpstr_count": raw_to_repeats(result_raw),
            "warpstr_raw_value": result_raw,
            "warpstr_basecall_count": raw_to_repeats(orig_raw),
            "warpstr_basecall_raw_value": orig_raw,
            "warpstr_reverse": row.get("reverse"),
            "warpstr_dtw_cost1": to_float(row.get("dtw_cost1")),
            "warpstr_dtw_cost2": to_float(row.get("dtw_cost2")),
            "signal_window_start": start,
            "signal_window_end": end,
            "signal_len": signal_len,
        }
    return rows


def load_strique(work_root: Path, sample: str) -> dict[str, dict[str, object]]:
    path = work_root / "strique" / f"{sample}.txt"
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_csv_dicts(path, delimiter="\t"):
        read_id = row.get("ID")
        if read_id:
            grouped[read_id].append(row)

    rows: dict[str, dict[str, object]] = {}
    for read_id, calls in grouped.items():
        counts = [to_int(call.get("count")) for call in calls]
        counts = [count for count in counts if count is not None]
        strands = sorted({call.get("strand", "") for call in calls if call.get("strand")})
        rows[read_id] = {
            "in_strique": 1,
            "strique_count": int(median(counts)) if counts else None,
            "strique_counts_all": ";".join(str(count) for count in counts),
            "strique_strand": ";".join(strands),
            "strique_duplicate_rows": len(calls),
        }
    return rows


def load_deeprepeat(work_root: Path, sample: str) -> dict[str, dict[str, object]]:
    sample_dir = work_root / "deeprepeat" / sample
    candidates = sorted(sample_dir.glob("*.fs.more*"))
    rows: dict[str, dict[str, object]] = {}
    if not candidates:
        return rows
    # Prefer the shortest/current file name over retry/filter suffixes when present.
    path = sorted(candidates, key=lambda p: (len(p.name), p.name))[0]
    with path.open() as handle:
        for line in handle:
            fields = line.split()
            if len(fields) >= 3:
                rows[fields[2]] = {
                    "in_deeprepeat": 1,
                    "deeprepeat_strand_flag": fields[1],
                    "deeprepeat_allocation": None,
                }
    return rows


def load_rel3_alignment_context(work_root: Path, sample: str) -> dict[str, dict[str, object]]:
    if sample != "REL3_WARPSTR_OK":
        return {}
    path = work_root / "rel3" / "rel3_warpstr_ok_alignment_context.tsv"
    rows: dict[str, dict[str, object]] = {}
    for row in read_csv_dicts(path, delimiter="\t"):
        read_id = row.get("read_id")
        if not read_id:
            continue
        rows[read_id] = {
            "mapq": to_int(row.get("bam_mapq")),
            "strand": "-" if row.get("bam_reverse") == "1" else "+" if row.get("bam_reverse") == "0" else None,
            "softclip": to_int(row.get("bam_softclip_bp")),
            "locus_ref_overlap_bp": to_int(row.get("locus_ref_overlap_bp")),
            "locus_inserted_bp": to_int(row.get("locus_inserted_bp")),
            "locus_deleted_bp": to_int(row.get("locus_deleted_bp")),
        }
    return rows


def load_alignment_signal_bounds(work_root: Path, sample: str) -> dict[str, dict[str, object]]:
    if sample != "REL3_EXPANDED":
        return {}
    path = work_root / "rel3" / "rel3_alignment_signal_bounds.tsv"
    rows: dict[str, dict[str, object]] = {}
    for row in read_csv_dicts(path, delimiter="\t"):
        read_id = row.get("read_id")
        start = to_int(row.get("signal_window_start"))
        end = to_int(row.get("signal_window_end"))
        if not read_id or start is None or end is None:
            continue
        rows[read_id] = {
            "signal_window_start": start,
            "signal_window_end": end,
            "signal_len": abs(end - start),
            "signal_boundary_source": row.get("boundary_source"),
            "alignment_flag": to_int(row.get("alignment_flag")),
            "secondary": to_int(row.get("secondary")),
            "supplementary": to_int(row.get("supplementary")),
            "basecall_len": to_int(row.get("basecall_len")),
            "mapq": to_int(row.get("mapq")),
            "strand": row.get("strand"),
            "softclip": to_int(row.get("softclip")),
        }
    return rows


def label_group(row: dict[str, object], truth: tuple[int, int] | None) -> str:
    if truth is None:
        return "unknown_truth"
    truth_long, truth_short = truth
    candidates = [
        row.get("warpstr_count"),
        row.get("strique_count"),
        row.get("warpstr_basecall_count"),
    ]
    numeric = [value for value in candidates if isinstance(value, int)]
    if not numeric:
        return "unlabeled"
    nearest = min(numeric, key=lambda value: min(abs(value - truth_long), abs(value - truth_short)))
    return "long_like" if abs(nearest - truth_long) <= abs(nearest - truth_short) else "short_like"


def build_sample_rows(repo_root: Path, sample: str) -> list[dict[str, object]]:
    work_root = repo_root / "ont-str-runner" / "work"
    data_root = repo_root / "ont-str-runner" / "data"

    truth = GROUND_TRUTH.get(sample)
    data_sample = "REL3" if sample == "REL3_EXPANDED" else sample
    f5index = load_f5index(data_root, data_sample)
    if not f5index:
        f5index = load_warpstr_fast5_index(work_root, sample)
    sources = [
        load_warpstr(work_root, sample),
        load_strique(work_root, sample),
        load_deeprepeat(work_root, sample),
        load_rel3_alignment_context(work_root, sample),
        load_alignment_signal_bounds(work_root, sample),
    ]
    read_ids = sorted(set(f5index).union(*(set(source) for source in sources)))

    rows = []
    for read_id in read_ids:
        row: dict[str, object] = {
            "sample": sample,
            "read_id": read_id,
            "truth_long": truth[0] if truth else None,
            "truth_short": truth[1] if truth else None,
            "locus": LOCUS,
            "motif": MOTIF,
            "fast5_path": f5index.get(read_id),
            "in_warpstr": 0,
            "in_strique": 0,
            "in_deeprepeat": 0,
        }
        for source in sources:
            row.update(source.get(read_id, {}))
        row["group_label"] = label_group(row, truth)
        rows.append(row)
    return rows


def write_table(rows: list[dict[str, object]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: as_text(row.get(field)) for field in FIELDNAMES})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build per-read HTT CAG evidence table.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--samples", nargs="+", default=list(DEFAULT_SAMPLES))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("ont-str-runner/work/analysis/evidence_table.tsv"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    output = args.output if args.output.is_absolute() else repo_root / args.output
    rows: list[dict[str, object]] = []
    for sample in args.samples:
        rows.extend(build_sample_rows(repo_root, sample))
    write_table(rows, output)
    print(f"Wrote {len(rows)} rows to {output}")


if __name__ == "__main__":
    main()
