# Evaluating Signal-Level STR Counting Methods on HTT CAG Samples Against Ground Truth

Author(s): [Your Name(s)]

## Abstract
We evaluate three signal-level short tandem repeat (STR) counting methods across 11 processed Huntington's disease samples at the HTT CAG locus (9 with published ground truth). We provide a detailed ND30626 case study and a multi-sample summary. WarpSTR allele peaks align closely with ground truth overall (mean absolute error: 0.38 repeats for the long allele, 0.75 for the short allele) but undercount the short allele in ND30626. STRique emits per-read repeat counts for all samples; after filtering zeros and extreme outliers (>200), its peaks show higher error (mean absolute error: 1.89 long, 1.44 short) and a tendency to overestimate the long allele. DeepRepeat processes reads but does not emit repeat counts in the current outputs; its logs show frequent segmentation warnings and missed short-allele modes in multiple samples. We propose concrete improvements: repeat-unit calibration, more robust boundary detection, and per-read confidence scores that feed uncertainty-aware allele clustering.

Plain-English takeaway: Across samples, WarpSTR is closest to the truth. STRique counts are usable but noisy without filtering. DeepRepeat still lacks repeat counts. The biggest opportunity is to fix boundary detection and convert counts into repeat units consistently.

## 1. Introduction
Counting STRs from nanopore signal is like measuring how many tiles fit in a repeating floor pattern: if you cut the pattern too early or too late, the count shifts by a few tiles even if the pattern itself is correct. This paper combines a multi-sample summary with a detailed ND30626 case study to understand where three methods agree with the ground truth and where they do not. We use the published HTT CAG ground truth (long/short CAG repeats per sample) as the reference label and compare WarpSTR, DeepRepeat, and STRique outputs to that label.

## 2. Materials and Methods

### 2.1 Samples and Ground Truth
Processed samples in the repo: GM04723, ND29970, ND30015, ND30016, ND30047, ND30422, ND30626, ND31551, ND33392, ND33947, ND40534.
Published ground truth is available for 9 of these samples (all except ND29970 and ND40534). ND30626 (41 / 21 repeats) is used as the detailed case study.

### 2.2 Data and Inputs
We use raw FAST5 signal, a BAM alignment, and a reference genome. WarpSTR is configured via `ont-str-runner/configs/warpstr_ND30626.yaml` with HTT coordinates `chr4:3074876-3074933` and motif `CAG`. DeepRepeat uses the sample BAM, FAST5 index (`htt.f5index`), and the same repeat coordinates.

### 2.3 Tools Evaluated
- WarpSTR: signal-level DTW alignment to an expected repeat pattern with allele clustering.
- DeepRepeat: model-based signal classification with repeat-region detection and per-read metrics.
- STRique: signal-level repeat counting using flank sequences and a pore model.

### 2.4 Evaluation Strategy
We compare each tool's allele estimates to the ground truth. For WarpSTR, we report both its DTW-based allele peaks and its basecall-derived peaks. For interpretability, we also convert peaks to approximate CAG repeat counts by dividing by 3 (CAG length) and rounding. For STRique, we use the per-read `count` field as repeat units, filter counts to 1-200, and identify dominant peaks in a short range (10-29) and long range (30-120).

## 3. Results
We first present a detailed ND30626 case study, followed by a multi-sample summary across all processed HTT CAG samples.

### 3.1 WarpSTR
Plain-English takeaway: WarpSTR finds two clear peaks that line up with a long mutant allele, but the short allele appears too small.

WarpSTR produces 3,757 per-read calls in `overview.csv`. After removing 9 negative values and 6 extreme outliers (>300), 3,742 reads remain for peak analysis. Two dominant peaks appear at 124 and 52 (WarpSTR units), with 58.85% and 41.15% of reads assigned to each peak, respectively. The same two-peak structure is present in the basecall-derived alleles (120 and 51). Median DTW costs are low for both peaks, suggesting stable alignments.

