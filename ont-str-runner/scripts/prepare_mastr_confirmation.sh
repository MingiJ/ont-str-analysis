#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}
MANIFEST=${MASTR_ACQUISITION_MANIFEST:-$REPO_ROOT/ont-str-runner/configs/mastr_confirmation_acquisition.tsv}
WORK_ROOT=${MASTR_WORK_ROOT:-$REPO_ROOT/ont-str-runner/work/mastr}
REFERENCE=${MASTR_REFERENCE:-/home/jkaranja/workdir/references/hg38.chr4.fa}
MINIMAP2_IMAGE=${MINIMAP2_IMAGE:-wkusmirek/warpstr:0.3.2}
MINIMAP2_BIN=${MINIMAP2_BIN:-/opt/ont/guppy/bin/minimap2}
PYTHON=${PYTHON:-$REPO_ROOT/.venv/bin/python}
THREADS=${THREADS:-16}
SAMTOOLS_THREADS=${SAMTOOLS_THREADS:-4}
MAX_HTT_READS=${MAX_HTT_READS:-128}
MIN_HTT_READS=${MIN_HTT_READS:-6}
FORCE=${FORCE:-0}

FASTQ_ROOT=$WORK_ROOT/fastq
ALIGNMENT_ROOT=$WORK_ROOT/alignment
RAW_ROOT=$WORK_ROOT/raw
SAMPLE_MAP=$WORK_ROOT/ena_selected_read_samples.tsv
READ_IDS=$WORK_ROOT/ena_selected_read_ids.txt

if [[ ! -f "$MANIFEST" ]]; then
  echo "Missing MASTR acquisition manifest: $MANIFEST" >&2
  exit 1
fi
if [[ ! -f "$REFERENCE" ]]; then
  echo "Missing hg38 chr4 reference: $REFERENCE" >&2
  exit 1
fi
if [[ ! -x "$PYTHON" ]]; then
  echo "Missing project Python: $PYTHON" >&2
  exit 1
fi
command -v docker >/dev/null || { echo "docker is required for frozen minimap2" >&2; exit 1; }
command -v samtools >/dev/null || { echo "samtools is required" >&2; exit 1; }

mkdir -p "$FASTQ_ROOT" "$ALIGNMENT_ROOT" "$RAW_ROOT"

verify_file() {
  local path=$1
  local expected_size=$2
  local expected_md5=$3
  [[ -s "$path" ]] || return 1
  [[ $(stat -c '%s' "$path") == "$expected_size" ]] || return 1
  [[ $(md5sum "$path" | awk '{print $1}') == "$expected_md5" ]]
}

download_verified() {
  local url=$1
  local output=$2
  local expected_size=$3
  local expected_md5=$4
  if [[ "$FORCE" != 1 ]] && verify_file "$output" "$expected_size" "$expected_md5"; then
    echo "Verified cached file: $output" >&2
    return
  fi
  local partial=$output.partial
  if [[ "$FORCE" == 1 ]]; then
    rm -f "$partial"
  fi
  curl -fL --retry 5 --retry-delay 3 --continue-at - --output "$partial" "$url"
  if ! verify_file "$partial" "$expected_size" "$expected_md5"; then
    echo "Checksum or size mismatch for $url" >&2
    rm -f "$partial"
    exit 1
  fi
  mv "$partial" "$output"
  echo "Downloaded and verified: $output" >&2
}

printf 'sample\tread_id\n' > "$SAMPLE_MAP.tmp"

while IFS=$'\t' read -r sample study bioproject biosample geo_sample experiment run barcode \
  fastq_url fastq_size fastq_md5 pod5_url pod5_size pod5_md5 dorado_version dorado_model status; do
  [[ "$sample" == sample ]] && continue
  [[ "$status" == eligible_primary ]] || continue

  fastq=$FASTQ_ROOT/$run.fastq.gz
  sample_dir=$ALIGNMENT_ROOT/$sample
  aligned_bam=$sample_dir/$sample.chr4.bam
  selected_bam=$sample_dir/$sample.htt.selected.bam
  metadata=$sample_dir/$sample.htt.selected.tsv
  mkdir -p "$sample_dir"

  download_verified "$fastq_url" "$fastq" "$fastq_size" "$fastq_md5"
  if [[ "$FORCE" == 1 || ! -s "$aligned_bam" || ! -s "$aligned_bam.bai" ]]; then
    echo "Aligning truth-free public FASTQ for $sample ($run)." >&2
    gzip -dc "$fastq" |
      docker run --rm -i \
        -v "$(dirname "$REFERENCE"):/references:ro" \
        "$MINIMAP2_IMAGE" \
        "$MINIMAP2_BIN" -t "$THREADS" -ax map-ont --secondary=no \
        "/references/$(basename "$REFERENCE")" - |
      samtools view -@ "$SAMTOOLS_THREADS" -b -F 2308 - |
      samtools sort -@ "$SAMTOOLS_THREADS" -o "$aligned_bam" -
    samtools index "$aligned_bam"
  fi

  "$PYTHON" "$REPO_ROOT/src/algorithm/select_external_htt_reads.py" \
    --input-bam "$aligned_bam" \
    --output-bam "$selected_bam" \
    --metadata "$metadata" \
    --max-reads "$MAX_HTT_READS" \
    --selection-seed "mastr-independent-ena-audit-v1:$sample"

  selected_count=$(awk 'NR > 1 {count++} END {print count + 0}' "$metadata")
  if (( selected_count < MIN_HTT_READS )); then
    echo "$sample has $selected_count selected reads; frozen minimum is $MIN_HTT_READS" >&2
    exit 1
  fi
  awk -F '\t' -v sample="$sample" 'NR > 1 {print sample "\t" $1}' "$metadata" >> "$SAMPLE_MAP.tmp"
  echo "$sample selected full-flank reads: $selected_count" >&2
done < "$MANIFEST"

mv "$SAMPLE_MAP.tmp" "$SAMPLE_MAP"
awk -F '\t' 'NR > 1 {print $2}' "$SAMPLE_MAP" | LC_ALL=C sort -u > "$READ_IDS"

read -r pod5_url pod5_size pod5_md5 < <(awk -F '\t' '
  NR == 1 {
    for (i = 1; i <= NF; i++) {
      if ($i == "raw_pod5_url") url_col = i
      if ($i == "raw_pod5_size_bytes") size_col = i
      if ($i == "raw_pod5_md5") md5_col = i
    }
    next
  }
  $17 == "eligible_primary" {print $url_col, $size_col, $md5_col; exit}
' "$MANIFEST")
POD5=$RAW_ROOT/FAW16852.pod5
download_verified "$pod5_url" "$POD5" "$pod5_size" "$pod5_md5"

echo "Selected read IDs: $(wc -l < "$READ_IDS" | tr -d ' ')" >&2
echo "Wrote ENA audit sample map: $SAMPLE_MAP" >&2
echo "Wrote ENA audit read-ID selection: $READ_IDS" >&2
echo "ENA/SRA headers are archive-local ordinals; raw POD5 UUID selection is a separate stage." >&2
echo "Verified raw POD5: $POD5" >&2
