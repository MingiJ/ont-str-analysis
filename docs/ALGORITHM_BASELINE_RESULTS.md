# Algorithm Baseline Results

Last updated: 2026-08-13.

## Plain-English Takeaway

The current algorithm baselines use the full nine-sample HTT CAG truth-window
set. These results supersede the older 266-row prototype results recorded in
`SESSION_STATE.md` and `docs/SESSION_PROGRESS_REPORT.md`.

Use these files as the source of truth for the current weak-label baseline
metrics:

```text
ont-str-runner/work/analysis/baseline_summary.tsv
ont-str-runner/work/analysis/baseline_predictions.tsv
ont-str-runner/work/analysis/neural_baseline_summary.tsv
ont-str-runner/work/analysis/neural_baseline_predictions.tsv
ont-str-runner/work/analysis/torch_rnn_summary.tsv
ont-str-runner/work/analysis/torch_rnn_predictions.tsv
ont-str-runner/work/analysis/torch_rnn.pt
ont-str-runner/work/analysis/neural_baseline_allele_summary_calibrated.tsv
ont-str-runner/work/analysis/neural_baseline_allele_calls_calibrated.tsv
ont-str-runner/work/analysis/loso_neural_summary.tsv
ont-str-runner/work/analysis/loso_neural_allele_calls.tsv
```

For the concise algorithm-vs-tool comparison, see:

```text
docs/ALGORITHM_BENCHMARK_COMPARISON.md
```

Reusable current caller:

```bash
.venv/bin/python src/algorithm/call_alleles.py
```

Current caller outputs:

```text
ont-str-runner/work/analysis/algorithm_predictions.tsv
ont-str-runner/work/analysis/algorithm_allele_calls.tsv
ont-str-runner/work/analysis/algorithm_summary.tsv
```

For unlabeled external samples, the caller now applies a MAPQ threshold of 20
when MAPQ metadata is available. If the two raw external clusters are separated
by fewer than five repeats, it reports an unresolved consensus instead of
inventing two calibrated alleles. The current expanded REL3 result is documented
in `docs/ALGORITHM_BENCHMARK_COMPARISON.md`.

## Dataset

- Signal rows: `30,356`
- Labeled rows: `30,356`
- Split: held-out sample
- Holdout sample: `ND33392`
- Training rows: `26,631`
- Test rows: `3,725`
- Labels: `long_like:16678`, `short_like:13678`

The labels are weak per-read labels derived from sample truth and tool-derived
read grouping. They are useful for prototype development, but they are not
manual per-read allele labels and should not be described as final thesis
ground truth.

## Ridge Regression Baseline

Command:

```bash
.venv/bin/python src/algorithm/baseline.py
```

Model summary:

- Feature set: signal summary statistics plus `128` temporal pooled bins.
- Training: deterministic ridge regression.
- Balanced training: enabled.

Current metrics:

- Train MAE: `7.722`
- Test MAE: `9.705`
- Test long-like MAE: `11.158`
- Test short-like MAE: `7.899`
- Held-out `ND33392` rows: `3,725`

Interpretation: this is the sanity-check baseline. It proves the extracted
signal windows and weak labels are trainable, but it is not competitive enough
to be the thesis model.

## NumPy MLP Baseline

Command:

```bash
.venv/bin/python src/algorithm/neural_baseline.py
```

Model summary:

- One-hidden-layer MLP.
- Input features: signal summary statistics plus `128` temporal pooled bins.
- Hidden dimension: `32`
- Epochs: `250`
- Optimizer: NumPy Adam implementation.
- Balanced training: enabled.

Current metrics:

- Train MAE: `5.134`
- Validation MAE at best epoch: `4.887`
- Test MAE: `7.405`
- Test long-like MAE: `9.355`
- Test short-like MAE: `4.982`
- Held-out `ND33392` rows: `3,725`

Interpretation: the NumPy MLP improves over ridge regression, especially for
short-like reads, but it is still a weak-label prototype. It compresses each
signal window into pooled features, so it likely loses boundary and periodicity
information that the planned sequence-aware RNN should use.

Sample-level allele evaluation:

```bash
.venv/bin/python src/algorithm/evaluate_allele_calls.py \
  --predictions ont-str-runner/work/analysis/neural_baseline_predictions.tsv \
  --calls ont-str-runner/work/analysis/neural_baseline_allele_calls_calibrated.tsv \
  --summary ont-str-runner/work/analysis/neural_baseline_allele_summary_calibrated.tsv \
  --calibration train-affine
```

Calibrated current-run allele metrics:

- All-sample allele MAE: `0.389`
- Held-out `ND33392` allele MAE: `0.500`
- Held-out `ND33392` call: `57/18` versus truth `57/17`

Important caveat: the all-sample metric includes training samples from this
single held-out-`ND33392` run. Use the leave-one-sample-out result below for the
current out-of-sample nine-sample estimate.

## PyTorch RNN Prototype

Command:

```bash
.venv/bin/python src/algorithm/torch_rnn.py --device cpu
```

Dependency note:

- PyTorch CPU build installed in `.venv`: `torch 2.12.0+cpu`
- CUDA availability: `False`

Model summary:

- Conv1d front-end plus bidirectional GRU.
- Hidden dimension: `32`
- Convolution channels: `8`
- Convolution strides: `32`, then `8`
- Epochs: `3`
- Batch size: `128`
- Balanced training: enabled.

Current metrics:

- Train MAE: `7.925`
- Validation MAE at best epoch: `7.333`
- Test MAE: `8.692`
- Test long-like MAE: `8.748`
- Test short-like MAE: `8.622`
- Held-out `ND33392` rows: `3,725`

Interpretation: the first CPU-feasible sequence model beats the ridge baseline
on total held-out MAE (`8.692` vs `9.705`) but does not yet beat the NumPy MLP
(`7.405`). Its long-like and short-like errors are more balanced than the MLP,
which suggests the sequence path is useful but needs more training/model tuning.

## Leave-One-Sample-Out MLP Allele Evaluation

Command:

```bash
.venv/bin/python src/algorithm/run_loso_neural.py
```

This trains the NumPy MLP nine times, each time holding out one truth sample,
then clusters per-read predictions into two sample alleles, applies the same
train-sample affine calibration used above, and applies a training-only
tail-span correction when a held-out long-signal span exceeds the training
range.

Current LOSO metrics:

- Samples: `9`
- Long-allele MAE: `0.333`
- Short-allele MAE: `0.778`
- Overall allele MAE: `0.556`

Benchmark comparison:

- WarpSTR overall allele MAE: about `0.722`
- STRique overall allele MAE: about `1.667`
- Current LOSO MLP overall allele MAE: `0.556`

Interpretation: the calibrated MLP plus tail-span correction now beats WarpSTR
and STRique in leave-one-sample-out evaluation. The tail correction is triggered
for `GM04723`, where the 72-repeat long allele is held out and the model has
not seen any training allele above 57 repeats. It changes the aggregate LOSO
call from `59/18` to `70/18` for truth `72/17`.

## Historical Note

Older notes mention a 266-row signal-window prototype with ridge test MAE
`6.937` and NumPy MLP test MAE `5.746`. Those numbers came from an earlier
small dataset containing `ND33392_WARPSTR_SMALL` and `REL3_WARPSTR_OK`. They
are retained only as historical debugging context.

For current thesis algorithm development, use the nine-sample `30,356`-row
results above.
