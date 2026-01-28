# Agent Guide: ont-str-code

This file is for future assistants working in this repo. It gives a fast map of the codebase, how to manage context, and how to compare WarpSTR/DeepRepeat/STRique results while designing a better algorithm.

## Quick map (where to look first)
- `ont-str-runner/` — main runner scaffolding for WarpSTR, DeepRepeat, STRique.
  - `ont-str-runner/README.md` — clean, up-to-date runner workflow.
  - `ont-str-runner/EXPLAINER.md` — plain-English walkthrough of the pipeline.
  - `ont-str-runner/scripts/` — entrypoints:
    - `run_warpstr.sh`
    - `run_deeprepeat.sh`
    - `run_strique.sh`
  - `ont-str-runner/configs/` — generated WarpSTR configs and STRique TSV.
  - `ont-str-runner/work/` — **outputs** by tool (warpstr/deeprepeat/strique).
- `README.md` (repo root) — publication-oriented overview and entry points.
- `docs/REPRODUCIBILITY.md` — step-by-step instructions to rerun benchmarks.
- `src/` — code for custom algorithm experiments.
- `extern/` — external dependencies.
- `img/` — analysis scripts/plots.

## Context management (how to avoid getting lost)
When answering questions or analyzing results, keep the context small and focus on 3 things:
1) **Sample ID** (e.g., ND30626)
2) **Tool** (WarpSTR vs DeepRepeat vs STRique)
3) **Output files** (exact log/CSV/SVG paths)

Communication style for this repo:
- Explain results **as simply as possible** so non-bioinformatics readers can follow.
- Be **friendly** and use short, clear sentences.
- Use **analogies** when helpful (e.g., “repeat counting is like measuring how many tiles fit in a pattern”).
- Always give the **plain-English takeaway** before technical detail.

Practical tips:
- Start from `ont-str-runner/EXPLAINER.md` when unsure about tool flow.
- For WarpSTR: only open the summary outputs first; avoid diving into large alignment logs unless asked.
- For DeepRepeat: prefer the most recent `*.log` (often `*_retry.log`) and the corresponding `.fs.more*` file.
- If older `.more` files were deleted, rely on retry outputs and note that allele counts may need regeneration.
- Always quote file paths when referring to results (helps other agents jump in quickly).

## Where results live (per tool)
### WarpSTR outputs
Typical path: `ont-str-runner/work/warpstr/<SAMPLE>/<LOCUS>/`
Key files:
- `overview.csv` — per-read repeat counts and DTW costs (primary quantitative output).
- `predictions/alleles.csv` — allele summary (two peaks + read counts).
- `summaries/alleles.svg` — histogram plot of repeat counts.
- `summaries/state_similarity.csv` — signal-vs-expected similarity summary.

### DeepRepeat outputs
Typical path: `ont-str-runner/work/deeprepeat/<SAMPLE>/`
Key files:
- `<REPEAT>.log` or `<REPEAT>_retry.log` — main log with per-read precision/recall/F1.
- `<SAMPLE>.fs.more*` — read list with strand flags; used to connect reads to downstream analysis.
- `trainedmod_32_0.2/` symlink — indicates which model was used.

### STRique outputs
Typical path: `ont-str-runner/work/strique/`
Key files:
- `<SAMPLE>.txt` — repeat count output (if generated).

## How to compare tools (repeat counts)
Use the same sample/locus and compare repeat distributions, not just single numbers.

Minimum viable comparison (WarpSTR vs DeepRepeat):
1) WarpSTR allele peaks from `predictions/alleles.csv`.
2) WarpSTR per-read repeat calls from `overview.csv`.
3) DeepRepeat per-read metrics from `*_retry.log` (quality) + `.fs.more.retry` (read list).
4) If DeepRepeat provides repeat counts (or can be derived), build a histogram and compare with WarpSTR.

