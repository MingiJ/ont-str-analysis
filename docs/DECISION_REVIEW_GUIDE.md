# How to Judge the HTT Raw-Signal Caller

This guide is the minimum background needed to audit design decisions and
results confidently. You do not need to become a nanopore-instrument engineer
or a deep-learning specialist. You do need to be able to follow the chain from
biological truth to raw signal, model input, validation split, allele call, and
reported metric.

## 1. Biological target and units

Humans are diploid, so an HTT sample normally has two CAG-repeat counts, one
per chromosome. The pair is unordered: `17/57` and `57/17` are the same
genotype. Expanded alleles cause the difficult cases and are not represented
evenly in the current nine samples.

Always check the unit before comparing outputs. A value may be:

- CAG repeat count;
- repeat-region base pairs, which is approximately three times CAG count;
- raw electrical samples; or
- a tool-specific score that is not a count.

For this project, final allele error is reported in CAG repeats. WarpSTR fields
that contain sequence/base length must be converted to CAG counts; STRique and
DeepRepeat count-like outputs use different conventions. A fair table converts
each tool once and documents the conversion.

## 2. Nanopore signal and coordinate mapping

Oxford Nanopore sequencing measures ionic current many times while DNA moves
through a pore. One DNA base therefore spans a variable number of raw samples.
The raw signal does not have a universal "samples per CAG" scale because motor
speed, pore state, strand, and basecalling chemistry vary by read.

Four coordinate systems matter:

1. reference coordinates on chromosome 4;
2. query/basecall coordinates in the read;
3. event or move-table coordinates linking called bases to signal; and
4. raw FAST5 sample indices.

The independent mapper follows BAM CIGAR operations from reference to query,
then native FAST5 events from query to raw samples. Boundary errors directly
change apparent repeat duration, so review MAPQ, supplementary/secondary
alignments, strand, clipping, raw samples per base in both flanks, and whether
more than one alignment spans the locus.

The key independence question is: **Did the proposed method obtain its input
window from the competitor it is supposed to beat?** The current bounded
archive answers no: it uses BAM/CIGAR/native-FAST5 mapping and only compares to
WarpSTR afterward for validation.

## 3. What the physics baselines mean

If a read moves through the pore at roughly stable speed, a longer repeat
usually occupies more raw samples. The duration baseline therefore:

1. finds two robust duration clusters within each sample without read labels;
2. pairs the shorter and longer clusters with the two sorted training truths;
3. fits an affine duration-to-CAG calibration on training samples only; and
4. applies that calibration to the held-out sample's two clusters.

This is a strong sanity check. A neural model that sees the same window should
beat this baseline on held-out validation genotypes before its residual is
trusted. The current independent repeat-duration baseline has LOSO allele MAE
`1.638`; the current RNN residual does not beat it.

The autocorrelation probe asks whether local signal repetition can correct for
read speed. Its fixed development score is `1.414`, but that feature was chosen
after inspecting these samples. The nested, protocol-correct feature selector
scores `1.725`. Judge the fixed score as a hypothesis requiring new data, not
as a benchmark victory.

## 4. Weak supervision and latent assignment

There is no objective allele label for every read. Only each sample's two
Sanger-derived allele counts are trusted. The proposed weak supervision uses
that unordered sample-level pair and treats each read's allele membership as a
latent variable.

This distinction is central:

- valid supervision: sample `A` has unordered truth `(17, 57)`;
- invalid shortcut: WarpSTR says this read is `long_like`, therefore train the
  new model on 57 for that read.

The shortcut can teach the new model to reproduce WarpSTR's choices and then
make an apparently independent comparison meaningless. Tests therefore verify
that changing `group_label` does not change training or baseline predictions.

## 5. Validation, leakage, and the small-sample problem

There are only nine labelled samples, not thousands. Reads from the same sample
share genotype, preparation, flow-cell, and technical effects, so a random
read split is leakage-prone and greatly overstates generalization.

The correct unit of splitting is the sample:

- outer test sample: untouched when producing that fold's prediction;
- inner validation sample(s): model/epoch/feature choice;
- remaining samples: fitting parameters.

Leave-one-sample-out (LOSO) reports one outer result per sample. Nested LOSO is
required whenever an epoch, threshold, architecture, or feature is selected.
If a design was invented after looking at all nine LOSO outcomes, its score is
development evidence even if the final code now implements clean folds. New
labelled samples are needed for confirmation.

## 6. Metrics and abstention

For truth pair `(s, l)` and prediction `(s_hat, l_hat)`, allele MAE is:

```text
(abs(s_hat - s) + abs(l_hat - l)) / 2
```

