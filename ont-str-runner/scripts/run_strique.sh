#!/usr/bin/env bash
set -euo pipefail

SAMPLE=${1:-}
if [[ -z "$SAMPLE" ]]; then
  echo "Usage: $0 <SAMPLE>" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_ROOT="${DATA_ROOT:-$ROOT/data}"
DATA_ROOT_REAL="$(realpath "$DATA_ROOT")"
DATA_DIR="$DATA_ROOT_REAL/$SAMPLE"
FAST5_SINGLE="$DATA_DIR/workspace/pass/0"
BAM="$DATA_DIR/$SAMPLE.bam"
if [[ ! -f "$BAM" ]]; then
  BAM="$DATA_DIR/bam/$SAMPLE.bam"
fi
SAM="$ROOT/work/strique/${SAMPLE}.sam"
FOFN="$ROOT/work/strique/${SAMPLE}.fofn"
OUT="$ROOT/work/strique/${SAMPLE}.txt"
CONFIG="$ROOT/configs/strique_config.tsv"
MODEL=${STRIQUE_MODEL:-/app/models/r9_4_450bps.model}
IMAGE=${STRIQUE_IMAGE:-giesselmann/strique:v0.4.2}
LOG_LEVEL=${STRIQUE_LOG_LEVEL:-debug}
SAMTOOLS_THREADS=${SAMTOOLS_THREADS:-}

ARCH="$(uname -m)"
DOCKER_PLATFORM=${STRIQUE_DOCKER_PLATFORM:-${DOCKER_DEFAULT_PLATFORM:-}}
if [[ -z "$DOCKER_PLATFORM" ]]; then
  case "$ARCH" in
    arm64|aarch64) DOCKER_PLATFORM="linux/amd64" ;;
  esac
fi

DOCKER_RUN=(docker run --rm)
if [[ -n "$DOCKER_PLATFORM" ]]; then
  DOCKER_RUN+=(--platform "$DOCKER_PLATFORM")
fi

if [[ ! -d "$FAST5_SINGLE" ]]; then
  echo "Missing FAST5 folder: $FAST5_SINGLE" >&2
  exit 1
fi
if [[ ! -f "$BAM" ]]; then
  echo "Missing BAM: $BAM" >&2
  exit 1
fi
if [[ ! -f "$CONFIG" ]]; then
  echo "Missing STRique config: $CONFIG" >&2
  exit 1
fi
if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found in PATH; install Docker Desktop or provide a local STRique install." >&2
  exit 1
fi

mkdir -p "$ROOT/work/strique"

if [[ -s "$SAM" && "${FORCE_SAM:-0}" != "1" && "$SAM" -nt "$BAM" ]]; then
  echo "SAM exists, skipping: $SAM"
else
  echo "Creating SAM from BAM..."
  if command -v samtools >/dev/null 2>&1; then
    SAMTOOLS_ARGS=(-h -o "$SAM")
    if [[ -n "$SAMTOOLS_THREADS" ]]; then
      SAMTOOLS_ARGS=(-@ "$SAMTOOLS_THREADS" "${SAMTOOLS_ARGS[@]}")
    fi
    samtools view "${SAMTOOLS_ARGS[@]}" "$BAM"
  else
    echo "samtools not found in PATH; install samtools or provide a SAM file." >&2
    exit 1
  fi
fi

if [[ -n "$DOCKER_PLATFORM" ]]; then
  echo "Using Docker platform: $DOCKER_PLATFORM"
fi

if [[ -s "$FOFN" && "${FORCE_REINDEX:-0}" != "1" && "$FOFN" -nt "$FAST5_SINGLE" ]]; then
  echo "FOFN exists, skipping index: $FOFN"
else
  echo "Indexing FAST5 for STRique..."
  "${DOCKER_RUN[@]}" \
    -v "$ROOT:$ROOT" \
    -v "$DATA_ROOT_REAL:$DATA_ROOT_REAL" \
    "$IMAGE" \
    bash -c "python3 /app/scripts/STRique.py index --recursive --out_prefix '$FAST5_SINGLE/' '$FAST5_SINGLE' > '$FOFN'"

  # Remove the first two lines only if STRique printed headers
  if [[ -f "$FOFN" ]]; then
    FIRST_LINE="$(head -n 1 "$FOFN" || true)"
    if [[ "$FIRST_LINE" != *".fast5"* ]]; then
      tail -n +3 "$FOFN" > "${FOFN}.tmp" && mv "${FOFN}.tmp" "$FOFN"
    fi
  fi
  if [[ ! -s "$FOFN" ]]; then
    echo "FOFN is empty after indexing: $FOFN" >&2
    exit 1
  fi
fi

if [[ -s "$OUT" && "${FORCE_COUNT:-0}" != "1" && "$OUT" -nt "$SAM" && "$OUT" -nt "$FOFN" ]]; then
  echo "Output exists, skipping count: $OUT"
else
  echo "Running STRique count..."
  "${DOCKER_RUN[@]}" \
    -v "$ROOT:$ROOT" \
    -v "$DATA_ROOT_REAL:$DATA_ROOT_REAL" \
    "$IMAGE" \
    python3 /app/scripts/STRique.py count \
    --out "$OUT" \
    --algn "$SAM" \
    --log_level "$LOG_LEVEL" \
    "$FOFN" \
    "$MODEL" \
    "$CONFIG"
fi

echo "STRique finished. Output: $OUT"