If you need read-by-read alignment:
- Use read IDs from `overview.csv` and match to IDs in `.fs.more.retry` or DeepRepeat logs.
- Build a join table on read_name and compare counts or confidence per read.

## Objective ground truth (HTT CAG repeats)
Use this table as the **ground truth** allele sizes and HTT status when validating tools or new algorithms. It comes from the supplementary PDF provided by the user (see source link below).

Source (Supplementary Table S4): `https://pmc.ncbi.nlm.nih.gov/articles/instance/5363210/bin/mmc1.pdf`
Supplementary Table 4 columns include SNP1 genotype (SNP/Normal/Mutant bases), the targeted allele (Mutant/Normal), and the family ID.

Family column explanation: this is the donor family or pedigree ID used in the paper to group related HD fibroblast lines. When it says "Unknown," the sample did not have a family ID reported in the table.

| Sample  | CAG repeats (long/short) | HTT status | SNP/Normal/Mutant (SNP1) | Family |
|---------|---------------------------|------------|---------------------------|--------|
| GM04723 | 72 / 17                   | Mutant     | C/G G C                   | 691 |
| GM04767 | 47 / 18                   | Mutant     | C/G G C                   | 691 |
| ND30015 | 41 / 20                   | Mutant     | C/G G C                   | NINDS3749 |
| ND30016 | 41 / 21                   | Mutant     | C/G G C                   | NINDS3749 |
| ND30047 | 41 / 18                   | Mutant     | C/G G C                   | NINDS3753 |
| ND30422 | 40 / 18                   | Mutant     | C/G G C                   | NINDS3751 |
| ND30626 | 41 / 21                   | Mutant     | C/G G C                   | NINDS3752 |
| ND31038 | 44 / 19                   | Normal     | C/G C G                   | NINDS3752 |
| ND31551 | 39 / 18                   | Normal     | C/G C G                   | Unknown |
| ND33392 | 57 / 17                   | Mutant     | C/G G C                   | NINDS4250 |
| ND33947 | 40 / 18                   | Mutant     | C/G G C                   | Unknown |

Raw Supplementary Table 4 excerpt (from the PMC supplementary PDF):
```
GM04723  CAG:72/17  Mutant  691
GM04767  CAG:47/18  Mutant  691
ND30015  CAG:41/20  Mutant  NINDS3749
ND30016  CAG:41/21  Mutant  NINDS3749
ND30047  CAG:41/18  Mutant  NINDS3753
ND30422  CAG:40/18  Mutant  NINDS3751
ND30626  CAG:41/21  Mutant  NINDS3752
ND31038  CAG:44/19  Normal  NINDS3752
ND31551  CAG:39/18  Normal  Unknown
ND33392  CAG:57/17  Mutant  NINDS4250
ND33947  CAG:40/18  Mutant  Unknown
```
How to use this table:
- Compare tool allele peaks to the long/short CAG values above.
- Check that mutant/normal classification aligns with the observed long allele size.
- Use this as the “label” set for algorithm evaluation and error analysis.

## What the tools actually do (very short)
- **WarpSTR**: aligns raw signal to an expected signal pattern (DTW) to *count repeat units per read*.
- **DeepRepeat**: uses a trained model to *classify signal positions as repeat/non-repeat*, yielding per-read quality metrics; repeat counts often derived from extra outputs.
- **STRique**: signal-level STR counter using flanking sequences and a pore model.

## Algorithm design notes (what to improve)
Common failure modes seen in logs:
- **Event segmentation warnings** (“less split points generated”) → noisy signal or poor event detection.
- **Boundary ambiguity** → repeat vs flank transitions are fuzzy and cause FP/FN.
- **Mapping dependence** → if BAM mapping is off, signal extraction is misaligned.

High-value improvements:
- Better repeat boundary detection (use signal + sequence context).
- Joint model: per-read **repeat count + confidence score**.
- Robustness to strand/reverse-complement differences.
- A principled way to cluster alleles with uncertainty.

