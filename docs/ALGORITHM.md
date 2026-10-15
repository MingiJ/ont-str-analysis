# Algorithm: Raw-Signal HTT CAG Genotype Caller

This document describes the method implemented in `src/algorithm/`. It is the
single reference for what the caller does, what is and is not claimed, and how
to reproduce every reported number.

Thesis: *Direct Estimation of Short Tandem Repeat Expansions from Raw Nanopore
Signals.*

## 1. Objective

Estimate the **unordered diploid HTT CAG genotype** (a pair of repeat counts,
e.g. `17/57`) for a sample, directly from Oxford Nanopore **raw signal**, and
report a calibrated uncertainty so the caller can **abstain** when the reads do
not support a reliable two-allele call.

The design constraint that shapes everything below: the only trusted labels are
**sample-level** (one unordered pair per person, from Sanger sizing). There is
no trusted per-read label, and the method never uses one.

## 2. Pipeline overview

```
raw signal (FAST5/POD5)  +  aligned reads (BAM/CRAM)
          |
   (1) locate the repeat in each read's signal   <- no competitor tool used
          |
   (2) measure repeat DURATION (number of signal samples)
          |
   (3) calibrate duration -> repeat count  (count = a + b * duration)
          |
   (4) aggregate per-read counts into two alleles (unordered genotype)
          |
   (5) decide: emit genotype + uncertainty, or abstain
```

## 3. Inputs

- **Raw signal** for reads overlapping the HTT locus (`chr4:3074876-3074933`).
- **Aligned reads** (BAM/CRAM) giving each read's position, CIGAR, and MAPQ.
- **Sample-level truth** (Sanger counts) — used only for calibration and
  evaluation, never as a per-read label.

## 4. Locating the repeat without a competitor tool (the key step)

A read's raw signal and the reference genome do not share a coordinate system.
The read's own bases are the only thing that lives in both worlds, so the repeat
window is found by **chaining three coordinate systems**:

```
reference coordinates  --(BAM CIGAR)-->  read/base coordinates  --(move table)-->  signal-sample coordinates
```

- **Reference -> read** uses the alignment CIGAR to translate the reference
  repeat interval into base positions within this read.
- **Read -> signal** uses the basecaller **move table** (the per-base tally of
  how many signal samples each base consumed) to translate those base positions
  into start/end indices in the raw signal.

This mapper (`alignment_signal_bounds.py`, `dorado_move_signal_bounds.py`) is
**independent of WarpSTR, STRique, and DeepRepeat**: it does not use any
competitor's signal coordinates, read selection, or per-read allele grouping.
Reads below MAPQ 60 and reads failing a raw-per-base consistency check are
dropped (1,135 of 1,152 windows retained on the nine development samples; 1.5%
rejected).

## 5. Core feature and calibration

- **Feature: repeat duration** = (repeat_end - repeat_start) in signal samples.
  Longer DNA spends more time in the pore, so duration scales with repeat count.
- **Calibration ("the ruler"):** an affine fit `count = a + b * duration`,
  fitted **only on training samples**. On the R9.4.1 development data the slope
  corresponds to roughly 33 signal samples per CAG. The ruler is not perfectly
  constant (it varies ~29-38 and drifts by allele), which is the main source of
  residual error.

> **Chemistry note.** The duration -> count mechanism is general, but the
> calibration constant is **chemistry-specific**. R10.4.1 translocates DNA at a
> different speed than R9.4.1, so the ruler must be **re-fitted** on R10 data
> rather than reused. The mechanism transfers; the constant does not.

## 6. From per-read counts to a sample genotype

Each read yields one estimated count. For a sample these cluster into (up to)
two modes — one per allele. Because the genotype is **unordered and diploid**,
the method:

- treats "which allele did this read come from?" as a **latent variable** it
  infers, rather than a given label;
- fits a two-component mixture to the per-read counts, with gates on separation,
  minor-component support, and model fit (BIC);
- emits a genotype only when those gates pass; otherwise reports an
  **unresolved** consensus (abstention) rather than inventing two alleles.