Key numbers:
- Total reads: 3,757 (3,742 used for peak analysis)
- WarpSTR allele peaks: 124 (2,202 reads, 58.85%), 52 (1,540 reads, 41.15%)
- Basecall allele peaks: 120 (2,212 reads, 59.11%), 51 (1,530 reads, 40.89%)
- DTW cost (median, dtw_cost1): 0.168 for the 124 peak, 0.196 for the 52 peak

Interpreting counts as base pairs yields approx 41 and 17 CAG repeats (124/3 and 52/3), matching the long allele but undercounting the short allele by ~4 repeats. The 120/51 basecall peaks map to ~40 and 17 repeats.

### 3.2 DeepRepeat
Plain-English takeaway: DeepRepeat processes the data but does not output repeat counts for ND30626 in this run, and its log signals segmentation difficulty.

DeepRepeat reports 3,975 reads in the log and outputs a read list of 3,784 reads (`ND30626.fs.more.retry`). The log contains 52,472 "less split points generated" warnings, indicating frequent event-segmentation issues that can blur repeat boundaries. No repeat-count file is present in the repo for ND30626, so allele comparison is not possible for this run.

### 3.3 STRique
Plain-English takeaway: STRique outputs repeat counts with two broad modes, but the short allele is still low and the distribution is noisy.

STRique outputs 3,823 per-read counts in `ND30626.txt`. We exclude 330 zero counts and 198 extreme outliers (>200), leaving 3,295 reads for peak analysis. The most frequent short-range peak (10-29) is 18 repeats (320 reads), and the most frequent long-range peak (30-120) is 43 repeats (304 reads). Compared to ground truth (41/21), STRique slightly overestimates the long allele (+2) and underestimates the short allele (-3).

### 3.4 Multi-sample summary (HTT CAG)
Plain-English takeaway: Across samples with ground truth, WarpSTR is closest to the truth; STRique tends to overestimate the long allele and slightly overestimate the short allele.

Table 2 summarizes allele peaks for all samples with published ground truth. WarpSTR shows low error overall (mean absolute error: 0.38 repeats long, 0.75 short), but its outputs are missing for GM04723 in the current repo. STRique emits counts for all samples, but with higher error (mean absolute error: 1.89 long, 1.44 short) and a consistent long-allele overcount. DeepRepeat does not emit repeat counts in the current outputs; its GMM peak selection misses an evident short-allele mode in ND30016, ND30047, ND30422, and ND30626.

Table 2. Multi-sample HTT CAG allele comparison (samples with published ground truth)

| Sample | Truth (L/S) | WarpSTR (L/S) | ΔWarpSTR | STRique (L/S) | ΔSTRique |
|--------|-------------|---------------|----------|---------------|----------|
| GM04723 | 72/17 | N/A | N/A | 72/16 | 0/-1 |
| ND30015 | 41/20 | 42/21 | 1/1 | 43/22 | 2/2 |
| ND30016 | 41/21 | 41/21 | 0/0 | 43/22 | 2/1 |
| ND30047 | 41/18 | 41/19 | 0/1 | 43/20 | 2/2 |
| ND30422 | 40/18 | 40/18 | 0/0 | 41/19 | 1/1 |
| ND30626 | 41/21 | 41/17 | 0/-4 | 43/18 | 2/-3 |
| ND31551 | 39/18 | 41/18 | 2/0 | 43/19 | 4/1 |
| ND33392 | 57/17 | 57/17 | 0/0 | 59/18 | 2/1 |
| ND33947 | 40/18 | 40/18 | 0/0 | 42/19 | 2/1 |

Processed samples without published ground truth (ND29970, ND40534) are excluded from the table; their current peaks are WarpSTR 40/17 and 46/26, and STRique 42/18 and 48/27, respectively.

## 4. Comparison to Ground Truth
Table 1 summarizes the ND30626 case study, while Table 2 provides a multi-sample summary for all samples with published ground truth.

Table 1. ND30626 HTT CAG allele comparison (ground truth: 41 / 21 repeats)

