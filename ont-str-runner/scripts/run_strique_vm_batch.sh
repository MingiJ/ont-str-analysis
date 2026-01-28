#!/usr/bin/env bash
set -euo pipefail

# Batch STRique runner for VM (native install, no Docker).
# Downloads samples in order, runs STRique, stores results on /mnt,
# and deletes sample data to save disk.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="$ROOT/work/strique"
CONFIG="$ROOT/configs/strique_config.tsv"

DATA_ROOT="${DATA_ROOT:-/mnt/ont-str-data}"
RESULT_ROOT="${RESULT_ROOT:-/mnt/ont-str-results/strique}"

CONDA_BIN="${CONDA_BIN:-/home/jeff/miniconda3/bin/conda}"
CONDA_ENV="${CONDA_ENV:-strique36}"
STRIQUE_PY="${STRIQUE_PY:-/home/jeff/src/STRique/scripts/STRique.py}"
STRIQUE_MODEL="${STRIQUE_MODEL:-/home/jeff/src/STRique/models/r9_4_450bps.model}"
STRIQUE_THREADS="${STRIQUE_THREADS:-4}"
SAMTOOLS_THREADS="${SAMTOOLS_THREADS:-4}"
START_AT="${START_AT:-}"

SAMPLES=(
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
  GM04723
  NA12878
)

URLS=(
  https://sra-pub-src-2.s3.amazonaws.com/SRR13068466/ND29970.tar.gz.1
  https://sra-pub-src-2.s3.amazonaws.com/SRR13068465/ND30015.tar.gz.1
  https://sra-pub-src-2.s3.amazonaws.com/SRR13068464/ND30016.tar.gz.1
  https://sra-pub-src-2.s3.amazonaws.com/SRR13068463/ND30047.tar.gz.1
  https://sra-pub-src-2.s3.amazonaws.com/SRR13068462/ND30422.tar.gz.1
  https://sra-pub-src-2.s3.amazonaws.com/SRR13068461/ND30626.tar.gz.1
  https://sra-pub-src-2.s3.amazonaws.com/SRR13068460/ND31551.tar.gz.1
  https://sra-pub-src-2.s3.amazonaws.com/SRR13068459/ND33392.tar.gz.1
  https://sra-pub-src-2.s3.amazonaws.com/SRR13068468/ND33947.tar.gz.1
  https://sra-pub-src-2.s3.amazonaws.com/SRR13068467/ND40534.tar.gz.1
  https://sra-pub-src-2.s3.amazonaws.com/SRR13068470/GM04723.tar.gz.1
  https://sra-pub-src-2.s3.amazonaws.com/SRR13068469/NA12878.tar.gz.1
)

