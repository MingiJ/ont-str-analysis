#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <sample-alias>" >&2
  exit 2
fi

SAMPLE_ALIAS=$1
REPO_ROOT=${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}
MANIFEST=${EXTERNAL_MANIFEST:-$REPO_ROOT/ont-str-runner/configs/external_confirmation_samples.tsv}
ANALYSIS_ROOT=${EXTERNAL_ANALYSIS_ROOT:-$REPO_ROOT/ont-str-runner/work/analysis/external_confirmation}
CANDIDATES=${EXTERNAL_BATCH_CANDIDATES:-$ANALYSIS_ROOT/$SAMPLE_ALIAS/$SAMPLE_ALIAS.fast5_batch_candidates.tsv}
OUTPUT_DIR=${EXTERNAL_FAST5_BATCH_DIR:-$ANALYSIS_ROOT/$SAMPLE_ALIAS/fast5_batches}
MAX_DISTANCE=${MAX_DISTANCE:-0}

if [[ ! -f "$CANDIDATES" ]]; then
  echo "Missing candidate table: $CANDIDATES" >&2
  exit 1
fi

FAST5_URL=$(awk -F '\t' -v alias="$SAMPLE_ALIAS" '
  NR == 1 {
    for (i = 1; i <= NF; i++) {
      if ($i == "sample_alias") alias_col = i
      if ($i == "raw_fast5_url") url_col = i
    }
    next
  }
  $alias_col == alias {gsub(/\r$/, "", $url_col); print $url_col; exit}
' "$MANIFEST")
if [[ -z "$FAST5_URL" ]]; then
  echo "Sample alias $SAMPLE_ALIAS is absent from $MANIFEST" >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"
while IFS=$'\t' read -r batch member offset size; do
  size=${size%$'\r'}
  [[ -n "$member" ]] || continue
  filename=$(basename "$member")
  output=$OUTPUT_DIR/$filename
  partial=$output.part
  if [[ -f "$output" ]]; then
    actual=$(stat -c %s "$output")
    if [[ "$actual" -eq "$size" ]]; then
      echo "Reusing batch $batch: $output" >&2
      continue
    fi
    echo "Existing file has the wrong size: $output ($actual != $size)" >&2
    exit 1
  fi

  downloaded=0
  if [[ -f "$partial" ]]; then
    downloaded=$(stat -c %s "$partial")
  fi
  if [[ "$downloaded" -gt "$size" ]]; then
    echo "Partial file exceeds expected size: $partial" >&2
    exit 1
  fi
  if [[ "$downloaded" -lt "$size" ]]; then
    start=$((offset + downloaded))
    end=$((offset + size - 1))
    chunk=$partial.chunk
    rm -f "$chunk"
    echo "Fetching batch $batch bytes $start-$end" >&2
    curl -fsSL --retry 3 --retry-delay 2 --range "$start-$end" "$FAST5_URL" -o "$chunk"
    expected_chunk=$((size - downloaded))
    actual_chunk=$(stat -c %s "$chunk")
    if [[ "$actual_chunk" -ne "$expected_chunk" ]]; then
      echo "Downloaded chunk size mismatch for $chunk ($actual_chunk != $expected_chunk)" >&2
      exit 1
    fi
    dd if="$chunk" of="$partial" oflag=append conv=notrunc status=none
    rm "$chunk"
  fi
  actual=$(stat -c %s "$partial")
  if [[ "$actual" -ne "$size" ]]; then
    echo "Downloaded size mismatch for $partial ($actual != $size)" >&2
    exit 1
  fi
  mv "$partial" "$output"
done < <(
  awk -F '\t' -v max_distance="$MAX_DISTANCE" '
    NR > 1 {
      distance = $6 + 0
      if (distance < 0) distance = -distance
      if (distance <= max_distance) print $5 "\t" $7 "\t" $8 "\t" $9
    }
  ' "$CANDIDATES" | sort -n -u
)

echo "Selective FAST5 batches are in $OUTPUT_DIR" >&2
