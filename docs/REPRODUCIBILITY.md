# Reproducibility Guide

This guide describes how to reproduce all benchmarks and tables used in the paper.

## 1) Requirements
- **OS**: Linux or macOS
- **Docker** (required for WarpSTR and DeepRepeat; STRique uses Docker for indexing/counting)
- **Python 3** with `pandas` (for `compare_ground_truth.py`)
- **ripgrep (`rg`)** (used by batch scripts)
- **samtools** (required on host only if running STRique)

Install Python deps if needed:
```bash
python -m pip install pandas
```

Optional:
- **latexmk + TeX Live/MacTeX** to compile the paper

## 2) Data layout
Place each sample under `ont-str-runner/data/<SAMPLE>/` using the structure below:

```
ont-str-runner/data/<SAMPLE>/
  workspace/pass/0/            # single FAST5
  bam/<SAMPLE>.bam             # BAM
  bam/<SAMPLE>.bam.bai         # BAI
  htt.f5index                  # DeepRepeat index (one per repeat)
```

Notes:
- The runner will automatically create `workspace/pass_multi/0/` for WarpSTR.
- If your BAM is directly at `data/<SAMPLE>/<SAMPLE>.bam`, the scripts will use it.
- If your data live elsewhere, set `DATA_ROOT=/path/to/data` when invoking the scripts.

## 2.1) Download truth-sample archives

The public archive URLs and SRA accessions are tracked in:

```
ont-str-runner/configs/truth_samples.tsv
```

Download all primary HTT CAG truth samples:

```bash
bash ont-str-runner/scripts/download_truth_samples.sh
```

Download only the currently missing local truth samples:

```bash
bash ont-str-runner/scripts/download_truth_samples.sh ND31551 ND33947
```

The downloader stores each archive as:

```
ont-str-runner/data/<SAMPLE>/<SAMPLE>.tar.gz.1
```

Samples used in the paper:
- GM04723
- ND30015
- ND30016
- ND30047
- ND30422
- ND30626
- ND31551
- ND33392
- ND33947

## 3) Reference and DeepRepeat model
You must supply a reference FASTA and DeepRepeat model directory.

Recommended environment variables:
```bash
export REFERENCE_FASTA=/abs/path/to/reference_genome.fa
export DEEPREPEAT_MODEL_DIR=/abs/path/to/trainedmod_32_0.2
```

The DeepRepeat model can be downloaded from the authors (see their paper / repository). For convenience:
```bash
wget https://www.openbioinformatics.org/hx1/drmodel/trainedmod_32_0.2.tar.gz
mkdir -p models
cd models
 tar -xvf ../trainedmod_32_0.2.tar.gz
```
Then set:
```bash
export DEEPREPEAT_MODEL_DIR=$PWD/models/trainedmod_32_0.2
```

## 4) Build f5index (DeepRepeat)
DeepRepeat requires a `.f5index` file that maps read IDs to FAST5 paths.

To build it (Dockerized, no local Python deps):
```bash
DATA_ROOT=ont-str-runner/data \
  bash ont-str-runner/scripts/build_f5index_docker.sh <SAMPLE> ontfast5
```
This writes:
```
ont-str-runner/data/<SAMPLE>/htt.f5index.ontfast5
```
Rename to `htt.f5index` or pass the rebuilt file as the active index.

## 5) Check current benchmark status

Before starting long Docker runs, inspect staged inputs and strict output
completion:

```bash
python3 ont-str-runner/scripts/benchmark_status.py
```

Important: for the thesis benchmark, WarpSTR is only considered complete when
`predictions/alleles.csv` exists. An `overview.csv` alone is a partial output
and must not be used for final allele-level metrics.

## 6) Run the strict thesis benchmark

The strict runner implements the thesis rerun policy:

- nine Monteys HTT CAG truth samples only
- optional extraction of local sample archives
- preflight checks for `REFERENCE_FASTA`, `DEEPREPEAT_MODEL_DIR`, Docker, and
  host `samtools`
- timestamped backup of old tool outputs before fresh runs
- fresh WarpSTR, DeepRepeat, and STRique runs
- strict completion checks before regenerating tables

Use preflight first:

```bash
REFERENCE_FASTA=/abs/path/to/reference_genome.fa \
DEEPREPEAT_MODEL_DIR=/abs/path/to/trainedmod_32_0.2 \
ONLY_PREFLIGHT=1 \
  bash ont-str-runner/scripts/run_truth_benchmarks_strict.sh
```

Then run the full benchmark:

