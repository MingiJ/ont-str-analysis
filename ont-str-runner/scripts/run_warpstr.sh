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
FAST5_SINGLE="$DATA_ROOT_REAL/$SAMPLE/workspace/pass/0"
FAST5_MULTI="$DATA_ROOT_REAL/$SAMPLE/workspace/pass_multi/0"
CONFIG="$ROOT/configs/warpstr_${SAMPLE}.yaml"
if [[ ! -f "$CONFIG" ]]; then
  if [[ -n "${REFERENCE_FASTA:-}" ]]; then
    "$ROOT/scripts/make_warpstr_config.sh" "$SAMPLE" "$REFERENCE_FASTA" "$DATA_ROOT_REAL"
  else
    echo "Missing config: $CONFIG" >&2
    echo "Set REFERENCE_FASTA to generate it automatically." >&2
    exit 1
  fi
fi
REF_PATH="$(rg '^reference_path:' "$CONFIG" | head -1 | sed 's/reference_path:[[:space:]]*//')"
REF_DIR=""
if [[ -n "$REF_PATH" ]]; then
  REF_DIR="$(dirname "$REF_PATH")"
fi
EXTRA_VOLUMES=()
if [[ -d "/Volumes/Legion" ]]; then
  EXTRA_VOLUMES+=(-v "/Volumes/Legion:/Volumes/Legion")
fi

if [[ ! -d "$FAST5_SINGLE" ]]; then
  echo "Missing FAST5 folder: $FAST5_SINGLE" >&2
  exit 1
fi
if [[ -z "$REF_PATH" ]]; then
  echo "Config missing reference_path: $CONFIG" >&2
  exit 1
fi

mkdir -p "$FAST5_MULTI"
if ! find "$FAST5_MULTI" -name '*.fast5' -print -quit | grep -q .; then
  echo "Converting single FAST5 to multi FAST5..."
  docker run --rm \
    -v "$ROOT:$ROOT" \
    -v "$DATA_ROOT_REAL:$DATA_ROOT_REAL" \
    "${EXTRA_VOLUMES[@]}" \
    ttubb/ont-fast5-api:latest \
    single_to_multi_fast5 -i "$FAST5_SINGLE" -s "$FAST5_MULTI"
else
  echo "Found existing multi FAST5 in $FAST5_MULTI"
fi

echo "Running WarpSTR..."
docker run --rm \
  -v "$ROOT:$ROOT" \
  -v "$DATA_ROOT_REAL:$DATA_ROOT_REAL" \
  ${REF_DIR:+-v "$REF_DIR:$REF_DIR"} \
  "${EXTRA_VOLUMES[@]}" \
  wkusmirek/warpstr:0.3.2 \
  python3.7 /opt/warpstr/WarpSTR.py "$CONFIG"
