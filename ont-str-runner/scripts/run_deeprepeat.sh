#!/usr/bin/env bash
set -euo pipefail

SAMPLE=${1:-}
REPEAT_NAME=${2:-}
COORD=${3:-}
MOTIF=${4:-}
MIN_REPEAT=${5:-3}

if [[ -z "$SAMPLE" || -z "$REPEAT_NAME" || -z "$COORD" || -z "$MOTIF" ]]; then
  echo "Usage: $0 <SAMPLE> <REPEAT_NAME> <CHR:START-END> <MOTIF> [MIN_REPEAT]" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_ROOT="${DATA_ROOT:-$ROOT/data}"
DATA_ROOT_REAL="$(realpath "$DATA_ROOT")"
DATA_DIR="$DATA_ROOT_REAL/$SAMPLE"
BAM="$DATA_DIR/$SAMPLE.bam"
if [[ ! -f "$BAM" ]]; then
  BAM="$DATA_DIR/bam/$SAMPLE.bam"
fi
F5INDEX="$DATA_DIR/${REPEAT_NAME}.f5index"
OUT_DIR="$ROOT/work/deeprepeat/$SAMPLE"
LOG="$OUT_DIR/${REPEAT_NAME}.log"
RPG=${RPG:-/app/data/wg_trf.cag.bed}
MODEL_DIR=${DEEPREPEAT_MODEL_DIR:-$ROOT/models/trainedmod_32_0.2}
MODEL_DIR=$(python3 - <<'PY' "$MODEL_DIR"
import os, sys
print(os.path.abspath(sys.argv[1]))
PY
)
EXTRA_VOLUMES=()
if [[ -d "/Volumes/Legion" ]]; then
  EXTRA_VOLUMES+=(-v "/Volumes/Legion:/Volumes/Legion")
fi
DEEPR_INDEX_FALLBACK=${DEEPR_INDEX_FALLBACK:-1}
DEEPR_FILTER_BAM=${DEEPR_FILTER_BAM:-1}

if [[ ! -f "$BAM" ]]; then
  echo "Missing BAM: $BAM" >&2
  exit 1
fi
if [[ ! -f "$F5INDEX" ]]; then
  echo "Missing f5index: $F5INDEX" >&2
  echo "Create it first (DeepRepeat requires a .f5index)." >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
if [[ ! -d "$MODEL_DIR" ]]; then
  echo "Missing DeepRepeat model dir: $MODEL_DIR" >&2
  echo "Set DEEPREPEAT_MODEL_DIR to the trainedmod_32_0.2 path." >&2
  exit 1
fi
# DeepRepeat expects an `htt` model directory for HTT runs; map to CAG_htt2_90 if needed.
if [[ ! -d "$MODEL_DIR/htt" && -d "$MODEL_DIR/CAG_htt2_90" ]]; then
  ln -s "$MODEL_DIR/CAG_htt2_90" "$MODEL_DIR/htt"
fi
if [[ ! -e "$OUT_DIR/trainedmod_32_0.2" ]]; then
  ln -s "$MODEL_DIR" "$OUT_DIR/trainedmod_32_0.2"
fi

# Validate f5index entries against current FAST5 folder; filter missing entries if needed.
FILTERED_F5INDEX="$OUT_DIR/${REPEAT_NAME}.f5index.filtered"
F5_STATS=$(python3 - <<'PY' "$F5INDEX" "$DATA_DIR" "$FILTERED_F5INDEX"
import sys
from pathlib import Path

f5index = Path(sys.argv[1])
data_dir = Path(sys.argv[2])
filtered = Path(sys.argv[3])

total = 0
missing = 0
kept = 0
extra = 0
lines = []
indexed_paths = set()

with f5index.open() as f:
    for line in f:
        total += 1
        line = line.rstrip("\n")
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        rel = parts[1]
        if (data_dir / rel).exists():
            lines.append(line)
            kept += 1
            indexed_paths.add(rel)
        else:
            missing += 1

# Count FAST5 files present but not referenced by the index.
pass0 = data_dir / "workspace" / "pass" / "0"
if pass0.exists():
    for fp in pass0.rglob("*.fast5"):
        try:
            rel = fp.relative_to(data_dir).as_posix()
        except Exception:
            continue
        if rel not in indexed_paths:
            extra += 1

if missing > 0:
    filtered.write_text("\n".join(lines) + ("\n" if lines else ""))
    out = str(filtered)
else:
    out = ""

print(f"{total} {missing} {kept} {extra} {out}")
PY
)
read -r F5_TOTAL F5_MISSING F5_KEPT F5_EXTRA F5_FILTERED_PATH <<<"$F5_STATS"

