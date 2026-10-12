# Weakly Supervised Raw-Signal HTT CAG Caller

## Research objective

Estimate the unordered diploid HTT CAG genotype directly from nanopore raw
signal while avoiding externally generated per-read allele labels. The method
must emit calibrated uncertainty and abstain when the reads do not support a
reliable two-allele call.

This is the defensible research direction. “A deep network for STR counting
from nanopore signal” is not itself novel.

## Prior-art audit (2026-08-14)

The literature search found substantial overlap with the broad thesis title:

- [NanoSatellite](https://pmc.ncbi.nlm.nih.gov/articles/PMC6857246/) already
  estimates tandem-repeat length directly from raw squiggles with DTW.
- [STRique](https://www.nature.com/articles/s41587-019-0293-x) localizes repeat
  boundaries with raw-signal alignment and counts repeats with an HMM.
- [DeepRepeat](https://link.springer.com/article/10.1186/s13059-022-02670-6)
  converts nanopore signal into images and uses a deep CNN for STR detection
  and quantification. It evaluates the same 11 HTT Huntington cell lines; the
  current nine labelled samples are a subset of that published dataset.
- [WarpSTR](https://pmc.ncbi.nlm.nih.gov/articles/PMC10307940/) aligns raw
  signal to a finite-state repeat model using a DTW-like algorithm and performs
  sample-level GMM genotyping.
- [Stevanovski et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC8896783/)
  already demonstrate targeted ReadUntil sequencing and clinical diagnosis of
  many repeat-expansion disorders, including HTT, with basecalled alignment,
  assembly, methylation, and repeat-genotyping analyses. Their public raw data
  are an external validation source, not a novel dataset created here.
- [SUMMER](https://pmc.ncbi.nlm.nih.gov/articles/PMC11750885/) independently
  reuses `SRP349335` and calls HTT alleles in NA13509 and NA13512 with Straglr
  from basecalled reads. Repeating a basecalled FASTQ/Straglr analysis would
  therefore add no novelty; the current gate instead tests the already-frozen
  independent raw-signal duration and ACF proxies.

No claim should therefore say that this is the first raw-signal, neural, or
sample-level STR caller. A focused novelty claim is potentially supportable
only for the complete combination below, subject to a wider formal literature
review before publication:

1. supervision by an unordered sample-level diploid genotype rather than
   baseline-derived per-read allele labels;
2. latent per-read allele assignment inside the learning objective;
3. sequence-aware raw-signal residual regression around a train-only physical
   duration prior;
4. heteroscedastic per-read uncertainty and an explicitly abstaining genotype
   caller; and
5. nested sample-disjoint validation and leave-one-sample-out evaluation.

## Implemented experimental method

`src/algorithm/weak_supervised_rnn.py` implements the current experiment.

Inputs:

- normalized raw current from an independently mapped repeat window per read;
- valid mapped repeat duration;
- sample identity for constructing bags; and
- the sample's unordered pair of Sanger-derived allele counts.

Training deliberately does not use `group_label`, `target`, WarpSTR read
counts, STRique read counts, or DeepRepeat allocations.

Model:

- a train-only affine duration prior fitted from two unsupervised duration
  centres per training sample;
- two 1D convolution layers;
- a bidirectional GRU or LSTM;
- a residual repeat-count head added to the duration prior; and
- a log-variance head for aleatoric uncertainty.

Objective:

- allele order is sorted internally, so swapping the truth pair is invariant;
- constrained generalized-EM assignment gives both latent alleles minimum
  support and uses duration only as a monotonic ordering prior;
- balanced component loss prevents the higher-coverage allele dominating;
- beta-NLL weighting plus an auxiliary Huber mean loss limits variance-driven
  mean underfitting; and
- model selection uses robust validation-sample genotype MAE, with the
  untrained duration prior (epoch 0) eligible; variance scaling uses the same
  distinct validation sample after selection.

Calling:

- a heteroscedastic one-versus-two Gaussian mixture comparison;
- BIC, separation, and minor-component support gates;
- a consensus plus `resolved=False` when evidence is insufficient; and
- `mixture_confidence`, which describes within-sample separation only and is
  not a calibrated probability that the genotype is accurate.

## Evaluation protocol

The primary protocol is nested leave-one-sample-out (LOSO):

```bash
.venv/bin/python src/algorithm/run_weak_supervised_loso.py \
  --signal-archive ont-str-runner/work/analysis/signal_repeat_windows_independent_qc_dev.npz \
  --index ont-str-runner/work/analysis/signal_repeat_windows_independent_qc_dev.index.tsv \
  --max-rows-per-sample 0 \
  --output-dir ont-str-runner/work/analysis/weak_supervised_rnn_repeat_valselect_loso_dev
```

For quick mechanics checks, the driver defaults to a deterministic 64-read cap.
That capped run is development evidence only. Each fold writes predictions,
calls, a checkpoint, and a summary. The aggregate reports both:

- resolved-call MAE, conditional on non-abstention; and
- candidate-mode MAE across every fold, explicitly not a clinical call metric.

Report coverage and conditional MAE together. Never convert an unresolved
consensus into an apparent diploid accuracy score.

The comparator table remains WarpSTR, DeepRepeat, STRique, the engineered MLP,
and the duration-only ablation, all on identical truth samples and allele units.

## Current empirical status

The original soft weak-supervision experiment collapsed near the midpoint of
the two allele labels. Constrained latent assignment separated short and long
reads but compressed expanded counts toward approximately 40 repeats.

A bounded 64-read/sample development run with the train-only duration prior,
20 epochs, and `ND33392` as the already-exposed test sample produced:

```text
ND33392 truth:              57/17
hybrid candidate modes:    61.55/24.35
hybrid forced-call MAE:    6.0 (caller threshold 0.10; now considered unsafe)
safer threshold 0.20:      unresolved
duration-only LOSO MAE:    3.597 across nine samples
```

The auxiliary mean-loss variant also abstained and remained biased. These are
negative development results, not final benchmark claims. In particular,
`ND33392` has now influenced design decisions and is no longer an untouched
confirmatory holdout; only complete nested LOSO results can support comparison.

The fixed nine-fold, 64-read/sample nested LOSO screen is now complete:

```text
folds:                       9
resolved folds:              0
resolved-call coverage:      0.000
all-fold candidate-mode MAE: 14.784
```

Candidate-mode MAE is included only to diagnose the unresolved mixture fits;
it is not a clinical call metric. This result fails the development gate. A
full 30,356-read run is not justified until the architecture changes, because
the capped folds show a systematic objective/caller failure rather than noisy
fold-to-fold behavior.

The current frozen engineered NumPy MLP remains substantially stronger on this
nine-sample dataset (LOSO allele MAE 0.556). The new RNN must not replace it in
the benchmark table until it improves under the same sample-disjoint protocol.

### Independent-boundary development gate

The BAM/CIGAR/native-FAST5 mapper is now generalized across all nine truth
samples. It does not use WarpSTR signal coordinates, WarpSTR read success, or
per-read allele groups. The bounded manifest contains 1,152 reads (128 per
sample), all at MAPQ 60. Independent raw-per-base consistency checks retain
1,135 reads and reject 17 (1.5%). The repeat-focused signal archive contains
all 1,135 accepted windows with no truncation.

The independent physics ablations are:

```text
full-flank window duration LOSO MAE: 4.776
mapped repeat duration LOSO MAE:     1.638
flank-rate-normalized duration MAE:  1.689
mapped query span LOSO MAE:          2.912
```

The `1.638` result is reproduced by
`src/algorithm/evaluate_repeat_duration_loso.py`. Each outer fold estimates two
unlabeled duration centres in the held-out sample, while its affine
duration-to-count calibration is fitted only on the other eight samples. No
held-out truth, tool-derived read count, or `group_label` enters prediction.
This forced duration ablation narrowly beats STRique (`1.667`) on the current
nine samples, but not WarpSTR (`0.722`) or the engineered MLP (`0.556`). It has
no uncertainty or abstention and is not a deployable caller.

The weak RNN on independent full-flank windows resolved only `1/9` folds and
had diagnostic candidate MAE `10.951`. Repeat-focused windows initially looked
better, but validation likelihood selected epochs with worsening validation
genotype error. The corrected selector therefore admits epoch 0 and minimizes
validation-sample allele MAE. Under this corrected nested protocol:

```text
folds selecting epoch 0:       7/9
folds selecting trained model: 2/9
resolved folds:                5/9
candidate-mode MAE:            5.775
conditional resolved MAE:      4.400
```

The neural residual is harmful relative to the independent duration baseline.
This is a useful negative result: the selection protocol now detects and
rejects most degradation instead of rewarding lower likelihood alone.

A bounded repeat-local periodicity probe was then added in
`src/algorithm/evaluate_repeat_periodicity_loso.py`. It divides mapped repeat
span by an unsupervised autocorrelation peak near the flank-implied CAG dwell
period. The fixed proxy gives LOSO MAE `1.414`, but this feature and its
parameters were developed after inspecting the same nine samples, so that
number is exploratory rather than confirmatory. A protocol-correct nested
selector chooses between raw duration and autocorrelation using only inner
training folds. It selects autocorrelation in 8/9 outer folds but has aggregate
outer MAE `1.725`, versus `1.638` for the pre-existing duration baseline. The
median selected period is 35 raw samples and median ACF strength is only 0.113,
so it must not yet be described as a reliable learned CAG periodicity signal.

### Frozen external-confirmation gate

An additional primary-data search identified two public, independently
genotyped Coriell Huntington samples in `SRP349335`: NA13509 (`15/70`) and
NA13512 (`16/44`). NCBI's full SRA XML maps these identities to exact FASTQ,
FAST5, and SLOW5 runs despite anonymized archive aliases. The acquisition is
frozen in `ont-str-runner/configs/external_confirmation_samples.tsv`.

The confirmation protocol is deliberately split:

1. `evaluate_external_confirmation.py predict` rejects external metadata with
   nonblank truth, fits duration and fixed ACF calibrations on all nine
   development samples, and writes sealed predictions;
2. no feature, lag range, threshold, or calibration may change after those
   predictions exist; and
3. only `evaluate_external_confirmation.py score` opens the Coriell truth
   manifest and reports per-sample plus pooled allele MAE.

This dataset is technically different from the older development cohort
(R9.4.1, Guppy-era ReadUntil/ReadFish targeted sequencing), which makes it a
useful chemistry/protocol generalization test. It is small and was previously
analyzed by basecalled-read methods, so a positive result supports external
confirmation of the raw-signal proxy, not a broad claim of clinical validity.

The frozen gate is now complete. Seventeen truth-free QC-passing reads were
available: five for NA13509 and twelve for NA13512. Prediction inputs and code
were hashed, both samples were predicted in one sealed file, and only then was
the Coriell manifest opened by the score subcommand:

```text
sample    feature                  prediction       truth   allele MAE
NA13509   duration                 11.909 / 71.449   15/70        2.270
NA13512   duration                 12.317 / 39.810   16/44        3.936
NA13509   ACF-period-normalized    12.435 / 61.533   15/70        5.516
NA13512   ACF-period-normalized    16.128 / 44.414   16/44        0.271

pooled duration allele MAE: 3.103
pooled fixed-ACF allele MAE: 2.894
```

The fixed ACF proxy improves pooled MAE by only `0.210`, and the direction
reverses across the two samples. This is weak, heterogeneous external support,
not a decisive confirmation of ACF superiority. It does show that both frozen
raw-signal proxies transfer across chemistry and boundary-generation protocol
well enough to recover the broad diploid structure. These two biological
samples are now exposed and must not be used for feature tuning.

## Main limitation and next gate

The independent-boundary gate is complete, so WarpSTR-boundary inheritance is
no longer the immediate blocker. The remaining evidence says that repeat
duration contains useful physical signal, but the current Conv-BiRNN objective
learns a residual that reduces genotype accuracy. Nine samples also provide
very little sample-level supervision for a neural sequence encoder.

The next research gate is therefore:

1. freeze the independent mapped-repeat duration LOSO result (`1.638`) and the
   corrected RNN run as positive-physics and negative-neural ablations;
2. do not tune individual outer folds or reuse outer truth for model choice;
3. freeze the external result above and seek additional independently
   genotyped biological samples; the reserved NA13509 technical replicate may
   test reproducibility but must not be counted as another independent sample;
4. require the next model to beat the epoch-0 duration prior on validation
   genotype MAE before it may affect an outer test prediction; and
5. predeclare the next comparison and uncertainty analysis before opening any
   new truth, then run it with the complete ablation table. NCBI still returns
   no runs for `GM04767` or `ND31038`, so those names must not be assigned to
   unrelated or unlabeled archives.

Success requires both competitive error and useful coverage. A method that
achieves low error only by abstaining on expanded alleles is not successful.

### Second independent confirmation: MASTR-seq HTT

A second primary-data audit identified four engineered HTT samples in
`SRP504233` with one compact raw POD5 in Zenodo record `17618429`. The frozen
uninterrupted-CAG truths are parental `20/22`, edited normal `20/22`, expanded
`22/56`, and expanded `22/72`. These labels come from the engineered RUES2
line definitions and archive sample mapping, not from the paper's observed
nanopore repeat distributions.

The raw metadata changed the interpretation of this gate before prediction:
`FAW16852.pod5` reports `FLO-MIN106`, `sqk-lsk109`, and 4,000-Hz sampling.
Therefore this is an independent targeted-library R9.4.1 confirmation, not the
initially proposed R10.4.1 cross-chemistry test. The compatible frozen Dorado
0.7.3 models are R9 FAST v3.4 for barcode/locus UUID selection and R9 SUP v3.6
for final move-table boundaries. The external-genotype firewall and ACF gate
are unchanged.

The CPU selection pass screens a deterministic SHA-256-ranked subset of 15,000
of the 91,869 raw UUIDs (seed `mastr-raw-screen-v1`). This compute cap was set
using only raw-run size and truth-free locus/barcode hit rate, before final
sample selection or prediction. Failure to reach six QC windows in any sample
invalidates the gate; it is not permission to inspect truth or tune a feature.

The confirmatory decision is predeclared as:

```text
required samples:                       all four MASTR samples
minimum QC-passing signal rows/sample:  6
primary pooled fixed-ACF allele MAE:     <= 3 repeats
expanded long-allele absolute error:    <= 5 repeats for both 56/72 samples
duration feature:                       diagnostic only, never gating
```

No feature, calibration, threshold, or boundary-QC change is allowed after
`mastr_sealed_predictions.tsv` is written. Only
`score_mastr_confirmation.sh` may open the isolated truth manifest.

The gate is complete and failed. The truth-free FAST screen selected 146 raw
UUIDs and SUP retained 145 QC windows: parental 27, normal 20, expanded-56 46,
and expanded-72 52. Before SUP or truth access, sequence-to-archive auditing
detected that the initial barcode09/barcode10 labels were reversed; the final
sample mapping was corrected and then passed at 100%, 100%, 97.6%, and 100%
concordance. This is a provenance correction, not genotype-driven tuning.

Fixed-ACF predictions and per-sample allele MAE were:

| Sample | Truth | Prediction | Allele MAE |
|---|---:|---:|---:|
| parental | 20/22 | 12.517/22.410 | 3.947 |
| normal | 20/22 | 13.915/20.442 | 3.822 |
| expanded-56 | 22/56 | 21.396/55.363 | 0.621 |
| expanded-72 | 22/72 | 19.071/77.781 | 4.355 |

Pooled fixed-ACF allele MAE was `3.186`, above the `3.000` threshold, and the
expanded-72 long-allele error was `5.781`, above the `5.000` threshold.
Diagnostic duration MAE was `4.622`. ACF therefore transferred better than
duration but did not pass either primary confirmatory condition. These four
samples are now exposed and must not be used to retune the feature,
calibration, QC rules, or gate.
