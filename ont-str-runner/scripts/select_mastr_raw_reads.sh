#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}
WORK_ROOT=${MASTR_WORK_ROOT:-$REPO_ROOT/ont-str-runner/work/mastr}
DORADO=${DORADO:-$REPO_ROOT/tools/dorado-0.7.3-linux-x64/bin/dorado}
FAST_MODEL=${DORADO_SELECTION_MODEL:-dna_r9.4.1_e8_fast@v3.4}
MODEL_ROOT=${DORADO_MODEL_ROOT:-$REPO_ROOT/tools/dorado-models}
MODEL_PATH=$MODEL_ROOT/$FAST_MODEL
REFERENCE=${MASTR_REFERENCE:-/home/jkaranja/workdir/references/hg38.chr4.fa}
POD5=${MASTR_POD5:-$WORK_ROOT/raw/FAW16852.pod5}
MANIFEST=${MASTR_ACQUISITION_MANIFEST:-$REPO_ROOT/ont-str-runner/configs/mastr_confirmation_acquisition.tsv}
PYTHON=${PYTHON:-$REPO_ROOT/.venv/bin/python}
SAMTOOLS_THREADS=${SAMTOOLS_THREADS:-4}
SELECTION_SHARDS=${SELECTION_SHARDS:-1}
MAX_SELECTION_RAW_READS=${MAX_SELECTION_RAW_READS:-15000}
RAW_SCREEN_SEED=${RAW_SCREEN_SEED:-mastr-raw-screen-v1}
FORCE=${FORCE:-0}

UNSORTED_BAM=$WORK_ROOT/mastr.dorado-0.7.3.r9-fast-v3.4.selection.unsorted.bam
BAM=$WORK_ROOT/mastr.dorado-0.7.3.r9-fast-v3.4.selection.bam
LOG_PREFIX=$WORK_ROOT/mastr.dorado-0.7.3.r9-fast-v3.4.selection
SAMPLE_MAP=$WORK_ROOT/selected_read_samples.tsv
READ_IDS=$WORK_ROOT/selected_read_ids.txt

for path in "$DORADO" "$REFERENCE" "$POD5" "$MANIFEST" "$PYTHON"; do
  if [[ ! -e "$path" ]]; then
    echo "Missing required input: $path" >&2
    exit 1
  fi
done

mkdir -p "$WORK_ROOT" "$MODEL_ROOT"
if [[ ! -d "$MODEL_PATH" ]]; then
  "$DORADO" download --model "$FAST_MODEL" --directory "$MODEL_ROOT"
fi

if [[ "$FORCE" == 1 || ! -s "$BAM" || ! -s "$BAM.bai" ]]; then
  if (( SELECTION_SHARDS < 1 )); then
    echo "SELECTION_SHARDS must be at least 1" >&2
    exit 1
  fi
  echo "Running truth-free Dorado FAST selection in $SELECTION_SHARDS deterministic shards." >&2
  "$PYTHON" - "$POD5" "$WORK_ROOT" "$SELECTION_SHARDS" "$MAX_SELECTION_RAW_READS" "$RAW_SCREEN_SEED" <<'PY'
import hashlib
from pathlib import Path
import sys
import pod5

pod5_path = Path(sys.argv[1])
work_root = Path(sys.argv[2])
shard_count = int(sys.argv[3])
max_reads = int(sys.argv[4])
seed = sys.argv[5]
with pod5.Reader(pod5_path) as reader:
    ranked = sorted(
        (hashlib.sha256(f"{seed}\0{read_id}".encode()).digest(), str(read_id))
        for read_id in reader.read_ids
    )
if max_reads > 0:
    ranked = ranked[:max_reads]
handles = [
    (work_root / f"selection.shard-{index}.read_ids.txt").open("w")
    for index in range(shard_count)
]
counts = [0] * shard_count
try:
    for index, (_, read_id) in enumerate(ranked):
        shard = index % shard_count
        handles[shard].write(f"{read_id}\n")
        counts[shard] += 1
finally:
    for handle in handles:
        handle.close()
print(f"raw_uuid_screen={len(ranked)} seed={seed} read_id_shards=" + ",".join(str(count) for count in counts))
PY

  rm -f "$UNSORTED_BAM"
  pids=()
  shard_bams=()
  for (( shard=0; shard<SELECTION_SHARDS; shard++ )); do
    shard_ids=$WORK_ROOT/selection.shard-$shard.read_ids.txt
    shard_bam=$WORK_ROOT/selection.shard-$shard.unsorted.bam
    shard_log=$LOG_PREFIX.shard-$shard.log
    rm -f "$shard_bam"
    "$DORADO" basecaller "$MODEL_PATH" "$POD5" \
      --device cpu \
      --read-ids "$shard_ids" \
      --kit-name SQK-NBD114-24 \
      --no-trim \
      --reference "$REFERENCE" \
      --secondary no \
      > "$shard_bam" 2> "$shard_log" &
    pids+=("$!")
    shard_bams+=("$shard_bam")
  done

  failed=0
  for pid in "${pids[@]}"; do
    if ! wait "$pid"; then
      failed=1
    fi
  done
  if (( failed )); then
    echo "At least one Dorado selection shard failed; inspect $LOG_PREFIX.shard-*.log" >&2
    exit 1
  fi
  samtools merge -@ "$SAMTOOLS_THREADS" -f "$UNSORTED_BAM" "${shard_bams[@]}"
  samtools sort -@ "$SAMTOOLS_THREADS" -o "$BAM" "$UNSORTED_BAM"
  samtools index "$BAM"
  rm -f "$UNSORTED_BAM" "${shard_bams[@]}"
fi

"$PYTHON" "$REPO_ROOT/src/algorithm/select_barcoded_htt_reads.py" \
  --bam "$BAM" \
  --acquisition-manifest "$MANIFEST" \
  --sample-map "$SAMPLE_MAP" \
  --read-ids "$READ_IDS" \
  --min-mapq 20 \
  --max-reads-per-sample 128 \
  --min-reads-per-sample 6

echo "Wrote raw UUID/sample map: $SAMPLE_MAP" >&2
echo "Wrote frozen SUP selection: $READ_IDS" >&2
"$REPO_ROOT/ont-str-runner/scripts/audit_mastr_archive_mapping.sh"
