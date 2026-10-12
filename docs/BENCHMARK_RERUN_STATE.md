# HTT CAG Benchmark Final State

Last updated: 2026-06-05 06:24 UTC.

## Plain-English Takeaway

The truth-sample benchmark is complete. All 9 published HTT CAG truth samples
have strict complete outputs from WarpSTR, DeepRepeat, and STRique.

Use the generated analysis files as the source of truth:

```text
ont-str-runner/work/analysis/ground_truth_comparison.csv
ont-str-runner/work/analysis/benchmark_report.md
ont-str-runner/work/analysis/benchmark_failures.tsv
```

## Completion Summary

- WarpSTR complete: 9/9
- DeepRepeat complete: 9/9
- STRique complete: 9/9
- Failure/incomplete records: 0

Final truth samples:

```text
GM04723 ND30015 ND30016 ND30047 ND30422 ND30626 ND31551 ND33392 ND33947
```

## Final Metrics

- WarpSTR long-allele MAE: 0.556 repeats
- WarpSTR short-allele MAE: 0.889 repeats
- STRique long-allele MAE: 1.889 repeats
- STRique short-allele MAE: 1.444 repeats
- DeepRepeat missed-short flags: 4/9

Plainly: WarpSTR is strongest overall, STRique completes all samples but
overestimates more often, and DeepRepeat has useful signal/allocation evidence
but weak GMM peak selection for short alleles.

## Unit Policy

- WarpSTR/basecall allele fields are sequence/base lengths and are converted to
  CAG repeats by dividing by 3 and rounding.
- STRique counts are treated as repeat counts directly after filtering zeros and
  extreme outliers.
- DeepRepeat GMM/allocr values are treated as repeat counts directly, but
  DeepRepeat is reported separately because it does not emit the same allele CSV
  as WarpSTR/STRique in this workflow.

## Recheck Commands

Regenerate the final comparison files:

```bash
python3 ont-str-runner/scripts/compare_ground_truth.py
```

Review the generated outputs:

```bash
cat ont-str-runner/work/analysis/benchmark_report.md
cat ont-str-runner/work/analysis/benchmark_failures.tsv
```

Compile the paper:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error paper/htt_cag_multisample_acm_bcb.tex
```

## Historical Note

The earlier tmux resume run `htt_benchmark_resume` with run id
`20260602T143618Z` has been superseded by the completed benchmark artifacts
above. Do not treat older partial WarpSTR, DeepRepeat, or STRique outputs as
final thesis metrics.