if [[ ${#SAMPLES[@]} -ne ${#URLS[@]} ]]; then
  echo "Sample/URL list length mismatch." >&2
  exit 1
fi

if [[ ! -f "$CONFIG" ]]; then
  echo "Missing STRique config: $CONFIG" >&2
  exit 1
fi

EXPECTED_HEADER=$'chr\tbegin\tend\tname\trepeat\tprefix\tsuffix'
HEADER="$(head -n 1 "$CONFIG" || true)"
if [[ "$HEADER" != "$EXPECTED_HEADER" ]]; then
  echo "STRique config header must be: $EXPECTED_HEADER" >&2
  exit 1
fi

for cmd in wget tar samtools; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    exit 1
  fi
done

if [[ ! -x "$CONDA_BIN" ]]; then
  echo "conda not found at $CONDA_BIN" >&2
  exit 1
fi
if [[ ! -f "$STRIQUE_PY" ]]; then
  echo "STRique.py not found at $STRIQUE_PY" >&2
  exit 1
fi
if [[ ! -f "$STRIQUE_MODEL" ]]; then
  echo "STRique model not found at $STRIQUE_MODEL" >&2
  exit 1
fi

CONDA_RUN=("$CONDA_BIN" "run" "-n" "$CONDA_ENV")

mkdir -p "$DATA_ROOT" "$RESULT_ROOT" "$WORK_DIR"
DONE_FILE="$RESULT_ROOT/.done"
touch "$DONE_FILE"

is_done() {
  local sample="$1"
  if [[ -s "$RESULT_ROOT/${sample}.txt" ]]; then
    return 0
  fi
  grep -qx "$sample" "$DONE_FILE" && return 0
  return 1
}

mark_done() {
  local sample="$1"
  if ! grep -qx "$sample" "$DONE_FILE"; then
    echo "$sample" >> "$DONE_FILE"
  fi
}

log() {
  echo "[$(date '+%F %T')] $*"
}

prepare_layout() {
  local sample="$1"
  local data_dir="$DATA_ROOT/$sample"

  # Handle nested archives: data/<SAMPLE>/<SAMPLE>/workspace/...
  if [[ -d "$data_dir/$sample/workspace" && ! -d "$data_dir/workspace" ]]; then
    ln -s "$data_dir/$sample/workspace" "$data_dir/workspace"
  fi
  if [[ -f "$data_dir/$sample/$sample.bam" && ! -f "$data_dir/$sample.bam" ]]; then
    ln -s "$data_dir/$sample/$sample.bam" "$data_dir/$sample.bam"
  fi
  if [[ -f "$data_dir/$sample/$sample.bam.bai" && ! -f "$data_dir/$sample.bam.bai" ]]; then
    ln -s "$data_dir/$sample/$sample.bam.bai" "$data_dir/$sample.bam.bai"
  fi

  local fast5_dir="$data_dir/workspace/pass/0"
  if [[ ! -d "$fast5_dir" || -z "$(ls -A "$fast5_dir" 2>/dev/null)" ]]; then
    if [[ -d "$data_dir/$sample/workspace/pass/0" ]]; then
      rm -rf "$data_dir/workspace"
      ln -s "$data_dir/$sample/workspace" "$data_dir/workspace"
      fast5_dir="$data_dir/workspace/pass/0"
    fi
  fi

  echo "$fast5_dir"
}

for i in "${!SAMPLES[@]}"; do
  sample="${SAMPLES[$i]}"
  url="${URLS[$i]}"

  if [[ -n "$START_AT" ]]; then
    if [[ "$sample" != "$START_AT" ]]; then
      continue
    fi
    START_AT=""
  fi

  if is_done "$sample"; then
    log "Skip $sample (result exists)."
    continue
  fi

  if [[ -s "$WORK_DIR/${sample}.txt" && ! -s "$RESULT_ROOT/${sample}.txt" ]]; then
    log "Found existing result for $sample in work dir. Moving to results."
    mkdir -p "$RESULT_ROOT"
    mv "$WORK_DIR/${sample}.txt" "$RESULT_ROOT/${sample}.txt"
    if [[ -s "$WORK_DIR/${sample}.log" ]]; then
      mv "$WORK_DIR/${sample}.log" "$RESULT_ROOT/${sample}.log"
    fi
    ln -sf "$RESULT_ROOT/${sample}.txt" "$WORK_DIR/${sample}.txt"
    mark_done "$sample"
    continue
  fi

  data_dir="$DATA_ROOT/$sample"
  mkdir -p "$data_dir"

  tarball="$data_dir/${sample}.tar.gz.1"
  if [[ ! -s "$tarball" ]]; then
    log "Downloading $sample..."
    wget -c -O "$tarball" "$url"
  fi

  log "Extracting $sample..."
  tar -xzf "$tarball" -C "$data_dir"
  rm -f "$tarball"

  fast5_dir="$(prepare_layout "$sample")"
  if [[ ! -d "$fast5_dir" ]]; then
    echo "Missing FAST5 dir for $sample: $fast5_dir" >&2
    exit 1
  fi

  bam="$data_dir/${sample}.bam"
  if [[ ! -f "$bam" ]]; then
    bam="$data_dir/bam/${sample}.bam"
  fi
  if [[ ! -f "$bam" ]]; then
    echo "Missing BAM for $sample" >&2
    exit 1
  fi

  sam="$WORK_DIR/${sample}.sam"
  if [[ ! -s "$sam" || "$bam" -nt "$sam" ]]; then
    log "Creating SAM for $sample..."
    samtools view -@ "$SAMTOOLS_THREADS" -h -o "$sam" "$bam"
  fi

  fofn="$WORK_DIR/${sample}.fofn"
  log "Indexing FAST5 for $sample..."
  "${CONDA_RUN[@]}" env HDF5_USE_FILE_LOCKING=FALSE PYTHONUNBUFFERED=1 \
    python "$STRIQUE_PY" index --recursive --out_prefix "$fast5_dir/" "$fast5_dir" > "$fofn"

  if [[ -f "$fofn" ]]; then
    first_line="$(head -n 1 "$fofn" || true)"
    if [[ "$first_line" != *".fast5"* ]]; then
      tail -n +3 "$fofn" > "${fofn}.tmp" && mv "${fofn}.tmp" "$fofn"
    fi
  fi
  if [[ ! -s "$fofn" ]]; then
    echo "FOFN is empty for $sample: $fofn" >&2
    exit 1
  fi

  out="$WORK_DIR/${sample}.txt"
  log "Running STRique count for $sample..."
  log_file="$WORK_DIR/${sample}.log"
  "${CONDA_RUN[@]}" env HDF5_USE_FILE_LOCKING=FALSE PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 \
    python "$STRIQUE_PY" count \
    --out "$out" \
    --algn "$sam" \
    --log_level info \
    --t "$STRIQUE_THREADS" \
    "$fofn" \
    "$STRIQUE_MODEL" \
    "$CONFIG" > "$log_file" 2>&1

  if [[ ! -s "$out" ]]; then
    echo "No STRique output for $sample" >&2
    exit 1
  fi

  log "Storing results for $sample..."
  mkdir -p "$RESULT_ROOT"
  mv "$out" "$RESULT_ROOT/${sample}.txt"
  ln -sf "$RESULT_ROOT/${sample}.txt" "$out"
  if [[ -s "$log_file" ]]; then
    mv "$log_file" "$RESULT_ROOT/${sample}.log"
  fi
  mark_done "$sample"

  log "Cleaning up $sample..."
  rm -f "$sam" "$fofn"
  rm -rf "$data_dir"
done

log "All samples complete."
