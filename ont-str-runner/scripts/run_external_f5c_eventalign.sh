#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <sample-alias>" >&2
  exit 2
fi

SAMPLE_ALIAS=$1
REPO_ROOT=${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}
ANALYSIS_ROOT=${EXTERNAL_ANALYSIS_ROOT:-$REPO_ROOT/ont-str-runner/work/analysis/external_confirmation}
SAMPLE_DIR=$ANALYSIS_ROOT/$SAMPLE_ALIAS
RAW_DIR=${EXTERNAL_SELECTED_RAW_DIR:-$SAMPLE_DIR/selected_raw}
HTT_BAM=${EXTERNAL_HTT_BAM:-$SAMPLE_DIR/$SAMPLE_ALIAS.htt.bam}
REFERENCE=${EXTERNAL_REFERENCE:-/home/jkaranja/workdir/references/hg38.chr4.fa}
F5C=${F5C_BIN:-/home/jkaranja/workdir/tools/f5c-v1.6/f5c_x86_64_linux}
VBZ_PLUGIN_DIR=${HDF5_PLUGIN_PATH:-/home/jkaranja/workdir/tools/vbz-1.0.1/ont-vbz-hdf-plugin-1.0.1-Linux/usr/local/hdf5/lib/plugin}
THREADS=${THREADS:-8}
FORCE=${FORCE:-0}
READS_FASTQ=$SAMPLE_DIR/$SAMPLE_ALIAS.htt.fastq
EVENTALIGN=$SAMPLE_DIR/$SAMPLE_ALIAS.eventalign.tsv
EVENTALIGN_SUMMARY=$SAMPLE_DIR/$SAMPLE_ALIAS.eventalign.summary.tsv

for path in "$HTT_BAM" "$HTT_BAM.bai" "$REFERENCE" "$F5C" "$VBZ_PLUGIN_DIR"; do
  if [[ ! -e "$path" ]]; then
    echo "Missing required input: $path" >&2
    exit 1
  fi
done
if ! find "$RAW_DIR" -maxdepth 1 -type f -name '*.fast5' -print -quit | grep -q .; then
  echo "No target-only FAST5 found in $RAW_DIR" >&2
  exit 1
fi

if [[ "$FORCE" == 1 || ! -s "$READS_FASTQ" ]]; then
  samtools fastq -n "$HTT_BAM" > "$READS_FASTQ"
fi

if [[ "$FORCE" == 1 || ! -s "$READS_FASTQ.index.readdb" ]]; then
  HDF5_PLUGIN_PATH=$VBZ_PLUGIN_DIR "$F5C" index -t "$THREADS" -d "$RAW_DIR" "$READS_FASTQ"
fi

if [[ "$FORCE" == 1 || ! -s "$EVENTALIGN" ]]; then
  HDF5_PLUGIN_PATH=$VBZ_PLUGIN_DIR "$F5C" eventalign \
    -t "$THREADS" \
    -r "$READS_FASTQ" \
    -b "$HTT_BAM" \
    -g "$REFERENCE" \
    --print-read-names \
    --signal-index \
    --summary "$EVENTALIGN_SUMMARY" \
    > "$EVENTALIGN"
fi

echo "Wrote $EVENTALIGN" >&2
echo "Wrote $EVENTALIGN_SUMMARY" >&2
