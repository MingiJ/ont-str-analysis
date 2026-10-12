#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}
WORK_ROOT=${MASTR_WORK_ROOT:-$REPO_ROOT/ont-str-runner/work/mastr}
DORADO=${DORADO:-$REPO_ROOT/tools/dorado-0.7.3-linux-x64/bin/dorado}
MODEL_NAME=${DORADO_MODEL:-dna_r9.4.1_e8_sup@v3.6}
MODEL_ROOT=${DORADO_MODEL_ROOT:-$REPO_ROOT/tools/dorado-models}
MODEL_PATH=$MODEL_ROOT/$MODEL_NAME
REFERENCE=${MASTR_REFERENCE:-/home/jkaranja/workdir/references/hg38.chr4.fa}
POD5=${MASTR_POD5:-$WORK_ROOT/raw/FAW16852.pod5}
READ_IDS=${MASTR_READ_IDS:-$WORK_ROOT/selected_read_ids.txt}
SAMPLE_MAP=${MASTR_SAMPLE_MAP:-$WORK_ROOT/selected_read_samples.tsv}
IDENTITY_AUDIT=${MASTR_IDENTITY_AUDIT:-$WORK_ROOT/mastr_archive_identity_audit.tsv}
PYTHON=${PYTHON:-$REPO_ROOT/.venv/bin/python}
SAMTOOLS_THREADS=${SAMTOOLS_THREADS:-4}
FORCE=${FORCE:-0}

UNSORTED_BAM=$WORK_ROOT/mastr.dorado-0.7.3.r9-sup-v3.6.unsorted.bam
BAM=$WORK_ROOT/mastr.dorado-0.7.3.r9-sup-v3.6.bam
BASECALL_LOG=$WORK_ROOT/mastr.dorado-0.7.3.r9-sup-v3.6.log
BOUNDS=$WORK_ROOT/mastr_dorado_move_signal_bounds.tsv
ARCHIVE=$WORK_ROOT/mastr_signal_repeat_windows.npz
INDEX=$WORK_ROOT/mastr_signal_repeat_windows.index.tsv
PREDICTIONS=$WORK_ROOT/mastr_sealed_predictions.tsv

for path in "$DORADO" "$REFERENCE" "$POD5" "$READ_IDS" "$SAMPLE_MAP" "$IDENTITY_AUDIT" "$PYTHON"; do
  if [[ ! -e "$path" ]]; then
    echo "Missing required input: $path" >&2
    exit 1
  fi
done
if awk -F '\t' 'NR > 1 {n++; if ($7 != "pass") bad=1} END {exit !(n == 4 && !bad)}' "$IDENTITY_AUDIT"; then
  :
else
  echo "Archive sample-identity audit did not pass for every sample: $IDENTITY_AUDIT" >&2
  exit 1
fi

mkdir -p "$WORK_ROOT" "$MODEL_ROOT"
if [[ ! -d "$MODEL_PATH" ]]; then
  "$DORADO" download --model "$MODEL_NAME" --directory "$MODEL_ROOT"
fi

if [[ "$FORCE" == 1 || ! -s "$BAM" || ! -s "$BAM.bai" ]]; then
  echo "Running frozen Dorado 0.7.3 R9 SUP basecalling for selected read IDs only." >&2
  "$DORADO" basecaller "$MODEL_PATH" "$POD5" \
    --device cpu \
    --emit-moves \
    --no-trim \
    --reference "$REFERENCE" \
    --read-ids "$READ_IDS" \
    --secondary no \
    > "$UNSORTED_BAM" 2> "$BASECALL_LOG"
  samtools sort -@ "$SAMTOOLS_THREADS" -o "$BAM" "$UNSORTED_BAM"
  samtools index "$BAM"
  rm -f "$UNSORTED_BAM"
fi

"$PYTHON" "$REPO_ROOT/src/algorithm/dorado_move_signal_bounds.py" \
  --bam "$BAM" \
  --pod5 "$POD5" \
  --sample-map "$SAMPLE_MAP" \
  --output "$BOUNDS" \
  --min-mapq 20

"$PYTHON" "$REPO_ROOT/src/algorithm/extract_pod5_signal_windows.py" \
  --manifest "$BOUNDS" \
  --output "$ARCHIVE" \
  --index "$INDEX" \
  --boundary-kind repeat \
  --padding 250 \
  --max-signal-len 10000

HASH_INPUTS=$WORK_ROOT/mastr_frozen_prediction_inputs.sha256
sha256sum \
  "$REPO_ROOT/src/algorithm/dorado_move_signal_bounds.py" \
  "$REPO_ROOT/src/algorithm/extract_pod5_signal_windows.py" \
  "$REPO_ROOT/src/algorithm/evaluate_external_confirmation.py" \
  "$REPO_ROOT/src/algorithm/evaluate_mastr_confirmation.py" \
  "$REPO_ROOT/src/algorithm/evaluate_repeat_periodicity_loso.py" \
  "$REPO_ROOT/ont-str-runner/configs/mastr_confirmation_acquisition.tsv" \
  "$REPO_ROOT/ont-str-runner/configs/mastr_runtime_versions.tsv" \
  "$REPO_ROOT/ont-str-runner/work/analysis/signal_repeat_windows_independent_qc_dev.index.tsv" \
  "$REPO_ROOT/ont-str-runner/work/analysis/signal_repeat_windows_independent_qc_dev.npz" \
  "$SAMPLE_MAP" \
  "$IDENTITY_AUDIT" \
  "$BOUNDS" \
  "$INDEX" \
  "$ARCHIVE" \
  > "$HASH_INPUTS.tmp"
mv "$HASH_INPUTS.tmp" "$HASH_INPUTS"

if [[ -e "$PREDICTIONS" && "$FORCE" != 1 ]]; then
  echo "Refusing to overwrite sealed predictions without FORCE=1: $PREDICTIONS" >&2
  exit 1
fi

"$PYTHON" "$REPO_ROOT/src/algorithm/evaluate_mastr_confirmation.py" predict \
  --external-index "$INDEX" \
  --external-archive "$ARCHIVE" \
  --output "$PREDICTIONS"
sha256sum "$PREDICTIONS" > "$PREDICTIONS.sha256"

echo "Sealed predictions are ready: $PREDICTIONS" >&2
echo "Frozen input hashes: $HASH_INPUTS" >&2
echo "Prediction hash: $PREDICTIONS.sha256" >&2
echo "Genotype truth has not been opened by this script." >&2
