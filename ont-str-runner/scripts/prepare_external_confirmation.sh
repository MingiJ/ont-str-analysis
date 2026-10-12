#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <sample-alias>" >&2
  echo "Example: $0 GBXM106320" >&2
  exit 2
fi

SAMPLE_ALIAS=$1
REPO_ROOT=${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}
MANIFEST=${EXTERNAL_MANIFEST:-$REPO_ROOT/ont-str-runner/configs/external_confirmation_samples.tsv}
ANALYSIS_ROOT=${EXTERNAL_ANALYSIS_ROOT:-$REPO_ROOT/ont-str-runner/work/analysis/external_confirmation}
MEMBER_INDEX=${EXTERNAL_MEMBER_INDEX:-$ANALYSIS_ROOT/${SAMPLE_ALIAS}_slow5.members.tsv}
REFERENCE=${EXTERNAL_REFERENCE:-/home/jkaranja/workdir/references/hg38.chr4.fa}
MINIMAP2_IMAGE=${MINIMAP2_IMAGE:-wkusmirek/warpstr:0.3.2}
MINIMAP2_BIN=${MINIMAP2_BIN:-/opt/ont/guppy/bin/minimap2}
THREADS=${THREADS:-10}
SAMTOOLS_THREADS=${SAMTOOLS_THREADS:-3}
LOCUS=${HTT_CONFIRMATION_LOCUS:-chr4:3074000-3076000}
MAX_HTT_READS=${MAX_HTT_READS:-128}
PYTHON=${PYTHON:-$REPO_ROOT/.venv/bin/python}
FORCE=${FORCE:-0}

if [[ ! -f "$MANIFEST" ]]; then
  echo "Missing external sample manifest: $MANIFEST" >&2
  exit 1
fi
if [[ ! -f "$MEMBER_INDEX" ]]; then
  echo "Missing remote tar member index: $MEMBER_INDEX" >&2
  echo "Build it first with src/algorithm/http_tar_members.py." >&2
  exit 1
fi
if [[ ! -f "$REFERENCE" ]]; then
  echo "Missing hg38 chr4 reference: $REFERENCE" >&2
  exit 1
fi

