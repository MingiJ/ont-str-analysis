## What the README experiment is doing (plain-English walkthrough)

This document explains the intent behind the original `README.md` in the parent repo and how it maps to the three tools we are running here.

### Goal
Estimate STR repeat counts (e.g., HTT CAG) from Oxford Nanopore signal data, and compare results across tools.

### Data required
- FAST5 files (raw signal) per sample.
- BAM/SAM alignments per sample.
- Reference genome (the same one used to produce BAM).
- DeepRepeat `.f5index` for each sample and repeat (required by DeepRepeat).

### Why multiple tools
- **WarpSTR**: end-to-end STR caller from raw signal; includes basecalling and DTW-based repeat calling.
- **DeepRepeat**: signal-level repeat detection using FAST5 + BAM + repeat coordinates.
- **STRique**: signal-level STR counting with pre-defined flanks and a pore model.

### Typical flow used in the README (simplified)
1) Convert single FAST5 to multi FAST5 (required by WarpSTR).
2) Run WarpSTR:
   - Extract reads around the locus.
   - Basecall with Guppy.
   - Generate expected signal from the repeat motif.
   - Align signal to expected repeat states (DTW).
   - Report allele lengths and repeat counts.
3) Run DeepRepeat:
   - Use BAM + FAST5 + repeat coordinates.
   - Requires a prebuilt `.f5index` for the FAST5 directory.
   - Output repeat estimates, with model-based statistics.
4) Run STRique:
   - Create FAST5 index (`.fofn`).
   - Run counting using flanks + motif model.

### What the README outputs show
- WarpSTR log lines show allele lengths (WarpSTR vs basecall).
- Times are long (hours per sample).
- The author ran multiple samples and recorded repeat unit counts (CAG/CGC etc).

### What we are doing differently
- We keep the same scientific intent but make the process reproducible:
  - consistent folder layout
  - reusable configs
  - scripts to avoid manual command chains

## Step-by-step example (using ND30626)

### 1) Put the data in place
Expected layout:
```
data/ND30626/
  workspace/pass/0/         # single fast5 files
  ND30626.bam
  ND30626.bam.bai
  htt.f5index               # DeepRepeat index (required)
```

If you do not have an `.f5index`, DeepRepeat will fail. You must create it
with the same tool you used previously for other runs (the exact generator
depends on your local DeepRepeat workflow). Once you have it, place it at:
`data/<SAMPLE>/<REPEAT_NAME>.f5index` (for HTT, the example uses `htt.f5index`).

### 2) Configure WarpSTR
Edit `configs/warpstr_ND30626.yaml`:
- `reference_path` = full reference genome path
- `output` = output folder
- `inputs` path points to `data/` and `runs: ND30626`
- `guppy_config.path` = `/opt/ont/guppy/bin/guppy_basecaller`
- `loci` includes HTT CAG coordinates
- `threads` set to match your CPU (e.g., 12)

### 3) Configure STRique
Edit `configs/strique_config.tsv` and set real flanks:
```
name    chrom   start   end     motif   prefix  suffix
HTT_CAG chr4    3074876 3074933 CAG     <PREFIX> <SUFFIX>
```

### 4) Run WarpSTR
```
bash scripts/run_warpstr.sh ND30626
```
This will:
- convert single FAST5 to multi FAST5 (if needed; WarpSTR requires multi FAST5),
- extract reads at the locus,
- basecall with Guppy,
- perform DTW-based repeat calling,
- output results under `work/warpstr/ND30626`.

### 5) Run DeepRepeat
```
bash scripts/run_deeprepeat.sh ND30626 HTT_CAG chr4:3074876-3074933 CAG
```
This will:
- use `ND30626.bam` + FAST5 + `htt.f5index` (required),
- run repeat detection on HTT CAG,
- write logs/results under `work/deeprepeat/ND30626`.

Note: the `htt.f5index` must match the FAST5 files present in `workspace/pass/0`. If the index is out of sync (missing files), DeepRepeat can fail. The runner now validates the index and will auto-generate a filtered index under `work/deeprepeat/<SAMPLE>/<REPEAT>.f5index.filtered` when missing entries are detected.
If the index still looks out of sync (missing entries or extra FAST5 files), the runner can rebuild the index from FAST5 using `scripts/build_f5index_docker.sh` (enabled by default; set `DEEPR_INDEX_FALLBACK=0` to disable).
To avoid missing-read errors, the runner also filters the BAM to read IDs present in the index (set `DEEPR_FILTER_BAM=0` to disable).

### 6) Run STRique
```
bash scripts/run_strique.sh ND30626
```
This will:
- create a FAST5 index (`.fofn`),
- count repeats using the STRique model,
- write output to `work/strique/ND30626.txt`.

### 7) Compare outputs
Look for:
- WarpSTR summaries in `work/warpstr/ND30626/*/overview.csv`
- DeepRepeat log in `work/deeprepeat/ND30626/HTT_CAG.log`
- STRique counts in `work/strique/ND30626.txt`