| Method              | Allele peaks (native units) | Approx CAG repeats | Notes |
|---------------------|-----------------------------|--------------------|-------|
| Ground truth        | 41 / 21                     | 41 / 21            | Mutant sample |
| WarpSTR (DTW)       | 124 / 52                    | 41 / 17            | Short allele undercounted |
| WarpSTR (basecall)  | 120 / 51                    | 40 / 17            | Both alleles slightly low |
| DeepRepeat          | N/A                         | N/A                | No counts in current output |
| STRique             | 43 / 18                     | 43 / 18            | Counts are already in repeat units |

## 5. Discussion
Across samples with ground truth, WarpSTR is the most accurate overall (low mean absolute error for both alleles), but it still undercounts the short allele in ND30626. STRique emits repeat counts for every processed sample but shows higher error and a consistent long-allele overcount, suggesting a calibration or boundary bias. The short allele remains the most vulnerable to boundary errors across tools.

DeepRepeat logs show extremely frequent segmentation warnings, which are consistent with boundary ambiguity. If the repeat boundary is fuzzy, the model may exclude a few repeat units on short alleles, pushing counts downward. DeepRepeat's GMM peak selection also misses an evident short-allele mode in multiple samples (ND30016, ND30047, ND30422, ND30626), indicating that peak selection is a bottleneck even when a short mode is present in the allocation histogram.

## 6. Opportunities for Improvement
Plain-English takeaway: We need better boundaries and a clear conversion to repeat units, plus confidence scores that describe how sure we are.

1) Repeat-unit calibration: explicitly convert signal or basecall lengths into repeat counts with a validated scaling rule (e.g., bp/3 for CAG), then validate against ground truth.
2) Boundary detection: use joint signal + sequence context to identify repeat start/end more robustly, especially for short alleles.
3) Confidence-aware clustering: cluster per-read counts into alleles using uncertainty (DTW cost or model confidence), not just raw counts.
4) Strand and mapping robustness: improve handling of reverse-complement reads and off-by-few mapping errors.
5) Output completeness and QC: ensure DeepRepeat emits repeat counts by default and STRique outputs include standard flags or filters for zero/outlier counts.

## 7. Limitations
- Single-locus analysis (HTT CAG) limits generalization to other motifs.
- DeepRepeat outputs do not include repeat counts in this repo, preventing allele-level comparison.
- WarpSTR outputs are missing for GM04723 in the current repo snapshot.
- STRique counts include many zeros and extreme outliers, so peak estimates depend on filtering.
- Two processed samples (ND29970, ND40534) lack published ground truth.

## 8. Conclusion
Across processed samples with published ground truth, WarpSTR is closest to the truth (mean absolute error: 0.38 repeats long, 0.75 short), while STRique has higher error (1.89 long, 1.44 short) and a consistent long-allele overcount. The ND30626 case study mirrors this pattern: the short allele is underestimated across tools that emit counts. DeepRepeat still lacks repeat-count output, highlighting a workflow gap rather than a core algorithmic failure. The most impactful improvements are repeat-unit calibration, stronger boundary detection, and confidence-aware allele clustering. These changes should reduce short-allele undercounting and improve cross-tool comparability.

## Data and Output Pointers
- WarpSTR summary: `ont-str-runner/work/warpstr/ND30626/HTT_CAG/predictions/alleles.csv`
- WarpSTR per-read calls: `ont-str-runner/work/warpstr/ND30626/HTT_CAG/overview.csv`
- WarpSTR histogram: `ont-str-runner/work/warpstr/ND30626/HTT_CAG/summaries/alleles.svg`
- DeepRepeat log: `ont-str-runner/work/deeprepeat/ND30626/htt_retry.log`
- DeepRepeat read list: `ont-str-runner/work/deeprepeat/ND30626/ND30626.fs.more.retry`
- STRique counts: `ont-str-runner/work/strique/ND30626.txt`
- STRique log: `ont-str-runner/work/strique/ND30626.log`
- Multi-sample comparison table: `ont-str-runner/work/analysis/ground_truth_comparison.csv`