SLOW5_URL=$(awk -F '\t' -v alias="$SAMPLE_ALIAS" '
  NR == 1 {
    for (i = 1; i <= NF; i++) {
      if ($i == "sample_alias") alias_col = i
      if ($i == "raw_slow5_url") url_col = i
    }
    next
  }
  $alias_col == alias {gsub(/\r$/, "", $url_col); print $url_col; exit}
' "$MANIFEST")
if [[ -z "$SLOW5_URL" ]]; then
  echo "Sample alias $SAMPLE_ALIAS is absent from $MANIFEST" >&2
  exit 1
fi

read -r FASTQ_OFFSET FASTQ_SIZE < <(awk -F '\t' '
  NR > 1 && $5 ~ /\/fastq_pass\/.*\.fastq\r?$/ {print $2, $3; exit}
' "$MEMBER_INDEX")
if [[ -z "${FASTQ_OFFSET:-}" || -z "${FASTQ_SIZE:-}" ]]; then
  echo "No pass FASTQ member found in $MEMBER_INDEX" >&2
  exit 1
fi
FASTQ_END=$((FASTQ_OFFSET + FASTQ_SIZE - 1))
read -r FAIL_FASTQ_OFFSET FAIL_FASTQ_SIZE < <(awk -F '\t' '
  NR > 1 && $5 ~ /\/fastq_fail\/.*\.fastq\r?$/ {print $2, $3; exit}
' "$MEMBER_INDEX")
if [[ -z "${FAIL_FASTQ_OFFSET:-}" || -z "${FAIL_FASTQ_SIZE:-}" ]]; then
  echo "No fail FASTQ member found in $MEMBER_INDEX" >&2
  exit 1
fi
FAIL_FASTQ_END=$((FAIL_FASTQ_OFFSET + FAIL_FASTQ_SIZE - 1))

SAMPLE_DIR=$ANALYSIS_ROOT/$SAMPLE_ALIAS
UNSORTED_BAM=$SAMPLE_DIR/$SAMPLE_ALIAS.chr4.unsorted.bam
CHR4_BAM=$SAMPLE_DIR/$SAMPLE_ALIAS.chr4.bam
HTT_OVERLAP_BAM=$SAMPLE_DIR/$SAMPLE_ALIAS.htt_overlap.bam
HTT_BAM=$SAMPLE_DIR/$SAMPLE_ALIAS.htt.bam
READ_METADATA=$SAMPLE_DIR/$SAMPLE_ALIAS.htt_read_metadata.tsv
PASS_HEADERS=$SAMPLE_DIR/$SAMPLE_ALIAS.pass_fastq_headers.txt.gz
FAIL_HEADERS=$SAMPLE_DIR/$SAMPLE_ALIAS.fail_fastq_headers.txt.gz
mkdir -p "$SAMPLE_DIR"

if [[ "$FORCE" == 1 || ! -s "$CHR4_BAM" || ! -s "$CHR4_BAM.bai" || ! -s "$PASS_HEADERS" ]]; then
  rm -f "$UNSORTED_BAM" "$CHR4_BAM" "$CHR4_BAM.bai" "$PASS_HEADERS"
  echo "Streaming $SAMPLE_ALIAS pass FASTQ bytes $FASTQ_OFFSET-$FASTQ_END to minimap2." >&2
  curl -fsSL --retry 3 --retry-delay 2 --range "$FASTQ_OFFSET-$FASTQ_END" "$SLOW5_URL" |
    tee >(awk 'NR % 4 == 1 {sub(/^@/, ""); print}' | gzip -c > "$PASS_HEADERS") |
    docker run --rm -i \
      -v "$(dirname "$REFERENCE"):/references:ro" \
      "$MINIMAP2_IMAGE" \
      "$MINIMAP2_BIN" -t "$THREADS" -y -ax map-ont --secondary=no \
      "/references/$(basename "$REFERENCE")" - |
    samtools view -@ "$SAMTOOLS_THREADS" -b -F 2308 -o "$UNSORTED_BAM" -
  samtools sort -@ "$SAMTOOLS_THREADS" -o "$CHR4_BAM" "$UNSORTED_BAM"
  samtools index "$CHR4_BAM"
  rm "$UNSORTED_BAM"
else
  echo "Reusing completed alignment: $CHR4_BAM" >&2
fi

if [[ "$FORCE" == 1 || ! -s "$FAIL_HEADERS" ]]; then
  rm -f "$FAIL_HEADERS"
  echo "Streaming only fail FASTQ headers for chronological batch ranking." >&2
  curl -fsSL --retry 3 --retry-delay 2 \
    --range "$FAIL_FASTQ_OFFSET-$FAIL_FASTQ_END" "$SLOW5_URL" |
    awk 'NR % 4 == 1 {sub(/^@/, ""); print}' |
    gzip -c > "$FAIL_HEADERS"
fi

samtools view -b "$CHR4_BAM" "$LOCUS" > "$HTT_OVERLAP_BAM"
samtools index "$HTT_OVERLAP_BAM"
"$PYTHON" "$REPO_ROOT/src/algorithm/select_external_htt_reads.py" \
  --input-bam "$HTT_OVERLAP_BAM" \
  --output-bam "$HTT_BAM" \
  --metadata "$READ_METADATA" \
  --max-reads "$MAX_HTT_READS"
rm -f "$HTT_OVERLAP_BAM" "$HTT_OVERLAP_BAM.bai"

echo "HTT alignments: $(samtools view -c "$HTT_BAM")" >&2
echo "Wrote $HTT_BAM" >&2
echo "Wrote $READ_METADATA" >&2
echo "Wrote $PASS_HEADERS" >&2
echo "Wrote $FAIL_HEADERS" >&2
