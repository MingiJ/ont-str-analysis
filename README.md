# ont-str-code

Reproducible benchmarking suite for signal-level STR counting on Nanopore HTT CAG samples.

## Repository map
- `paper/` — LaTeX source for the manuscript (`paper/htt_cag_multisample_acm_bcb.tex`).
- `ont-str-runner/` — minimal runner for WarpSTR, DeepRepeat, STRique.
- `docs/REPRODUCIBILITY.md` — step-by-step instructions to reproduce all results.
- `docs/legacy/README_history.md` — historical command logs (archived).

## Quick start (reproduce the benchmarks)
```bash
# 1) Put data in ont-str-runner/data/<SAMPLE>/ (see docs/REPRODUCIBILITY.md)
# 2) Set paths to your reference and DeepRepeat model
export REFERENCE_FASTA=/abs/path/to/reference_genome.fa
export DEEPREPEAT_MODEL_DIR=/abs/path/to/trainedmod_32_0.2

# 3) Run all samples (WarpSTR + DeepRepeat; add RUN_STRIQUE=1 to include STRique)
RUN_STRIQUE=1 bash ont-str-runner/scripts/run_all_htt_samples.sh

# 4) Build the comparison CSV used in the paper
python ont-str-runner/scripts/compare_ground_truth.py

# 5) Compile the paper
latexmk -pdf -interaction=nonstopmode -halt-on-error paper/htt_cag_multisample_acm_bcb.tex
```

## Data availability
Raw FAST5/BAM files are not included in this repository. See `docs/REPRODUCIBILITY.md` for the required directory layout and how to rebuild indices.

## Paper
- Source: `paper/htt_cag_multisample_acm_bcb.tex`
- BibTeX references: `paper/references.bib`

## Contact
Jeff Kimingi Karanja — jeff.kimingi.karanja@stud.edu.pl

Supervisor: Wiktor Ku\'smirek — Wiktor.Kusmirek@pw.edu.pl
