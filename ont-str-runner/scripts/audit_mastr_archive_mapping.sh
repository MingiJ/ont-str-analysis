#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}
WORK_ROOT=${MASTR_WORK_ROOT:-$REPO_ROOT/ont-str-runner/work/mastr}
MANIFEST=${MASTR_ACQUISITION_MANIFEST:-$REPO_ROOT/ont-str-runner/configs/mastr_confirmation_acquisition.tsv}
FAST_BAM=${MASTR_SELECTION_BAM:-$WORK_ROOT/mastr.dorado-0.7.3.r9-fast-v3.4.selection.bam}
SAMPLE_MAP=${MASTR_SAMPLE_MAP:-$WORK_ROOT/selected_read_samples.tsv}
READ_IDS=${MASTR_READ_IDS:-$WORK_ROOT/selected_read_ids.txt}
PYTHON=${PYTHON:-$REPO_ROOT/.venv/bin/python}
MINIMAP2_IMAGE=${MINIMAP2_IMAGE:-wkusmirek/warpstr:0.3.2}
MINIMAP2_BIN=${MINIMAP2_BIN:-/opt/ont/guppy/bin/minimap2}
THREADS=${THREADS:-16}
FORCE=${FORCE:-0}

ENA_FASTA=$WORK_ROOT/ena_all_reads.sample_prefixed.fasta
RAW_FASTA=$WORK_ROOT/selected_raw_fast_calls.fasta
PAF=$WORK_ROOT/selected_raw_to_ena.paf
SUMMARY=$WORK_ROOT/mastr_archive_identity_audit.tsv

for path in "$MANIFEST" "$FAST_BAM" "$SAMPLE_MAP" "$READ_IDS" "$PYTHON"; do
  if [[ ! -e "$path" ]]; then
    echo "Missing archive-audit input: $path" >&2
    exit 1
  fi
done

if [[ "$FORCE" == 1 || ! -s "$ENA_FASTA" ]]; then
  "$PYTHON" - "$MANIFEST" "$WORK_ROOT/fastq" "$ENA_FASTA" <<'PY'
import csv
import gzip
from pathlib import Path
import sys

manifest = Path(sys.argv[1])
fastq_root = Path(sys.argv[2])
output = Path(sys.argv[3])
with manifest.open(newline="") as handle, output.open("w") as destination:
    for row in csv.DictReader(handle, delimiter="\t"):
        if row.get("status") != "eligible_primary":
            continue
        sample = row["sample"]
        run = row["sra_run"]
        with gzip.open(fastq_root / f"{run}.fastq.gz", "rt") as source:
            while True:
                header = source.readline().strip()
                if not header:
                    break
                sequence = source.readline().strip()
                source.readline()
                source.readline()
                read_name = header.removeprefix("@").split()[0]
                destination.write(f">{sample}|{read_name}\n{sequence}\n")
PY
fi

samtools view -N "$READ_IDS" -b "$FAST_BAM" | samtools fasta -n - > "$RAW_FASTA"
# Request base-level alignment so PAF columns 10/11 contain exact residue
# matches/alignment length; mapping-only PAF values are chaining estimates.
docker run --rm \
  -v "$WORK_ROOT:$WORK_ROOT:ro" \
  "$MINIMAP2_IMAGE" \
  "$MINIMAP2_BIN" -t "$THREADS" -x map-ont -c --secondary=no "$ENA_FASTA" "$RAW_FASTA" \
  > "$PAF"

"$PYTHON" "$REPO_ROOT/src/algorithm/audit_mastr_archive_mapping.py" \
  --sample-map "$SAMPLE_MAP" \
  --paf "$PAF" \
  --output "$SUMMARY" \
  --min-identity 0.85 \
  --min-query-coverage 0.80 \
  --min-matches-per-sample 3 \
  --min-concordance 0.90

sha256sum "$ENA_FASTA" "$RAW_FASTA" "$PAF" "$SUMMARY" > "$WORK_ROOT/mastr_archive_identity_audit.sha256"
echo "Passed truth-free raw UUID/archive sample-identity audit: $SUMMARY" >&2