Aggregate LOSO MAE averages that value across samples. With only nine samples,
also inspect every fold: a single expanded allele can dominate the mean.

An uncertainty-aware caller may abstain. Then three quantities must stay
separate:

- coverage: fraction of samples resolved;
- conditional resolved MAE: error only where the caller did not abstain; and
- candidate-mode MAE: diagnostic error if candidate clusters are forced.

A caller is not good merely because it has low conditional MAE after rejecting
the hard expanded samples. Coverage and error must be reported together.
`mixture_confidence` measures within-sample separation; it is not the
probability that the genotype is correct.

## 7. How to review any proposed change

Ask these questions in order:

1. **Truth:** What is trusted, in what unit, and where did it come from?
2. **Independence:** Did any competitor provide windows, labels, counts, or
   filtering decisions used by the new method?
3. **Split:** Are all reads from an outer sample absent from fitting and model
   selection?
4. **Selection:** Was this feature, epoch, or threshold chosen using only inner
   training/validation samples?
5. **Baseline:** Does it beat raw mapped-repeat duration under the identical
   folds and read set?
6. **Coverage:** Did accuracy improve because difficult calls were rejected?
7. **Per-fold behavior:** Does the improvement hold for expanded and normal
   alleles, or depend on one sample?
8. **Reproducibility:** Is there a command, frozen input manifest, output table,
   test for leakage, and documented random seed?
9. **Novelty:** Is the claim about the precise combination of supervision,
   model, uncertainty, and evaluation rather than the already-published broad
   idea of raw-signal STR calling?
10. **Status language:** Is the number clearly marked as exploratory,
    development, or confirmatory?

If any of questions 1-4 fails, do not interpret the final MAE. If 1-4 passes
but 5-7 fails, the experiment is a valid negative result. That is what happened
with the current Conv-BiRNN residual.

## 8. Current results and their proper interpretation

| Result | Allele MAE | Status | Correct conclusion |
|---|---:|---|---|
| Frozen engineered MLP | 0.556 | Existing benchmark | Best current score, but built from the earlier engineered pipeline |
| WarpSTR | 0.722 | Comparator | Strong published-tool comparator after correct unit conversion |
| Independent repeat duration | 1.638 | Reproducible development baseline | Useful physical signal; no uncertainty model |
| STRique | 1.667 | Comparator | Slightly worse than duration on these nine samples |
| Fixed ACF-normalized duration | 1.414 | Exploratory/post-development | Freeze and confirm externally; do not claim a win |
| Nested duration/ACF selection | 1.725 | Protocol-correct development diagnostic | Feature choice did not improve the baseline |
| Corrected weak RNN candidate modes | 5.775 | Negative development result | Neural residual is harmful; do not scale it up |
| Coriell fixed ACF | 2.894 | First external gate, 2 samples | Weak heterogeneous support; now exposed |
| MASTR fixed ACF | 3.186 | Frozen confirmation, 4 samples | Failed pooled <=3 and expanded-long <=5 gates |
| MASTR duration | 4.622 | Diagnostic only | Worse than ACF; cannot alter the frozen decision |

The most important reviewer habit is to value a clean negative result more than
an impressive number obtained after leakage or repeated tuning. The present
evidence supports the independent mapper and duration physics. It does not yet
support the neural architecture or a confirmatory periodicity claim.
The completed MASTR gate strengthens that conclusion: the ACF proxy transfers
better than duration, but it missed the pooled threshold by `0.186` repeats
and the expanded-72 long-allele threshold by `0.781` repeats. Those misses are
small enough to motivate a genuinely new method, but not small enough to call
the frozen experiment a pass.

## 9. Suggested learning sequence

To become comfortable reviewing the project, study in this order:

1. HTT CAG genetics, diploid genotypes, and repeat-count versus base-pair units.
2. SAM/BAM fields and CIGAR operations, especially clipping and supplementary
   alignments.
3. Nanopore FAST5 raw signal, event/move tables, dwell time, and strand
   orientation.
4. Robust clustering, affine regression, MAE, and Gaussian mixture models.
5. Train/validation/test separation, grouped cross-validation, nested LOSO,
   and data leakage.
6. Weak supervision, latent variables, heteroscedastic regression, calibration,
   and selective prediction/abstention.
7. The exact algorithms in NanoSatellite, STRique, DeepRepeat, and WarpSTR so
   novelty and comparator fairness can be assessed precisely.

Use `docs/ALGORITHM_EXPLANATION_FOR_REFERENCE.md` for the tool-by-tool
plain-English explanation and `docs/PROPOSED_RNN_ALGORITHM_PLAN.md` for the
current research claim, protocol, and gate results.
