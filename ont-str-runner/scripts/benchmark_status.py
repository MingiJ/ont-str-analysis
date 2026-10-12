#!/usr/bin/env python3
"""Print input and strict-output status for the HTT CAG benchmark."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data"
SAMPLES = (
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


def has_fast5(sample_dir: Path) -> bool:
    fast5_dir = sample_dir / "workspace" / "pass" / "0"
    return fast5_dir.exists() and any(fast5_dir.rglob("*.fast5"))


def has_archive(sample_dir: Path, sample: str) -> bool:
    patterns = (f"{sample}.tar.gz", f"{sample}.tar.gz.*", f"{sample}.tgz", f"{sample}.tar")
    return any(any(sample_dir.glob(pattern)) for pattern in patterns)


def bam_status(sample_dir: Path, sample: str) -> tuple[bool, bool]:
    bam = sample_dir / f"{sample}.bam"
    bai = sample_dir / f"{sample}.bam.bai"
    if not bam.exists():
        bam = sample_dir / "bam" / f"{sample}.bam"
        bai = sample_dir / "bam" / f"{sample}.bam.bai"
    return bam.exists(), bai.exists()


def deeprepeat_complete(sample: str) -> bool:
    log = ROOT / "work" / "deeprepeat" / sample / "htt.log"
    if not log.exists():
        return False
    text = log.read_text(errors="ignore")
    if "Testing Finished!" not in text:
        return False
    return not any(marker in text for marker in ("Traceback", "OSError", "Error", "Exception"))


def strique_complete(sample: str) -> bool:
    path = ROOT / "work" / "strique" / f"{sample}.txt"
    if not path.exists() or path.stat().st_size == 0:
        return False
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            try:
                int(float(row.get("count", "")))
            except Exception:
                continue
            return True
    return False


def yes(value: bool) -> str:
    return "yes" if value else "no"


def main() -> None:
    fields = [
        "sample",
        "archive",
        "fast5",
        "bam",
        "bai",
        "htt_f5index",
        "warpstr_alleles",
        "deeprepeat_complete",
        "strique_complete",
    ]
    writer = csv.DictWriter(sys.stdout, fieldnames=fields, delimiter="\t")
    writer.writeheader()
    for sample in SAMPLES:
        sample_dir = DATA_ROOT / sample
        bam, bai = bam_status(sample_dir, sample)
        writer.writerow(
            {
                "sample": sample,
                "archive": yes(has_archive(sample_dir, sample)),
                "fast5": yes(has_fast5(sample_dir)),
                "bam": yes(bam),
                "bai": yes(bai),
                "htt_f5index": yes((sample_dir / "htt.f5index").exists()),
                "warpstr_alleles": yes((ROOT / "work" / "warpstr" / sample / "HTT_CAG" / "predictions" / "alleles.csv").exists()),
                "deeprepeat_complete": yes(deeprepeat_complete(sample)),
                "strique_complete": yes(strique_complete(sample)),
            }
        )


if __name__ == "__main__":
    main()
