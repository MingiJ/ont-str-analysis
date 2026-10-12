#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_ROOT_DEFAULT="$ROOT/data"
DATA_ROOT="${DATA_ROOT:-$DATA_ROOT_DEFAULT}"
DATA_ROOT_REAL="$(realpath "$DATA_ROOT")"
LOG_DIR="$ROOT/work/logs"
BACKUP_ROOT="$ROOT/work/benchmark_backups"
RUN_ID="${RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
BACKUP_DIR="$BACKUP_ROOT/$RUN_ID"
RUN_STRIQUE="${RUN_STRIQUE:-1}"
PREPARE_ARCHIVES="${PREPARE_ARCHIVES:-1}"
FRESH_OUTPUTS="${FRESH_OUTPUTS:-1}"
ONLY_PREFLIGHT="${ONLY_PREFLIGHT:-0}"
TRUTH_SAMPLES=(
  GM04723
  ND30015
  ND30016
  ND30047
  ND30422
  ND30626
  ND31551
  ND33392
  ND33947
)
if [[ -n "${SAMPLES:-}" ]]; then
  # shellcheck disable=SC2206
  TRUTH_SAMPLES=(${SAMPLES})
fi

mkdir -p "$LOG_DIR" "$BACKUP_ROOT"

log() {
  printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*"
}

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

have_command() {
  command -v "$1" >/dev/null 2>&1
}

sample_tarball() {
  local sample="$1"
  find "$DATA_ROOT_REAL/$sample" -maxdepth 1 -type f \( -name "${sample}.tar.gz" -o -name "${sample}.tar.gz.*" -o -name "${sample}.tgz" -o -name "${sample}.tar" \) 2>/dev/null | sort | head -n 1
}

sample_has_inputs() {
  local sample="$1"
  local dir="$DATA_ROOT_REAL/$sample"
  [[ -d "$dir/workspace/pass/0" ]] &&
    find "$dir/workspace/pass/0" -name '*.fast5' -print -quit | grep -q . &&
    { [[ -f "$dir/$sample.bam" ]] || [[ -f "$dir/bam/$sample.bam" ]]; } &&
    { [[ -f "$dir/$sample.bam.bai" ]] || [[ -f "$dir/bam/$sample.bam.bai" ]]; } &&
    [[ -f "$dir/htt.f5index" ]]
}

prepare_sample() {
  local sample="$1"
  local dir="$DATA_ROOT_REAL/$sample"
  mkdir -p "$dir"
  if sample_has_inputs "$sample"; then
    log "$sample inputs already staged"
    return
  fi

  local tarball
  tarball="$(sample_tarball "$sample" || true)"
  if [[ -z "$tarball" ]]; then
    log "$sample missing local archive; skipping extraction"
    return
  fi

  log "Extracting $sample archive: $tarball"
  case "$tarball" in
    *.tar.gz|*.tar.gz.*|*.tgz) tar -xzf "$tarball" -C "$DATA_ROOT_REAL" ;;
    *.tar) tar -xf "$tarball" -C "$DATA_ROOT_REAL" ;;
    *) fail "Unsupported archive type: $tarball" ;;
  esac
}

preflight_sample() {
  local sample="$1"
  if sample_has_inputs "$sample"; then
    log "$sample input check: ok"
  else
    log "$sample input check: missing FAST5/BAM/BAI/htt.f5index"
    return 1
  fi
}

preflight_environment() {
  [[ -n "${REFERENCE_FASTA:-}" ]] || fail "Set REFERENCE_FASTA=/abs/path/to/reference FASTA"
  [[ -f "$REFERENCE_FASTA" ]] || fail "REFERENCE_FASTA does not exist: $REFERENCE_FASTA"
  [[ -n "${DEEPREPEAT_MODEL_DIR:-}" ]] || fail "Set DEEPREPEAT_MODEL_DIR=/abs/path/to/trainedmod_32_0.2"
  [[ -d "$DEEPREPEAT_MODEL_DIR" ]] || fail "DEEPREPEAT_MODEL_DIR does not exist: $DEEPREPEAT_MODEL_DIR"
  have_command docker || fail "docker is required for WarpSTR, DeepRepeat, and STRique"
  if [[ "$RUN_STRIQUE" -eq 1 ]]; then
    have_command samtools || fail "samtools is required on the host for STRique"
  fi
  have_command python3 || fail "python3 is required"
}