## Quick “analysis checklist” for a new sample
1) Confirm input files exist (FAST5, BAM, f5index).
2) Run WarpSTR and read `predictions/alleles.csv` + `summaries/alleles.svg`.
3) Run DeepRepeat and inspect the latest log (`*_retry.log`).
4) Compare allele peaks and read counts between tools.
5) Document disagreements (outliers, low-F1 reads, multi-modal peaks).

## Good starting files to open
- `ont-str-runner/EXPLAINER.md`
- `ont-str-runner/README.md`
- `ont-str-runner/work/warpstr/<SAMPLE>/<LOCUS>/predictions/alleles.csv`
- `ont-str-runner/work/warpstr/<SAMPLE>/<LOCUS>/summaries/alleles.svg`
- `ont-str-runner/work/deeprepeat/<SAMPLE>/*_retry.log`

## Notes about this repo
- The repo root `README.md` is the publication-oriented overview; detailed runner usage is in `ont-str-runner/README.md`.
- Outputs are big; avoid loading large logs unless necessary. Prefer summaries first.

## Publication and thesis notes (for documentation/papers)
- Thesis title: **Direct Estimation of Short Tandem Repeat Expansions from Raw Nanopore Signals using a Deep Recurrent Neural Network**
- Degree/program: Master of Science in Computer Science
- Institution: Warsaw University of Technology (Warsaw, Masovian Voivodeship, Poland)
- Author: Jeff Kimingi Karanja (ID: 342068)
- Supervisor: Kuśmirek Wiktor
- External data location: `/Volumes/Legion/thesis/data` (contains GM04723, ND29970, ND30015, ND30016, ND30047, ND30422, ND30626, ND31551, ND33392, ND33947, ND40534)
- Paper format currently used in this repo: ACM-BCB (acmart `sigconf`) draft in `paper/htt_cag_multisample_acm_bcb.tex`

## Pipeline handoff notes (recent changes to keep future agents in sync)
- Data location: runners default to `ont-str-runner/data`. Override with `DATA_ROOT=/path/to/data` as needed.
- Batch runner: `ont-str-runner/scripts/run_all_htt_samples.sh` now skips WarpSTR if `overview.csv` exists, and skips DeepRepeat only if `htt.log` contains `Testing Finished!` and has no errors.
- DeepRepeat robustness:
  - `ont-str-runner/scripts/run_deeprepeat.sh` now validates `.f5index` entries and auto-filters missing FAST5 entries.
  - If index is out of sync, it can rebuild from FAST5 via `scripts/build_f5index_docker.sh` (dockerized ont-fast5-api). Controlled by `DEEPR_INDEX_FALLBACK` (default 1).
  - BAM is filtered to read IDs present in the index to avoid `Error! Cannot find read_it` (`DEEPR_FILTER_BAM`, default 1).
  - DeepRepeat mounts `/Volumes/Legion` into Docker automatically when available.
- F5index fallback: `ont-str-runner/scripts/build_f5index_docker.sh` generates `htt.f5index.ontfast5` (or `.h5py`) in `data/<SAMPLE>/`. For ND30016, rebuilt index matched filtered index exactly.
- DeepRepeat messaging fix: after rebuild, stats are recomputed so “extra FAST5” warnings aren’t stale.
- Comparison script: `ont-str-runner/scripts/compare_ground_truth.py` now parses DeepRepeat GMM peaks/allocr, computes `deeprepeat_gmm_missed_short`, and adds new columns to `ground_truth_comparison.csv`.
- Paper update: `paper/htt_cag_multisample_acm_bcb.tex` discussion now includes a DeepRepeat peak-selection weakness; added a preliminary table of samples where GMM misses the short allele.
- GM04723 added: included in batch list; ground truth added (72/17). WarpSTR configs are now auto-generated (see `make_warpstr_config.sh`).
- Logging note: `run_all_htt_samples.log` is overwritten on each restart (stdout `>`). Switch to `>>` if you need full history.
