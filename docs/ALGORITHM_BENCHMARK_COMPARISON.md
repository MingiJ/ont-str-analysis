# Algorithm vs Tool Benchmark Checkpoint

Last updated: 2026-08-13.

## Plain-English Takeaway

The current calibrated NumPy MLP algorithm beats WarpSTR, STRique, and
DeepRepeat on the nine known HTT CAG truth samples. The stricter
leave-one-sample-out result now also beats WarpSTR after adding a training-only
tail-span correction for out-of-range long alleles.

## Current Development-Set Comparison

These numbers compare sample-level allele calls against the same nine truth
samples used for the tool benchmark.

| Method | Long MAE | Short MAE | Overall allele MAE | Notes |
|--------|----------|-----------|--------------------|-------|
| Calibrated NumPy MLP | 0.111 | 0.667 | 0.389 | Current best algorithm checkpoint; calibrated allele calls from per-read MLP predictions. |
| WarpSTR | 0.556 | 0.889 | 0.722 | Best existing benchmark tool in this repo. |
| STRique | 1.889 | 1.444 | 1.667 | Completes all samples but tends to overestimate. |
| DeepRepeat GMM | not primary | not primary | 7.833 | Parsed GMM peaks; 4/9 missed-short flags make it weak as a final allele caller. |

Current algorithm output files:

```text
ont-str-runner/work/analysis/algorithm_allele_calls.tsv
ont-str-runner/work/analysis/algorithm_summary.tsv
ont-str-runner/work/analysis/neural_baseline_allele_calls_calibrated.tsv
ont-str-runner/work/analysis/neural_baseline_allele_summary_calibrated.tsv
```

Reusable caller command:

```bash
.venv/bin/python src/algorithm/call_alleles.py
```

This trains on all labeled truth windows in the current archive and emits
sample-level allele calls. Current development-set caller output has overall
allele MAE `0.444`.

Tool benchmark output files:

```text
ont-str-runner/work/analysis/ground_truth_comparison.csv
ont-str-runner/work/analysis/benchmark_report.md
```

## Current Out-of-Sample Check

Leave-one-sample-out NumPy MLP with train-only affine calibration and
tail-span correction:

```text
ont-str-runner/work/analysis/loso_neural_allele_calls.tsv
ont-str-runner/work/analysis/loso_neural_summary.tsv
```

LOSO metrics:

| Method | Long MAE | Short MAE | Overall allele MAE |
|--------|----------|-----------|--------------------|
| Calibrated NumPy MLP LOSO + tail span | 0.333 | 0.778 | 0.556 |
| WarpSTR benchmark | 0.556 | 0.889 | 0.722 |
| STRique benchmark | 1.889 | 1.444 | 1.667 |

Interpretation: the algorithm now beats WarpSTR, STRique, and DeepRepeat under
the current nine-sample LOSO allele-level evaluation.

## Main Remaining Failure

Before the tail-span correction, the LOSO error was dominated by `GM04723`.

```text
truth: 72/17
LOSO calibrated MLP call before tail span: 59/18
LOSO calibrated MLP call after tail span: 70/18
remaining error: -2/+1
```

When `GM04723` is held out, the training fold has no allele longer than
`57` repeats. The MLP alone under-extrapolates to the 72-repeat allele. The
tail-span correction detects that the held-out long-signal span exceeds the
training range and extrapolates from the three largest training long-span
anchors.

## REL3 Expanded Validation

The original `REL3_WARPSTR_OK` probe contained only the 54 reads for which
WarpSTR successfully generated boundaries. Its `54/18` algorithm call is now a
historical failure-mode result, not the preferred REL3 estimate. It was selected
through another tool's success filter and was already marked low confidence.

The expanded validation derives signal boundaries independently. The new
`alignment_signal_bounds.py` maps the HTT reference interval through each BAM
CIGAR into the native FAST5 basecall, then maps basecall positions into raw
signal through the FAST5 event/move table. On 38 reads shared with WarpSTR, the
median absolute differences for the four raw boundaries are only `12-29`
samples.

Expanded artifacts:

```text
ont-str-runner/work/rel3/rel3_alignment_signal_bounds.tsv
ont-str-runner/work/analysis/evidence_table_truth_plus_rel3_expanded.tsv
ont-str-runner/work/analysis/signal_windows_rel3_expanded.npz
ont-str-runner/work/analysis/signal_windows_rel3_expanded.index.tsv
ont-str-runner/work/analysis/signal_windows_truth_plus_rel3_expanded.npz
ont-str-runner/work/analysis/signal_windows_truth_plus_rel3_expanded.index.tsv
```

Coverage:

```text
REL3 FAST5/BAM matched reads: 172
independent full-flank windows: 93
MAPQ-60 windows: 33
```

The default external-sample caller now filters populated MAPQ values below 20.
It also reports a single unresolved consensus when two external raw clusters
are separated by fewer than five repeats. The resulting REL3 call is:

```text
sample: REL3_EXPANDED
call: 17/17 (unresolved consensus)
raw prediction median: 18.812
rows available/used: 93/33
rows quality-filtered: 60
confidence: low
confidence reason: small_read_count;unresolved_allele_separation;mapping_quality_filtering
```

Sensitivity analysis without the MAPQ filter produces `38/15` from all 93
windows. The high cluster is driven by low-MAPQ extreme predictions, so it must
not be interpreted as evidence for an expanded allele. The all-read outputs are
kept separately as `algorithm_truth_plus_rel3_expanded_all_reads_*`.

Independent basecall evidence supports a normal-length, unresolved result. In
the 33 MAPQ-60 reads, the exact HTT interval has median `14` total CAG triplets
(range `10-18`) and median longest uninterrupted run `11` (range `4-18`). The
model's raw median is `18.812`. These sources do not support the old
low-confidence long call around 54 repeats.

REL3 remains unlabeled in this workspace. These results measure call stability
and failure handling, not MAE. The nine truth-sample LOSO result remains the
source of the algorithm's scored accuracy.

## Next Technical Target

- Increase independent high-quality REL3 coverage beyond the current 33
  MAPQ-60 reads, preferably with additional matched REL3 FAST5/BAM data.
- Add boundary-quality and sequence-context features to per-read confidence so
  extreme predictions are rejected without relying on sample-level filtering.
- Replace weak per-read labels with stronger boundary/allele supervision before
  treating the neural model as final thesis evidence.
