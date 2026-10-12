# ont-str-runner

Minimal, repeatable runner for WarpSTR, DeepRepeat, and STRique.

## Folder layout
```
ont-str-runner/
  data/
    <SAMPLE>/
      workspace/pass/0/           # single fast5 files
      bam/<SAMPLE>.bam            # alignments (required for DeepRepeat/STRique)
      bam/<SAMPLE>.bam.bai
  work/
    warpstr/
    deeprepeat/
    strique/
  configs/
    warpstr_<SAMPLE>.yaml
    strique_config.tsv
  scripts/
    run_warpstr.sh
    run_deeprepeat.sh
    run_strique.sh
```

## Required inputs
- FAST5 (single) at `data/<SAMPLE>/workspace/pass/0/`
- BAM + BAI at `data/<SAMPLE>/bam/<SAMPLE>.bam`
- WarpSTR config at `configs/warpstr_<SAMPLE>.yaml` (can be auto-generated)
- STRique config at `configs/strique_config.tsv`
- DeepRepeat f5index at `data/<SAMPLE>/<REPEAT_NAME>.f5index`

## Example repeat definition
- name: `HTT_CAG`
- coord: `chr4:3074876-3074933`
- sequence: `CAG`

## Quick start
1) Put data in `data/<SAMPLE>/` as shown above.
2) Generate WarpSTR config (requires a reference FASTA):
```bash
REFERENCE_FASTA=/abs/path/to/reference_genome.fa \
  bash scripts/make_warpstr_config.sh <SAMPLE> "$REFERENCE_FASTA"
```
3) Review `configs/strique_config.tsv` (see STRique config format below).
4) Run tools:
```bash
bash scripts/run_warpstr.sh <SAMPLE>
bash scripts/run_deeprepeat.sh <SAMPLE> HTT_CAG chr4:3074876-3074933 CAG
bash scripts/run_strique.sh <SAMPLE>
```

For strict thesis reruns on a multi-core workstation:
```bash
REFERENCE_FASTA=/abs/path/to/reference_genome.fa \
DEEPREPEAT_MODEL_DIR=/abs/path/to/trainedmod_32_0.2 \
WARPSTR_JOBS=1 WARPSTR_THREADS=16 DEEPREPEAT_JOBS=2 STRIQUE_JOBS=2 RUN_STRIQUE=1 \
  bash scripts/run_truth_benchmarks_optimized.sh
```

## Final truth-sample benchmark

The final published-ground-truth HTT CAG benchmark completed on 2026-06-05:

- WarpSTR complete: 9/9 samples
- DeepRepeat complete: 9/9 samples
- STRique complete: 9/9 samples
- Failure/incomplete records: 0

Final result files:

```text
work/analysis/ground_truth_comparison.csv
work/analysis/benchmark_report.md
work/analysis/benchmark_failures.tsv
```

Plain-English takeaway: WarpSTR is strongest overall, STRique completes every
sample but overestimates more often, and DeepRepeat has useful
signal/allocation evidence but weak GMM peak selection for short alleles.

By default, generated WarpSTR configs disable per-read DTW alignment PNGs
(`tr_calling_config.visualize_alignment: False`) because they are slow and not
needed for the thesis benchmark table. Set `WARPSTR_VISUALIZE_ALIGNMENT=True`
when debugging individual reads.

If your STRique pore model differs, override it:
```bash
STRIQUE_MODEL=/app/models/<MODEL>.model bash scripts/run_strique.sh <SAMPLE>
```

## Environment variables
- `DATA_ROOT` — data root (default: `ont-str-runner/data`)
- `REFERENCE_FASTA` — reference FASTA path (used to auto-generate WarpSTR configs)
- `DEEPREPEAT_MODEL_DIR` — DeepRepeat model directory (default: `models/trainedmod_32_0.2`)
- `RUN_STRIQUE=1` — when set, `run_all_htt_samples.sh` will also run STRique
- `WARPSTR_THREADS`, `WARPSTR_JOBS`, `DEEPREPEAT_JOBS`, `STRIQUE_JOBS` — optimized benchmark runner controls
- `WARPSTR_VISUALIZE_ALIGNMENT` — set to `True` to write per-read WarpSTR DTW alignment PNGs; default is `False`
- `SKIP_COMPLETED=1` — optimized benchmark runner resumes from strict completed outputs; use with `FRESH_OUTPUTS=0`

## Batch STRique on VM (native, sequential downloads)
For low-disk VMs, use the batch script to download one sample at a time,
run STRique, store results on `/mnt`, and delete sample data:
```bash
bash scripts/run_strique_vm_batch.sh
```
Outputs accumulate under `/mnt/ont-str-results/strique/` for a single rsync back to your Mac.
You can resume from a specific sample:
```bash
START_AT=ND30015 bash scripts/run_strique_vm_batch.sh
```
The script also auto-resumes by skipping samples already completed (checks
`/mnt/ont-str-results/strique/<SAMPLE>.txt` and `/mnt/ont-str-results/strique/.done`).

## STRique config format (important)
The STRique TSV **must** use this column order and header:
```
chr    begin    end    name    repeat    prefix    suffix
```
If the file is in the older order (e.g., `name, chrom, start, end, motif, ...`),
STRique will fail with an error like:
`ValueError: invalid literal for int() with base 10: 'chr4'`.

## Notes
- WarpSTR requires multi fast5, so the script converts from single fast5 automatically.
- DeepRepeat needs a valid `.f5index` for the FAST5 folder. Place it in `data/<SAMPLE>/<REPEAT_NAME>.f5index`.
  - If the index is out of sync (references missing FAST5 files), DeepRepeat can fail. The runner now validates the index and will write a filtered copy to `work/deeprepeat/<SAMPLE>/<REPEAT>.f5index.filtered` and use that automatically.
  - If the index still appears out of sync, the runner can rebuild it from FAST5 using `scripts/build_f5index_docker.sh` (enabled by default; set `DEEPR_INDEX_FALLBACK=0` to disable).
  - The runner filters the BAM to read IDs present in the index to avoid missing-read errors (set `DEEPR_FILTER_BAM=0` to disable).
- DeepRepeat requires the trained model directory. Set `DEEPREPEAT_MODEL_DIR` (default: `models/trainedmod_32_0.2` under repo root).
- STRique creates a `.fofn` index and uses the provided model file.
  - If your download unpacks to `data/<SAMPLE>/<SAMPLE>/workspace/...`, symlink
    `data/<SAMPLE>/workspace` to `data/<SAMPLE>/<SAMPLE>/workspace` so STRique can find FAST5s.
