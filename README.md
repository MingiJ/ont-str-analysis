# ont-str-code

Reproducible benchmarking suite for signal-level STR counting on Nanopore HTT CAG samples.

## Repository map
- `paper/` — LaTeX source for the manuscript (`paper/htt_cag_multisample_acm_bcb.tex`).
- `ont-str-runner/` — minimal runner for WarpSTR, DeepRepeat, STRique.
- `docs/REPRODUCIBILITY.md` — step-by-step instructions to reproduce all results.
- `docs/legacy/README_history.md` — historical command logs (archived).

## Quick start (reproduce the benchmarks)
```bash
# 1) Download or stage truth-sample archives
bash ont-str-runner/scripts/download_truth_samples.sh

# 2) Set paths to your reference and DeepRepeat model
export REFERENCE_FASTA=/abs/path/to/reference_genome.fa
export DEEPREPEAT_MODEL_DIR=/abs/path/to/trainedmod_32_0.2

# 3) Run strict preflight, then the fresh benchmark
ONLY_PREFLIGHT=1 bash ont-str-runner/scripts/run_truth_benchmarks_strict.sh
RUN_STRIQUE=1 bash ont-str-runner/scripts/run_truth_benchmarks_strict.sh

# 4) Review generated comparison/report files under ont-str-runner/work/analysis/

# 5) Compile the paper
latexmk -pdf -interaction=nonstopmode -halt-on-error paper/htt_cag_multisample_acm_bcb.tex
```

## Data availability
Raw FAST5/BAM files are not included in this repository. Public archive URLs for
the HTT CAG truth samples are tracked in
`ont-str-runner/configs/truth_samples.tsv`; see `docs/REPRODUCIBILITY.md` for
download, staging, and index notes.

## Paper
- Source: `paper/htt_cag_multisample_acm_bcb.tex`
- BibTeX references: `paper/references.bib`

## Final benchmark results
The completed 9-sample HTT CAG truth benchmark has strict complete outputs for
WarpSTR, DeepRepeat, and STRique, with zero failure/incomplete records. The
paper results are sourced from:

```text
ont-str-runner/work/analysis/ground_truth_comparison.csv
ont-str-runner/work/analysis/benchmark_report.md
ont-str-runner/work/analysis/benchmark_failures.tsv
```

Plain-English takeaway: WarpSTR is strongest overall, STRique completes every
sample but overestimates more often, and DeepRepeat has useful
signal/allocation evidence but weak GMM peak selection for short alleles.

## Contact
Jeff Kimingi Karanja — jeff.kimingi.karanja@stud.edu.pl

Supervisor: Wiktor Ku\'smirek — Wiktor.Kusmirek@pw.edu.pl