The research model (`weak_supervised_rnn.py`) extends this with a sequence
encoder (Conv1d + bidirectional GRU/LSTM) that learns a **residual** around the
train-only duration prior, plus a heteroscedastic (per-read) uncertainty head.

## 7. What is and is not claimed as novel

Raw-signal, neural, and sample-level STR calling each already exist
(NanoSatellite, STRique, DeepRepeat, WarpSTR). This work does **not** claim to
be the first of any of those. The defensible novelty is the **specific
combination**:

1. supervision by an **unordered sample-level** genotype, not tool-derived
   per-read labels;
2. **latent per-read allele assignment** inside the learning objective;
3. a sequence-aware raw-signal **residual** around a train-only duration prior;
4. **heteroscedastic per-read uncertainty** and an explicitly **abstaining**
   caller; and
5. **nested, sample-disjoint** validation and leave-one-sample-out evaluation.

## 8. Evaluation protocol

- **Nested leave-one-sample-out (LOSO):** hold out an entire person; train and
  make every modelling choice on the other eight; predict the held-out person;
  repeat for all nine. Reads from one person are correlated, so a random
  *read* split would leak and inflate the score.
- **Leakage discipline:** no competitor boundaries as input; no tuning on
  held-out truth; feature/threshold choices made on inner training folds only.
- **Report coverage and conditional error together.** Low error achieved by
  abstaining on the hard (expanded) alleles is not a success.

## 9. Results (nine R9.4.1 samples, allele MAE in CAG repeats)

| Method | Allele MAE | Notes |
|---|---:|---|
| **Independent duration baseline** | **1.638** | Headline. No competitor input; pure physics on independently-mapped boundaries. Reproduced by `evaluate_repeat_duration_loso.py`. |
| WarpSTR | 0.722 | Comparator (R9 tool). |
| DeepRepeat | 1.556 | Comparator; no clean per-read count. |
| STRique | 1.667 | Comparator (R9 tool). |
| Engineered MLP | 0.556 | **Not an independent result** — its windows derive from WarpSTR boundaries, so it is excluded from the headline claim. |
| Weak-supervised RNN | 5.775 | Negative result: the neural residual currently hurts relative to the duration baseline. |
| Length-dependent ruler (nested) | 1.69 | Negative result: data coverage, not ruler shape, is the limiting factor. |

Honest summary: the independent duration baseline (**1.638**) narrowly beats
STRique but not WarpSTR; the neural residual is a documented **negative
result**; and the bottleneck is **expanded-allele data coverage**, confirmed
experimentally (the one 72-repeat sample is always extrapolated beyond the
training maximum of 57).

External transfer tests (different chemistry/protocol) are frozen and reported
in `docs/PROPOSED_RNN_ALGORITHM_PLAN.md`: two Coriell HD samples (pooled
duration MAE 3.103) and the MASTR-seq engineered cohort (pooled MAE 3.186,
which failed its pre-declared accuracy gate). Both are transfer checks, not
clinical validation.

## 10. Reproduce

```bash
# headline independent duration baseline (nested LOSO)
.venv/bin/python src/algorithm/evaluate_repeat_duration_loso.py

# weak-supervised RNN, nested LOSO
.venv/bin/python src/algorithm/run_weak_supervised_loso.py \
  --signal-archive ont-str-runner/work/analysis/signal_repeat_windows_independent_qc_dev.npz \
  --index ont-str-runner/work/analysis/signal_repeat_windows_independent_qc_dev.index.tsv \
  --output-dir ont-str-runner/work/analysis/weak_supervised_rnn_repeat_valselect_loso_dev

# comparison figures (per-sample error vs length; per-read distributions)
.venv/bin/python src/algorithm/make_comparison_figures.py

# unit tests
.venv/bin/python -m unittest discover -s src/algorithm -p 'test_*.py'
```

See also `docs/PROPOSED_RNN_ALGORITHM_PLAN.md` (full method and prior-art
audit), `docs/ALGORITHM_BENCHMARK_COMPARISON.md`, and `docs/REPRODUCIBILITY.md`.
