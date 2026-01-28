#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_ROOT_DEFAULT="$ROOT/data"
DATA_ROOT="${DATA_ROOT:-$DATA_ROOT_DEFAULT}"

SAMPLES=(
  GM04723
  ND29970
  ND30015
  ND30016
  ND30047
  ND30422
  ND30626
  ND31551
  ND33392
  ND33947
  ND40534
)

LOG_DIR="$ROOT/work/logs"
mkdir -p "$LOG_DIR"
RUN_STRIQUE=${RUN_STRIQUE:-0}

for SAMPLE in "${SAMPLES[@]}"; do
  CONFIG="$ROOT/configs/warpstr_${SAMPLE}.yaml"
  if [[ ! -f "$CONFIG" ]]; then
    if [[ -n "${REFERENCE_FASTA:-}" ]]; then
      "$ROOT/scripts/make_warpstr_config.sh" "$SAMPLE" "$REFERENCE_FASTA" "$DATA_ROOT"
    else
      echo "Missing config for $SAMPLE. Set REFERENCE_FASTA to auto-generate it." >&2
      exit 1
    fi
  fi

  WARP_OVERVIEW="$ROOT/work/warpstr/$SAMPLE/HTT_CAG/overview.csv"
  if [[ -f "$WARP_OVERVIEW" ]]; then
    echo "=== $SAMPLE: WarpSTR (skip, overview exists) ==="
  else
    echo "=== $SAMPLE: WarpSTR ==="
    DATA_ROOT="$DATA_ROOT" bash "$ROOT/scripts/run_warpstr.sh" "$SAMPLE" \
      > "$LOG_DIR/${SAMPLE}_warpstr.log" 2>&1
  fi

  DEEP_LOG="$ROOT/work/deeprepeat/$SAMPLE/htt.log"
  if [[ -f "$DEEP_LOG" ]] && rg -q "Testing Finished!" "$DEEP_LOG" && ! rg -q "Traceback|OSError|Error|Exception" "$DEEP_LOG"; then
    echo "=== $SAMPLE: DeepRepeat (skip, successful log exists) ==="
  else
    echo "=== $SAMPLE: DeepRepeat ==="
    DATA_ROOT="$DATA_ROOT" bash "$ROOT/scripts/run_deeprepeat.sh" "$SAMPLE" htt chr4:3074876-3074933 CAG \
      > "$LOG_DIR/${SAMPLE}_deeprepeat.log" 2>&1
  fi

  if [[ "$RUN_STRIQUE" -eq 1 ]]; then
    STRIQUE_OUT="$ROOT/work/strique/${SAMPLE}.txt"
    if [[ -f "$STRIQUE_OUT" ]]; then
      echo "=== $SAMPLE: STRique (skip, output exists) ==="
    else
      echo "=== $SAMPLE: STRique ==="
      DATA_ROOT="$DATA_ROOT" bash "$ROOT/scripts/run_strique.sh" "$SAMPLE" \
        > "$LOG_DIR/${SAMPLE}_strique.log" 2>&1
    fi
  fi

done

echo "All runs complete. Logs in $LOG_DIR"