```bash
REFERENCE_FASTA=/abs/path/to/reference_genome.fa \
DEEPREPEAT_MODEL_DIR=/abs/path/to/trainedmod_32_0.2 \
RUN_STRIQUE=1 \
  bash ont-str-runner/scripts/run_truth_benchmarks_strict.sh
```

### Performance-optimized run

For a multi-core workstation, prefer the optimized runner after preflight. It
runs the heavy WarpSTR/Guppy phase with controlled threading, then runs
DeepRepeat and STRique in small parallel pools.

On a 20-core, 49 GiB RAM machine, a good starting point is:

```bash
REFERENCE_FASTA=/abs/path/to/reference_genome.fa \
DEEPREPEAT_MODEL_DIR=/abs/path/to/trainedmod_32_0.2 \
WARPSTR_JOBS=1 \
WARPSTR_THREADS=16 \
DEEPREPEAT_JOBS=2 \
STRIQUE_JOBS=2 \
RUN_STRIQUE=1 \
  bash ont-str-runner/scripts/run_truth_benchmarks_optimized.sh
```

Avoid running multiple WarpSTR jobs unless the machine has substantially more
than 20 cores. One WarpSTR/Guppy job can already use most of this machine.

Generated WarpSTR configs default to `tr_calling_config.visualize_alignment:
False`. This avoids thousands of per-read DTW alignment PNGs and keeps the
benchmark focused on repeat calls. For read-level debugging, set
`WARPSTR_VISUALIZE_ALIGNMENT=True` before generating configs.

To resume a partially completed strict rerun, use `FRESH_OUTPUTS=0
SKIP_COMPLETED=1`. The runner will keep completed strict outputs and rerun only
missing or failed sample-tool pairs.

Outputs:

```
ont-str-runner/work/analysis/ground_truth_comparison.csv
ont-str-runner/work/analysis/benchmark_failures.tsv
ont-str-runner/work/analysis/benchmark_report.md
```

Final benchmark status as of 2026-06-05:

- WarpSTR complete: 9/9 truth samples
- DeepRepeat complete: 9/9 truth samples
- STRique complete: 9/9 truth samples
- Failure/incomplete records: 0

Plain-English takeaway: WarpSTR is strongest overall on these labels, STRique
completes every sample but overestimates more often, and DeepRepeat has useful
signal/allocation evidence but weak GMM peak selection for short alleles. Treat
`ground_truth_comparison.csv` and `benchmark_report.md` as the final result
sources for the paper.

Old outputs are moved, not deleted, under:

```
ont-str-runner/work/benchmark_backups/<RUN_ID>/
```

## 7) Run individual tools for debugging
### Single sample
```bash
REFERENCE_FASTA=/abs/path/to/reference_genome.fa \
  DEEPREPEAT_MODEL_DIR=/abs/path/to/trainedmod_32_0.2 \
  bash ont-str-runner/scripts/run_warpstr.sh <SAMPLE>

REFERENCE_FASTA=/abs/path/to/reference_genome.fa \
  DEEPREPEAT_MODEL_DIR=/abs/path/to/trainedmod_32_0.2 \
  bash ont-str-runner/scripts/run_deeprepeat.sh <SAMPLE> htt chr4:3074876-3074933 CAG

bash ont-str-runner/scripts/run_strique.sh <SAMPLE>
```

### Legacy all-sample batch
The older batch runner is still available for exploratory work, but the strict
runner above should be used for thesis benchmark reruns.

```bash
REFERENCE_FASTA=/abs/path/to/reference_genome.fa \
DEEPREPEAT_MODEL_DIR=/abs/path/to/trainedmod_32_0.2 \
RUN_STRIQUE=1 \
  bash ont-str-runner/scripts/run_all_htt_samples.sh
```

If `configs/warpstr_<SAMPLE>.yaml` is missing, the runner will auto-generate it using `REFERENCE_FASTA`.

Logs are stored in:
```
ont-str-runner/work/logs/
```

## 8) Generate the comparison CSV/report manually
```bash
python3 ont-str-runner/scripts/compare_ground_truth.py
```
Outputs:
```
ont-str-runner/work/analysis/ground_truth_comparison.csv
ont-str-runner/work/analysis/benchmark_failures.tsv
ont-str-runner/work/analysis/benchmark_report.md
```

## 9) Build the paper
```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error paper/htt_cag_multisample_acm_bcb.tex
```

## Troubleshooting
- **DeepRepeat index errors**: the runner validates the index and will filter missing entries automatically.
- **Missing FAST5s in index**: rebuild with `build_f5index_docker.sh` and re-run.
- **STRique config errors**: ensure `ont-str-runner/configs/strique_config.tsv` has the required column order.
