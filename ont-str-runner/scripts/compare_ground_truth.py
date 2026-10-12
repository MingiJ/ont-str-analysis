#!/usr/bin/env python3
"""Compare HTT CAG benchmark outputs against published ground truth.

The strict mode used for the thesis benchmark excludes partial tool outputs
from final metrics. Partial outputs are still recorded in the failure table so
they can be debugged without accidentally becoming evidence.
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[1]
WARPSTR_ROOT = ROOT / "work" / "warpstr"
DEEP_ROOT = ROOT / "work" / "deeprepeat"
STRIQUE_ROOT = ROOT / "work" / "strique"
OUT_DIR = ROOT / "work" / "analysis"
OUT_CSV = OUT_DIR / "ground_truth_comparison.csv"
FAILURES_TSV = OUT_DIR / "benchmark_failures.tsv"
REPORT_MD = OUT_DIR / "benchmark_report.md"
MOTIF_LEN = 3

# Ground truth from Monteys et al. Supplementary Table S4.
GROUND_TRUTH = {
    "GM04723": (72, 17),
    "ND30015": (41, 20),
    "ND30016": (41, 21),
    "ND30047": (41, 18),
    "ND30422": (40, 18),
    "ND30626": (41, 21),
    "ND31551": (39, 18),
    "ND33392": (57, 17),
    "ND33947": (40, 18),
}

TRUTH_SAMPLES = tuple(GROUND_TRUTH)
FATAL_PATTERNS = ("Traceback", "OSError", "Error", "Exception")
FAILURE_FIELDS = ["sample", "tool", "status", "reason", "path"]


def read_alleles_csv(path: Path) -> dict[str, int | None]:
    with path.open(newline="") as handle:
        row = next(csv.DictReader(handle))

    def as_int(key: str) -> int | None:
        value = row.get(key)
        if value in (None, "", "-"):
            return None
        return int(float(value))

    return {
        "warp_a1": as_int("WarpSTR_allele1"),
        "warp_a1_freq": as_int("WarpSTR_allele1_freq"),
        "warp_a2": as_int("WarpSTR_allele2"),
        "warp_a2_freq": as_int("WarpSTR_allele2_freq"),
        "base_a1": as_int("basecall_allele1"),
        "base_a1_freq": as_int("basecall_allele1_freq"),
        "base_a2": as_int("basecall_allele2"),
        "base_a2_freq": as_int("basecall_allele2_freq"),
    }


def choose_peaks(a1: int | None, a2: int | None) -> tuple[int | None, int | None]:
    values = [value for value in (a1, a2) if value is not None]
    if not values:
        return None, None
    return max(values), min(values) if len(values) > 1 else None


def frequency_for_peak(a1: int | None, f1: int | None, a2: int | None, f2: int | None, peak: int | None) -> int | None:
    if peak is None:
        return None
    if a1 == peak:
        return f1
    if a2 == peak:
        return f2
    return None


def approx_repeats(bp: int | None) -> int | None:
    if bp is None:
        return None
    # WarpSTR/basecall allele fields are sequence/base lengths in this workflow.
    return int(round(bp / float(MOTIF_LEN)))


def delta(call: int | None, truth: int | None) -> int | None:
    if call is None or truth is None:
        return None
    return call - truth


def read_overview_stats(path: Path) -> dict[str, int | None]:
    if not path.exists():
        return {"warp_overview_total": None, "warp_overview_neg": None, "warp_overview_high": None}
    total = neg = high = 0
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            total += 1
            try:
                value = float(row["results"])
            except Exception:
                continue
            if value < 0:
                neg += 1
            if value > 300:
                high += 1
    return {"warp_overview_total": total, "warp_overview_neg": neg, "warp_overview_high": high}


def blank_warpstr() -> dict[str, object]:
    keys = [
        "warp_peak_long",
        "warp_peak_short",
        "warp_peak_long_reads",
        "warp_peak_short_reads",
        "base_peak_long",
        "base_peak_short",
        "base_peak_long_reads",
        "base_peak_short_reads",
        "warp_long_rep",
        "warp_short_rep",
        "warp_long_delta",
        "warp_short_delta",
        "base_long_rep",
        "base_short_rep",
        "base_long_delta",
        "base_short_delta",
        "warpstr_complete",
    ]
    return {key: None for key in keys}


def warpstr_stats(sample: str, truth_long: int, truth_short: int) -> tuple[dict[str, object], list[dict[str, str]]]:
    failures: list[dict[str, str]] = []
    stats = blank_warpstr()
    alleles_path = WARPSTR_ROOT / sample / "HTT_CAG" / "predictions" / "alleles.csv"
    overview_path = WARPSTR_ROOT / sample / "HTT_CAG" / "overview.csv"
    stats.update(read_overview_stats(overview_path))

    if not alleles_path.exists():
        reason = "missing predictions/alleles.csv"
        if overview_path.exists():
            reason = "overview.csv exists but predictions/alleles.csv is missing"
        failures.append({"sample": sample, "tool": "WarpSTR", "status": "incomplete", "reason": reason, "path": str(alleles_path)})
        stats["warpstr_complete"] = False
        return stats, failures

    try:
        alleles = read_alleles_csv(alleles_path)
    except Exception as exc:
        failures.append({"sample": sample, "tool": "WarpSTR", "status": "failed", "reason": f"unparseable alleles.csv: {exc}", "path": str(alleles_path)})
        stats["warpstr_complete"] = False
        return stats, failures

    warp_long, warp_short = choose_peaks(alleles["warp_a1"], alleles["warp_a2"])
    base_long, base_short = choose_peaks(alleles["base_a1"], alleles["base_a2"])
    warp_long_rep = approx_repeats(warp_long)
    warp_short_rep = approx_repeats(warp_short)
    base_long_rep = approx_repeats(base_long)
    base_short_rep = approx_repeats(base_short)

    stats.update(
        {
            "warp_peak_long": warp_long,
            "warp_peak_short": warp_short,
            "warp_peak_long_reads": frequency_for_peak(alleles["warp_a1"], alleles["warp_a1_freq"], alleles["warp_a2"], alleles["warp_a2_freq"], warp_long),
            "warp_peak_short_reads": frequency_for_peak(alleles["warp_a1"], alleles["warp_a1_freq"], alleles["warp_a2"], alleles["warp_a2_freq"], warp_short),
            "base_peak_long": base_long,
            "base_peak_short": base_short,
            "base_peak_long_reads": frequency_for_peak(alleles["base_a1"], alleles["base_a1_freq"], alleles["base_a2"], alleles["base_a2_freq"], base_long),
            "base_peak_short_reads": frequency_for_peak(alleles["base_a1"], alleles["base_a1_freq"], alleles["base_a2"], alleles["base_a2_freq"], base_short),
            "warp_long_rep": warp_long_rep,
            "warp_short_rep": warp_short_rep,
            "warp_long_delta": delta(warp_long_rep, truth_long),
            "warp_short_delta": delta(warp_short_rep, truth_short),
            "base_long_rep": base_long_rep,
            "base_short_rep": base_short_rep,
            "base_long_delta": delta(base_long_rep, truth_long),
            "base_short_delta": delta(base_short_rep, truth_short),
            "warpstr_complete": True,
        }
    )
    return stats, failures


def pick_deeprepeat_log(sample_dir: Path) -> Path | None:
    preferred = [sample_dir / "htt_retry.log", sample_dir / "htt.log"]
    for path in preferred:
        if path.exists():
            return path
    logs = sorted(sample_dir.glob("*htt*.log"))
    return logs[0] if logs else None


def deeprepeat_stats(sample: str) -> tuple[dict[str, object], list[dict[str, str]]]:
    sample_dir = DEEP_ROOT / sample
    log_path = pick_deeprepeat_log(sample_dir)
    fs_more = sample_dir / f"{sample}.fs.more.retry"
    if not fs_more.exists():
        fs_more = sample_dir / f"{sample}.fs.more"
    failures: list[dict[str, str]] = []

    stats: dict[str, object] = {
        "deeprepeat_complete": False,
        "deeprepeat_log": str(log_path) if log_path else None,
        "deeprepeat_reads_reported": None,
        "deeprepeat_warn_count": None,
        "deeprepeat_repeat_info": None,
        "deeprepeat_fs_more_count": None,
        "deeprepeat_gmm_peaks": None,
        "deeprepeat_allocr_top2": None,
        "deeprepeat_allocr_short_peak": None,
        "deeprepeat_allocr_short_count": None,
        "deeprepeat_allocr_long_peak": None,
        "deeprepeat_allocr_long_count": None,
        "deeprepeat_gmm_missed_short": None,
    }

    if fs_more.exists():
        with fs_more.open() as handle:
            stats["deeprepeat_fs_more_count"] = sum(1 for _ in handle)

    if log_path is None or not log_path.exists():
        failures.append({"sample": sample, "tool": "DeepRepeat", "status": "incomplete", "reason": "missing htt.log", "path": str(sample_dir)})
        return stats, failures

    text = log_path.read_text(errors="ignore")
    fatal_hits = [pattern for pattern in FATAL_PATTERNS if pattern in text]
    if "Testing Finished!" not in text:
        failures.append({"sample": sample, "tool": "DeepRepeat", "status": "incomplete", "reason": "missing Testing Finished! marker", "path": str(log_path)})
    if fatal_hits:
        failures.append({"sample": sample, "tool": "DeepRepeat", "status": "failed", "reason": "fatal log markers: " + ",".join(fatal_hits), "path": str(log_path)})

    reads = re.search(r"There are\s+(\d+)\s+reads", text)
    if reads:
        stats["deeprepeat_reads_reported"] = int(reads.group(1))
    stats["deeprepeat_warn_count"] = text.count("Warning!!! less split points generated")
    stats["deeprepeat_repeat_info"] = text.count("Repeat Info:")

    gmm_peaks: list[int] = []
    match = re.search(r"GMM:.*?\[([^\]]+)\]", text)
    if match:
        gmm_peaks = [int(value.strip()) for value in match.group(1).split(",") if value.strip().isdigit()]
    stats["deeprepeat_gmm_peaks"] = ",".join(str(value) for value in gmm_peaks) if gmm_peaks else None

    allocr: dict[int, int] = {}
    match = re.search(r"allocr:([^\n]+)", text)
    if match:
        for part in match.group(1).strip().rstrip(",").split(","):
            if ":" not in part:
                continue
            key, value = part.strip().split(":", 1)
            try:
                allocr[int(key)] = int(value)
            except ValueError:
                continue

    top2 = sorted(allocr.items(), key=lambda item: item[1], reverse=True)[:2]
    stats["deeprepeat_allocr_top2"] = ";".join(f"{key}:{value}" for key, value in top2) if top2 else None
    short_candidates = {key: value for key, value in allocr.items() if 15 <= key <= 25}
    long_candidates = {key: value for key, value in allocr.items() if 35 <= key <= 80}
    if short_candidates:
        short_peak = max(short_candidates.items(), key=lambda item: item[1])[0]
        stats["deeprepeat_allocr_short_peak"] = short_peak
        stats["deeprepeat_allocr_short_count"] = short_candidates[short_peak]
    if long_candidates:
        long_peak = max(long_candidates.items(), key=lambda item: item[1])[0]
        stats["deeprepeat_allocr_long_peak"] = long_peak
        stats["deeprepeat_allocr_long_count"] = long_candidates[long_peak]

    short_count = stats["deeprepeat_allocr_short_count"]
    long_count = stats["deeprepeat_allocr_long_count"]
    short_peak = stats["deeprepeat_allocr_short_peak"]
    if isinstance(short_count, int) and isinstance(long_count, int) and isinstance(short_peak, int) and gmm_peaks:
        short_ratio = short_count / float(short_count + long_count)
        stats["deeprepeat_gmm_missed_short"] = short_ratio >= 0.2 and min(gmm_peaks) >= short_peak + 8

    if not gmm_peaks and not allocr:
        failures.append({"sample": sample, "tool": "DeepRepeat", "status": "incomplete", "reason": "no parseable GMM/allocr evidence", "path": str(log_path)})
    if not failures:
        stats["deeprepeat_complete"] = True
    return stats, failures


def strique_stats(sample: str) -> tuple[dict[str, object], list[dict[str, str]]]:
    txt_path = STRIQUE_ROOT / f"{sample}.txt"
    stats: dict[str, object] = {
        "strique_complete": False,
        "strique_txt": str(txt_path) if txt_path.exists() else None,
        "strique_total": None,
        "strique_zero": None,
        "strique_high": None,
        "strique_filtered": None,
        "strique_peak_short": None,
        "strique_peak_short_reads": None,
        "strique_peak_long": None,
        "strique_peak_long_reads": None,
        "strique_long_rep": None,
        "strique_long_delta": None,
        "strique_short_rep": None,
        "strique_short_delta": None,
    }
    failures: list[dict[str, str]] = []

    if not txt_path.exists() or txt_path.stat().st_size == 0:
        failures.append({"sample": sample, "tool": "STRique", "status": "incomplete", "reason": "missing or empty output txt", "path": str(txt_path)})
        return stats, failures

    counts: list[int] = []
    zero_count = high_count = 0
    try:
        with txt_path.open(newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            for row in reader:
                if row.get("target") and row["target"] != "HTT_CAG":
                    continue
                try:
                    value = int(float(row["count"]))
                except Exception:
                    continue
                counts.append(value)
                if value <= 0:
                    zero_count += 1
                if value > 200:
                    high_count += 1
    except Exception as exc:
        failures.append({"sample": sample, "tool": "STRique", "status": "failed", "reason": f"unparseable output: {exc}", "path": str(txt_path)})
        return stats, failures

    filtered = [count for count in counts if 1 <= count <= 200]
    hist = Counter(filtered)

    def peak_in_range(lo: int, hi: int) -> tuple[int | None, int | None]:
        items = [(key, value) for key, value in hist.items() if lo <= key <= hi]
        if not items:
            return None, None
        return max(items, key=lambda item: (item[1], -item[0]))

    short_peak, short_reads = peak_in_range(10, 29)
    long_peak, long_reads = peak_in_range(30, 120)
    stats.update(
        {
            "strique_total": len(counts),
            "strique_zero": zero_count,
            "strique_high": high_count,
            "strique_filtered": len(filtered),
            "strique_peak_short": short_peak,
            "strique_peak_short_reads": short_reads,
            "strique_peak_long": long_peak,
            "strique_peak_long_reads": long_reads,
            "strique_complete": bool(counts and short_peak is not None and long_peak is not None),
        }
    )
    if not stats["strique_complete"]:
        failures.append({"sample": sample, "tool": "STRique", "status": "incomplete", "reason": "missing parseable short or long peak", "path": str(txt_path)})
    return stats, failures


def build_rows(samples: tuple[str, ...]) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    rows: list[dict[str, object]] = []
    failures: list[dict[str, str]] = []
    for sample in samples:
        truth_long, truth_short = GROUND_TRUTH[sample]
        row: dict[str, object] = {"sample": sample, "truth_long": truth_long, "truth_short": truth_short}

        stats, tool_failures = warpstr_stats(sample, truth_long, truth_short)
        row.update(stats)
        failures.extend(tool_failures)

        stats, tool_failures = deeprepeat_stats(sample)
        row.update(stats)
        failures.extend(tool_failures)

        stats, tool_failures = strique_stats(sample)
        row.update(stats)
        strique_long = row.get("strique_peak_long")
        strique_short = row.get("strique_peak_short")
        if isinstance(strique_long, int):
            row["strique_long_rep"] = strique_long
            row["strique_long_delta"] = strique_long - truth_long
        if isinstance(strique_short, int):
            row["strique_short_rep"] = strique_short
            row["strique_short_delta"] = strique_short - truth_short
        failures.extend(tool_failures)

        row["benchmark_complete"] = bool(row.get("warpstr_complete") and row.get("deeprepeat_complete") and row.get("strique_complete"))
        rows.append(row)
    return rows, failures


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_failures(path: Path, failures: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FAILURE_FIELDS, delimiter="\t")
        writer.writeheader()
        for failure in failures:
            writer.writerow(failure)


def abs_values(rows: list[dict[str, object]], key: str) -> list[int]:
    values: list[int] = []
    for row in rows:
        value = row.get(key)
        if isinstance(value, int):
            values.append(abs(value))
    return values


def metric_line(label: str, values: list[int]) -> str:
    if not values:
        return f"- {label}: unavailable"
    return f"- {label}: {mean(values):.3f} repeats over {len(values)} calls"


def write_report(path: Path, rows: list[dict[str, object]], failures: list[dict[str, str]]) -> None:
    complete_rows = [row for row in rows if row.get("benchmark_complete")]
    warp_rows = [row for row in rows if row.get("warpstr_complete")]
    strique_rows = [row for row in rows if row.get("strique_complete")]
    deep_rows = [row for row in rows if row.get("deeprepeat_complete")]
    missed_short = sum(1 for row in rows if row.get("deeprepeat_gmm_missed_short") is True)

    lines = [
        "# HTT CAG Benchmark Report",
        "",
        "## Plain-English Takeaway",
        "",
        f"{len(complete_rows)}/{len(rows)} truth samples have strict complete outputs from WarpSTR, DeepRepeat, and STRique.",
        "Partial outputs are recorded for debugging but should not be used as final thesis metrics.",
        "",
        "## Completion",
        "",
        f"- WarpSTR complete: {len(warp_rows)}/{len(rows)}",
        f"- DeepRepeat complete: {len(deep_rows)}/{len(rows)}",
        f"- STRique complete: {len(strique_rows)}/{len(rows)}",
        f"- Failure/incomplete records: {len(failures)}",
        "",
        "## Unit Policy",
        "",
        "- WarpSTR/basecall allele fields are treated as sequence/base lengths and converted to CAG repeats by dividing by 3 and rounding.",
        "- STRique counts are treated as repeat counts directly.",
        "- DeepRepeat GMM/allocr values are treated as repeat counts directly, but DeepRepeat is reported separately because it does not emit the same allele CSV as WarpSTR/STRique.",
        "",
        "## MAE Summary",
        "",
        metric_line("WarpSTR long-allele MAE", abs_values(warp_rows, "warp_long_delta")),
        metric_line("WarpSTR short-allele MAE", abs_values(warp_rows, "warp_short_delta")),
        metric_line("STRique long-allele MAE", abs_values(strique_rows, "strique_long_delta")),
        metric_line("STRique short-allele MAE", abs_values(strique_rows, "strique_short_delta")),
        f"- DeepRepeat missed-short flags: {missed_short}",
        "",
        "## Output Files",
        "",
        f"- Comparison CSV: `{OUT_CSV}`",
        f"- Failure table: `{FAILURES_TSV}`",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare strict HTT CAG benchmark outputs.")
    parser.add_argument("--samples", nargs="+", default=list(TRUTH_SAMPLES), help="Samples to compare.")
    parser.add_argument("--output", type=Path, default=OUT_CSV)
    parser.add_argument("--failures", type=Path, default=FAILURES_TSV)
    parser.add_argument("--report", type=Path, default=REPORT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    samples = tuple(args.samples)
    unknown = [sample for sample in samples if sample not in GROUND_TRUTH]
    if unknown:
        raise SystemExit("Unknown truth samples: " + ", ".join(unknown))
    rows, failures = build_rows(samples)
    write_csv(args.output, rows)
    write_failures(args.failures, failures)
    write_report(args.report, rows, failures)
    print(f"Wrote {args.output}")
    print(f"Wrote {args.failures}")
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