# Optional fallback: rebuild f5index from FAST5 if index appears out of sync.
if [[ ("${F5_MISSING:-0}" -gt 0 || "${F5_EXTRA:-0}" -gt 0) && "${DEEPR_INDEX_FALLBACK}" -eq 1 ]]; then
  if [[ -x "$ROOT/scripts/build_f5index_docker.sh" ]]; then
    echo "DeepRepeat f5index mismatch detected (missing=${F5_MISSING:-0}, extra=${F5_EXTRA:-0})."
    echo "Attempting to rebuild f5index via fallback generator..."
    DATA_ROOT="$DATA_ROOT_REAL" "$ROOT/scripts/build_f5index_docker.sh" "$SAMPLE" ontfast5 || true
    REBUILT_F5INDEX="$DATA_DIR/${REPEAT_NAME}.f5index.ontfast5"
    if [[ -f "$REBUILT_F5INDEX" ]]; then
      echo "Using rebuilt f5index: $REBUILT_F5INDEX"
      F5INDEX="$REBUILT_F5INDEX"
      # Recompute index stats after rebuild so messaging is accurate.
      F5_STATS=$(python3 - <<'PY' "$F5INDEX" "$DATA_DIR" "$FILTERED_F5INDEX"
import sys
from pathlib import Path

f5index = Path(sys.argv[1])
data_dir = Path(sys.argv[2])
filtered = Path(sys.argv[3])

total = 0
missing = 0
kept = 0
extra = 0
lines = []
indexed_paths = set()

with f5index.open() as f:
    for line in f:
        total += 1
        line = line.rstrip("\n")
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        rel = parts[1]
        if (data_dir / rel).exists():
            lines.append(line)
            kept += 1
            indexed_paths.add(rel)
        else:
            missing += 1

pass0 = data_dir / "workspace" / "pass" / "0"
if pass0.exists():
    for fp in pass0.rglob("*.fast5"):
        try:
            rel = fp.relative_to(data_dir).as_posix()
        except Exception:
            continue
        if rel not in indexed_paths:
            extra += 1

if missing > 0:
    filtered.write_text("\n".join(lines) + ("\n" if lines else ""))
    out = str(filtered)
else:
    out = ""

print(f"{total} {missing} {kept} {extra} {out}")
PY
)
      read -r F5_TOTAL F5_MISSING F5_KEPT F5_EXTRA F5_FILTERED_PATH <<<"$F5_STATS"
    fi
  else
    echo "Fallback indexer not found: $ROOT/scripts/build_f5index_docker.sh" >&2
  fi
fi

if [[ "${F5_MISSING:-0}" -gt 0 ]]; then
  if [[ "${F5_KEPT:-0}" -eq 0 ]]; then
    echo "DeepRepeat f5index check failed: 0 valid FAST5 entries (missing ${F5_MISSING}/${F5_TOTAL})." >&2
    exit 1
  fi
  echo "DeepRepeat f5index check: ${F5_MISSING}/${F5_TOTAL} FAST5 entries missing. Using filtered index: $F5_FILTERED_PATH"
  F5INDEX="$F5_FILTERED_PATH"
fi
if [[ "${F5_EXTRA:-0}" -gt 0 ]]; then
  echo "DeepRepeat f5index check: ${F5_EXTRA} FAST5 files present but not indexed; they will be ignored."
  echo "If you need them included, rebuild the f5index from the FAST5 folder."
fi

# Option 2: filter BAM to reads present in f5index to avoid missing read_id errors.
if [[ "${DEEPR_FILTER_BAM}" -eq 1 ]]; then
  READ_IDS_FILE="$OUT_DIR/${REPEAT_NAME}.read_ids.txt"
  python3 - <<'PY' "$F5INDEX" "$READ_IDS_FILE"
import sys

f5index = sys.argv[1]
out_path = sys.argv[2]
ids = set()
with open(f5index, "r") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if parts:
            ids.add(parts[0])
with open(out_path, "w") as out:
    for rid in sorted(ids):
        out.write(rid + "\n")
PY

  FILTERED_BAM="$OUT_DIR/${SAMPLE}.f5index.bam"
  if [[ ! -f "$FILTERED_BAM" ]]; then
    echo "Filtering BAM to reads present in f5index..."
    docker run --rm \
      -v "$ROOT:$ROOT" \
      -v "$DATA_ROOT_REAL:$DATA_ROOT_REAL" \
      "${EXTRA_VOLUMES[@]}" \
      -w "$OUT_DIR" \
      quay.io/biocontainers/samtools:1.17--h00cdaf9_0 \
      samtools view -b -N "$READ_IDS_FILE" -o "$FILTERED_BAM" "$BAM"
    docker run --rm \
      -v "$ROOT:$ROOT" \
      -v "$DATA_ROOT_REAL:$DATA_ROOT_REAL" \
      "${EXTRA_VOLUMES[@]}" \
      -w "$OUT_DIR" \
      quay.io/biocontainers/samtools:1.17--h00cdaf9_0 \
      samtools index "$FILTERED_BAM"
  fi
  BAM="$FILTERED_BAM"
fi

echo "Running DeepRepeat..."
docker run --rm \
  -v "$ROOT:$ROOT" \
  -v "$DATA_ROOT_REAL:$DATA_ROOT_REAL" \
  -v "$MODEL_DIR:$MODEL_DIR" \
  "${EXTRA_VOLUMES[@]}" \
  -w "$OUT_DIR" \
  genomicslab/deeprepeat:0.1.3 \
  DeepRepeat.py Detect \
    --gn "$REPEAT_NAME" \
    --TempRem 0 \
    --epchon 50 \
    --repeat_relax_bp 15 \
    --UniqueID "$SAMPLE" \
    --is_pcr 0 \
    --repeatName "${SAMPLE}_${REPEAT_NAME}" \
    --repeat "${COORD}:${MOTIF}:${MIN_REPEAT}" \
    --o "$OUT_DIR" \
    --bam "$BAM" \
    --f5folder "$DATA_DIR" \
    --algLen 100 \
    --f5i "$F5INDEX" \
    --rpg "$RPG" \
  > "$LOG" 2>&1

echo "DeepRepeat finished. Log: $LOG"