backup_path() {
  local path="$1"
  if [[ -e "$path" ]]; then
    local parent
    parent="$(dirname "$path")"
    if [[ ! -w "$parent" || ! -w "$path" ]]; then
      log "Fixing Docker-owned permissions for $parent"
      docker run --rm \
        -v "$ROOT/work:$ROOT/work" \
        wkusmirek/warpstr:0.3.2 \
        chown -R "$(id -u):$(id -g)" "$parent" "$path"
    fi
    mkdir -p "$BACKUP_DIR/$(dirname "${path#$ROOT/work/}")"
    mv "$path" "$BACKUP_DIR/${path#$ROOT/work/}"
    log "Backed up $path"
  fi
}

backup_sample_outputs() {
  local sample="$1"
  [[ "$FRESH_OUTPUTS" -eq 1 ]] || return 0
  mkdir -p "$BACKUP_DIR"
  backup_path "$ROOT/work/warpstr/$sample"
  backup_path "$ROOT/work/deeprepeat/$sample"
  backup_path "$ROOT/work/strique/${sample}.txt"
  backup_path "$ROOT/work/strique/${sample}.sam"
  backup_path "$ROOT/work/strique/${sample}.fofn"
}

ensure_config() {
  local sample="$1"
  "$ROOT/scripts/make_warpstr_config.sh" "$sample" "$REFERENCE_FASTA" "$DATA_ROOT_REAL"
}

run_warpstr_strict() {
  local sample="$1"
  log "$sample WarpSTR: running"
  DATA_ROOT="$DATA_ROOT_REAL" bash "$ROOT/scripts/run_warpstr.sh" "$sample" > "$LOG_DIR/${sample}_warpstr_${RUN_ID}.log" 2>&1
  local allele_csv="$ROOT/work/warpstr/$sample/HTT_CAG/predictions/alleles.csv"
  [[ -s "$allele_csv" ]] || fail "$sample WarpSTR did not produce $allele_csv"
  log "$sample WarpSTR: complete"
}

run_deeprepeat_strict() {
  local sample="$1"
  log "$sample DeepRepeat: running"
  DATA_ROOT="$DATA_ROOT_REAL" bash "$ROOT/scripts/run_deeprepeat.sh" "$sample" htt chr4:3074876-3074933 CAG > "$LOG_DIR/${sample}_deeprepeat_${RUN_ID}.log" 2>&1
  local log_path="$ROOT/work/deeprepeat/$sample/htt.log"
  [[ -s "$log_path" ]] || fail "$sample DeepRepeat did not produce $log_path"
  grep -q "Testing Finished!" "$log_path" || fail "$sample DeepRepeat missing Testing Finished! marker"
  if grep -Eq "Traceback|OSError|Error|Exception" "$log_path"; then
    fail "$sample DeepRepeat log contains fatal markers"
  fi
  log "$sample DeepRepeat: complete"
}

run_strique_strict() {
  local sample="$1"
  [[ "$RUN_STRIQUE" -eq 1 ]] || return 0
  log "$sample STRique: running"
  DATA_ROOT="$DATA_ROOT_REAL" bash "$ROOT/scripts/run_strique.sh" "$sample" > "$LOG_DIR/${sample}_strique_${RUN_ID}.log" 2>&1
  local out="$ROOT/work/strique/${sample}.txt"
  [[ -s "$out" ]] || fail "$sample STRique did not produce $out"
  python3 - "$out" <<'PY'
import csv
import sys
path = sys.argv[1]
count = 0
with open(path, newline="") as handle:
    reader = csv.DictReader(handle, delimiter="\t")
    for row in reader:
        try:
            int(float(row.get("count", "")))
        except Exception:
            continue
        count += 1
if count == 0:
    raise SystemExit("no parseable STRique count rows")
PY
  log "$sample STRique: complete"
}

main() {
  log "Strict HTT benchmark run id: $RUN_ID"
  preflight_environment

  local missing=0
  for sample in "${TRUTH_SAMPLES[@]}"; do
    if [[ "$PREPARE_ARCHIVES" -eq 1 ]]; then
      prepare_sample "$sample"
    fi
    if ! preflight_sample "$sample"; then
      missing=1
    fi
  done
  [[ "$missing" -eq 0 ]] || fail "One or more truth samples are missing inputs. Stage archives/data before running."

  if [[ "$ONLY_PREFLIGHT" -eq 1 ]]; then
    log "Preflight complete; ONLY_PREFLIGHT=1 so no tool runs were started."
    return
  fi

  for sample in "${TRUTH_SAMPLES[@]}"; do
    backup_sample_outputs "$sample"
    ensure_config "$sample"
    run_warpstr_strict "$sample"
    run_deeprepeat_strict "$sample"
    run_strique_strict "$sample"
  done

  python3 "$ROOT/scripts/compare_ground_truth.py" --samples "${TRUTH_SAMPLES[@]}"
  log "Strict benchmark complete. Comparison and report are in $ROOT/work/analysis"
}

main "$@"
