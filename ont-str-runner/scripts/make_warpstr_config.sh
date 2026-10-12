#!/usr/bin/env bash
set -euo pipefail

SAMPLE=${1:-}
REF_FASTA=${2:-}
DATA_ROOT=${3:-}
OUT_DIR=${4:-}
THREADS=${WARPSTR_THREADS:-12}
VISUALIZE_ALIGNMENT=${WARPSTR_VISUALIZE_ALIGNMENT:-False}

if [[ -z "$SAMPLE" || -z "$REF_FASTA" ]]; then
  echo "Usage: $0 <SAMPLE> <REFERENCE_FASTA> [DATA_ROOT] [OUT_DIR]" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_ROOT=${DATA_ROOT:-"$ROOT/data"}
OUT_DIR=${OUT_DIR:-"$ROOT/work/warpstr/$SAMPLE"}

abspath() {
  python3 - <<'PY' "$1"
import os, sys
print(os.path.abspath(sys.argv[1]))
PY
}

REF_FASTA_ABS=$(abspath "$REF_FASTA")
DATA_ROOT_ABS=$(abspath "$DATA_ROOT")
OUT_DIR_ABS=$(abspath "$OUT_DIR")

if [[ ! -f "$REF_FASTA_ABS" ]]; then
  echo "Missing reference FASTA: $REF_FASTA_ABS" >&2
  exit 1
fi
if [[ ! -d "$DATA_ROOT_ABS" ]]; then
  echo "Missing data root: $DATA_ROOT_ABS" >&2
  exit 1
fi

CONFIG="$ROOT/configs/warpstr_${SAMPLE}.yaml"
cat > "$CONFIG" <<EOF_CFG
reference_path: ${REF_FASTA_ABS}
output: ${OUT_DIR_ABS}
threads: ${THREADS}

inputs:
  - path: ${DATA_ROOT_ABS}
    runs: ${SAMPLE}

single_read_extraction: True
guppy_annotation: True
exp_signal_generation: True
tr_region_extraction: True
tr_region_calling: True
genotyping: True

force_overwrite: True

tr_calling_config:
    visualize_alignment: ${VISUALIZE_ALIGNMENT}

guppy_config:
    path: /opt/ont/guppy/bin/guppy_basecaller
    flowcell: FLO-MIN106
    kit: SQK-LSK109

loci:
  - name: HTT_CAG
    coord: chr4:3074876-3074933
    motif: CAG
EOF_CFG

echo "Wrote $CONFIG"
