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

## 5) Run the benchmarks
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

### All samples (batch)
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

## 6) Generate the comparison CSV (paper tables)
```bash
python ont-str-runner/scripts/compare_ground_truth.py
```
Output:
```
ont-str-runner/work/analysis/ground_truth_comparison.csv
```

## 7) Build the paper
```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error paper/htt_cag_multisample_acm_bcb.tex
```

## Troubleshooting
- **DeepRepeat index errors**: the runner validates the index and will filter missing entries automatically.
- **Missing FAST5s in index**: rebuild with `build_f5index_docker.sh` and re-run.
- **STRique config errors**: ensure `ont-str-runner/configs/strique_config.tsv` has the required column order.
