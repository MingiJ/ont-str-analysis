# Algorithm development

This folder will hold the new STR counting algorithm implementation.

Recommended structure:
```
src/algorithm/
  data_io.py        # FAST5/BAM helpers
  evidence_table.py # joins baseline per-read evidence for training/debugging
  signal.py         # signal preprocessing + event segmentation
  model.py          # core model / alignment / inference
  postprocess.py    # peak calling / confidence scoring
  eval.py           # evaluation hooks
```

Design goals (from paper):
- repeat-boundary detection improvements
- per-read confidence with uncertainty-aware clustering
- robustness to strand / mapping offsets

Current thesis gate:
- the strict HTT CAG truth benchmark is complete for nine samples
- use `ont-str-runner/work/analysis/ground_truth_comparison.csv` and
  `ont-str-runner/work/analysis/benchmark_report.md` as the benchmark sources
- treat the current NumPy models as weak-label prototypes, not final thesis
  model evidence

Start here:
- define inputs/outputs for per-read counting
- implement a minimal pipeline that reads one FAST5 + BAM alignment and returns repeat count + confidence

Current first milestone:
```bash
python3 src/algorithm/evidence_table.py
```

This writes `ont-str-runner/work/analysis/evidence_table.tsv`, a per-read metadata table joining available WarpSTR, STRique, DeepRepeat, f5index, truth-label, and alignment-context evidence. It is the input manifest for later raw-signal window extraction.

By default it uses the nine complete truth samples:

```text
GM04723 ND30015 ND30016 ND30047 ND30422 ND30626 ND31551 ND33392 ND33947
```

`REL3_WARPSTR_OK` remains useful as an unlabeled failure-mode probe, but include
it only with explicit `--samples`.

Current second milestone:
```bash
.venv/bin/python src/algorithm/signal_windows.py
```

This writes normalized fixed-width raw-signal arrays to `ont-str-runner/work/analysis/signal_windows.npz` and read metadata to `ont-str-runner/work/analysis/signal_windows.index.tsv`. By default it extracts reads with WarpSTR-derived raw-signal boundaries from the nine-sample truth manifest. Window metadata includes the absolute source span, padded window span, stored length, and truncation flag.

Current third milestone:
```bash
.venv/bin/python src/algorithm/baseline.py
```

This loads `signal_windows.npz` with `src/algorithm/dataset.py`, builds combined signal-summary and temporal pooled-bin features, and fits a deterministic ridge-regression baseline. It writes per-read predictions to `ont-str-runner/work/analysis/baseline_predictions.tsv` and metrics to `ont-str-runner/work/analysis/baseline_summary.tsv`.

Default evaluation uses a held-out sample split with `ND33392` as the test
sample, so reads from the same sample do not leak across train and test. Use
`--split random-read` only for quick sanity checks.

Current baseline caveat: this is a weak-label sanity check, not the thesis model. Labels come from existing tool-derived read groups, not manual per-read truth.

Current nine-sample ridge result:

```text
rows_total: 30356
holdout_sample: ND33392
test_mae: 9.705
test_mae_long_like: 11.158
test_mae_short_like: 7.899
```

Current fourth milestone:
```bash
.venv/bin/python src/algorithm/neural_baseline.py
```

This trains a lightweight NumPy neural prototype: a one-hidden-layer MLP over summary plus temporal pooled signal features with inverse-label weighting and an internal validation split for early model selection. It writes per-read predictions to `ont-str-runner/work/analysis/neural_baseline_predictions.tsv` and metrics to `ont-str-runner/work/analysis/neural_baseline_summary.tsv`.

Current neural caveat: this is still a weak-label prototype, not the final RNN.
On the nine-sample held-out `ND33392` split, it improves test MAE versus the
ridge baseline, but long-allele generalization remains weaker than short-allele
generalization. The next model should use a sequence-aware architecture and
better boundary supervision.

Current nine-sample NumPy neural result:

```text
rows_total: 30356
holdout_sample: ND33392
test_mae: 7.405
test_mae_long_like: 9.355
test_mae_short_like: 4.982
```

Baseline result reference:

```text
docs/ALGORITHM_BASELINE_RESULTS.md
```

Historical note: older 266-row ridge/NumPy results in session handoff notes are
superseded by the nine-sample 30356-row run above.

Current allele-level evaluation command:

```bash
.venv/bin/python src/algorithm/evaluate_allele_calls.py \
  --predictions ont-str-runner/work/analysis/neural_baseline_predictions.tsv \
  --calls ont-str-runner/work/analysis/neural_baseline_allele_calls_calibrated.tsv \
  --summary ont-str-runner/work/analysis/neural_baseline_allele_summary_calibrated.tsv \
  --calibration train-affine
```

Current calibrated held-out `ND33392` MLP allele result:

```text
truth: 57/17
call: 57/18
allele_mae: 0.500
```

Current leave-one-sample-out MLP allele result:

```bash
.venv/bin/python src/algorithm/run_loso_neural.py
```

```text
overall_allele_mae: 0.556
long_mae: 0.333
short_mae: 0.778
tail_span_correction: True
```

This beats the current WarpSTR and STRique overall allele MAEs on the nine
truth samples under leave-one-sample-out evaluation. The key improvement is a
tail-span correction for out-of-range long alleles: GM04723 held out changes
from `59/18` to `70/18` for `72/17` truth.

Current reusable caller:

```bash
.venv/bin/python src/algorithm/call_alleles.py
```

This trains on all labeled rows in the supplied signal archive, predicts every
read, clusters sample-level alleles, applies train-sample calibration, and uses
the tail-span correction for out-of-range long alleles. Default outputs:

```text
ont-str-runner/work/analysis/algorithm_predictions.tsv
ont-str-runner/work/analysis/algorithm_allele_calls.tsv
ont-str-runner/work/analysis/algorithm_summary.tsv
```

REL3 validation now uses independent BAM/native-FAST5 signal boundaries rather
than only the 54 reads selected by WarpSTR. Build the expanded boundary table:

```bash
.venv/bin/python src/algorithm/alignment_signal_bounds.py
```

This maps the HTT reference interval through BAM CIGAR operations and native
FAST5 event/move tables. Current coverage is 93 full-flank windows from 172
matched REL3 reads. Boundary validation against 38 existing WarpSTR reads has
median absolute differences of 12-29 raw samples.

The same mapper now covers all nine truth samples without using WarpSTR read
selection, WarpSTR signal boundaries, or per-read allele groups. Build the
bounded development manifest with:

```bash
.venv/bin/python src/algorithm/build_independent_truth_manifest.py
```

This produced 1,152 rows (128 per sample); 1,135 passed independent boundary
consistency checks. Build the repeat-focused archive used by the current
physics and RNN ablations with:

```bash
.venv/bin/python src/algorithm/signal_windows.py \
  --manifest ont-str-runner/work/analysis/independent_truth_signal_bounds_dev.tsv \
  --boundary-kind repeat \
  --padding 250 \
  --max-signal-len 10000 \
  --require-boundary-qc \
  --output ont-str-runner/work/analysis/signal_repeat_windows_independent_qc_dev.npz \
  --index ont-str-runner/work/analysis/signal_repeat_windows_independent_qc_dev.index.tsv
```

The archive contains 1,135 repeat windows with no truncation. Its exact mapped
repeat span can be evaluated without any neural model or per-read labels:

```bash
.venv/bin/python src/algorithm/evaluate_repeat_duration_loso.py
```

The strict nine-fold LOSO allele MAE is `1.638`. This is substantially better
than the independent full-flank duration ablation (`4.776`) and narrowly
better than STRique (`1.667`), but remains worse than the frozen engineered MLP
(`0.556`) and WarpSTR (`0.722`). It is a forced physics ablation without
uncertainty or abstention, not the proposed final caller.

A repeat-local autocorrelation probe is available as a development-only next
gate:

```bash
.venv/bin/python src/algorithm/evaluate_repeat_periodicity_loso.py
```

The fixed autocorrelation-normalized proxy has exploratory LOSO MAE `1.414`,
but its feature and parameters were devised after inspecting these nine
samples. It is therefore not an unbiased benchmark result. A nested selector
that chooses between raw duration and autocorrelation using only inner training
folds obtains MAE `1.725` (autocorrelation selected in 8/9 folds). The evidence
supports external confirmation of a frozen periodicity estimator; it does not
support further tuning or a claimed win on the same samples.

Build the combined manifest while keeping REL3 unlabeled:

```bash
.venv/bin/python src/algorithm/evidence_table.py \
  --samples GM04723 ND30015 ND30016 ND30047 ND30422 ND30626 ND31551 \
            ND33392 ND33947 REL3_EXPANDED \
  --output ont-str-runner/work/analysis/evidence_table_truth_plus_rel3_expanded.tsv
```

Create the REL3-only windows, then combine them with the existing nine-sample
truth archive:

```bash
.venv/bin/python src/algorithm/signal_windows.py \
  --manifest ont-str-runner/work/analysis/evidence_table_truth_plus_rel3_expanded.tsv \
  --samples REL3_EXPANDED \
  --output ont-str-runner/work/analysis/signal_windows_rel3_expanded.npz \
  --index ont-str-runner/work/analysis/signal_windows_rel3_expanded.index.tsv

.venv/bin/python src/algorithm/combine_signal_archives.py \
  --input ont-str-runner/work/analysis/signal_windows.npz \
          ont-str-runner/work/analysis/signal_windows.index.tsv \
  --input ont-str-runner/work/analysis/signal_windows_rel3_expanded.npz \
          ont-str-runner/work/analysis/signal_windows_rel3_expanded.index.tsv \
  --output ont-str-runner/work/analysis/signal_windows_truth_plus_rel3_expanded.npz \
  --index ont-str-runner/work/analysis/signal_windows_truth_plus_rel3_expanded.index.tsv
```

Expanded archive:

```text
ont-str-runner/work/analysis/signal_windows_truth_plus_rel3_expanded.npz
ont-str-runner/work/analysis/signal_windows_truth_plus_rel3_expanded.index.tsv
```

Current REL3 caller command:

```bash
.venv/bin/python src/algorithm/call_alleles.py \
  --signal-archive ont-str-runner/work/analysis/signal_windows_truth_plus_rel3_expanded.npz \
  --index ont-str-runner/work/analysis/signal_windows_truth_plus_rel3_expanded.index.tsv \
  --predictions ont-str-runner/work/analysis/algorithm_truth_plus_rel3_expanded_predictions.tsv \
  --calls ont-str-runner/work/analysis/algorithm_truth_plus_rel3_expanded_allele_calls.tsv \
  --summary ont-str-runner/work/analysis/algorithm_truth_plus_rel3_expanded_summary.tsv
```

Current REL3 call:

```text
REL3_EXPANDED: 17/17 unresolved consensus
raw prediction median: 18.812
rows available/used: 93/33
rows filtered below MAPQ 20: 60
confidence: low
confidence reason: small_read_count;unresolved_allele_separation;mapping_quality_filtering
```

REL3 is unlabeled here, so this is a stability/failure-handling probe rather
than an MAE measurement. The historical 54-read `54/18` result was selected by
WarpSTR success and is superseded for interpretation. Without MAPQ filtering,
the expanded 93-read sensitivity call is `38/15`; low-MAPQ extreme predictions
drive its apparent long cluster. Independent sequence evidence in the 33
MAPQ-60 reads supports a normal-length, unresolved result.

Current fifth milestone:
```bash
.venv/bin/python src/algorithm/torch_rnn.py
```

This trains the first PyTorch sequence-aware prototype: a small Conv1d front-end
followed by a bidirectional GRU by default. The current defaults are sized for a
CPU-feasible first experiment. It consumes the padded normalized raw-signal
windows directly and writes per-read predictions, confidence scores, summary
metrics, and a checkpoint:

```text
ont-str-runner/work/analysis/torch_rnn_predictions.tsv
ont-str-runner/work/analysis/torch_rnn_summary.tsv
ont-str-runner/work/analysis/torch_rnn.pt
```

Use a CPU smoke test before longer training:

```bash
.venv/bin/python src/algorithm/torch_rnn.py --device cpu --epochs 1 --max-rows 512
```

Current RNN status: implemented and run with CPU PyTorch (`torch 2.12.0+cpu`).

Current nine-sample PyTorch RNN result:

```text
rows_total: 30356
holdout_sample: ND33392
test_mae: 8.692
test_mae_long_like: 8.748
test_mae_short_like: 8.622
```

Interpretation: the first CPU-feasible RNN beats the ridge baseline (`9.705`)
but does not yet beat the NumPy MLP (`7.405`). Its errors are more balanced
between long-like and short-like reads, so the sequence path is promising but
still needs model and label improvements.

Current RNN caveat: this is still weak-label training. The completed run proves
the raw-signal sequence path works in PyTorch, but final thesis evidence still
needs stronger labeling, boundary supervision, and sample-level allele
clustering.

## Unordered-diploid weak-supervision experiment

The next prototype removes baseline-derived per-read assignments from training:

```bash
.venv/bin/python src/algorithm/weak_supervised_rnn.py \
  --device cpu \
  --epochs 20 \
  --min-component-fraction 0.30 \
  --caller-min-component-fraction 0.20 \
  --holdout-sample ND33392
```

`weak_supervised_rnn.py` uses only the unordered sample genotype as training
supervision. It fits a duration calibration on training samples only, learns a
Conv-BiRNN residual and heteroscedastic variance, performs latent allele
assignment, calibrates uncertainty on a separate validation sample, and may
abstain rather than force a diploid call. The index `group_label` and per-read
`target` fields are not used for optimization.

Run the primary nested sample-disjoint evaluator with:

```bash
.venv/bin/python src/algorithm/run_weak_supervised_loso.py
```

The evaluator defaults to 64 reads per sample for a development screen. Use
`--max-rows-per-sample 0` for a full-read run. It reports resolved-call
coverage separately from conditional resolved-call MAE; candidate-mode MAE is
also reported but is not a clinical call metric.

The original WarpSTR-window screen resolved `0/9` folds and produced
diagnostic candidate-mode MAE `14.784`. Repeating the experiment on the new
independent full-flank windows still resolved only `1/9` folds (candidate MAE
`10.951`). Repeat-focused windows improved separation, but the first selector
incorrectly preferred validation likelihood even as validation genotype error
worsened.

The corrected implementation makes epoch 0 (the duration prior) eligible and
selects epochs by validation-sample allele MAE. In the resulting nine-fold
run, seven folds rejected neural training and two selected trained epochs. The
aggregate uncertainty caller resolved `5/9`, with candidate MAE `5.775` and
conditional resolved-call MAE `4.400`. This remains much worse than the clean
duration-only LOSO ablation (`1.638`), so the Conv-BiRNN residual fails the
development gate and is frozen as a negative result. It has not beaten the
frozen NumPy MLP and is not the default caller. See
`docs/PROPOSED_RNN_ALGORITHM_PLAN.md` for the prior-art audit, exact novelty
scope, experimental results, and next research gate.

Unit tests:

```bash
PYTHONPATH=src/algorithm .venv/bin/python -m unittest \
  src/algorithm/test_alignment_signal_bounds.py \
  src/algorithm/test_call_alleles.py \
  src/algorithm/test_evaluate_external_confirmation.py \
  src/algorithm/test_external_fast5_batches.py \
  src/algorithm/test_extract_external_fast5_reads.py \
  src/algorithm/test_f5c_signal_bounds.py \
  src/algorithm/test_http_tar_members.py \
  src/algorithm/test_repeat_duration_loso.py \
  src/algorithm/test_repeat_periodicity_loso.py \
  src/algorithm/test_remote_fast5_lookup.py \
  src/algorithm/test_select_external_htt_reads.py \
  src/algorithm/test_signal_windows.py \
  src/algorithm/test_uncertainty_alleles.py \
  src/algorithm/test_weak_supervised_rnn.py
```

## External confirmation gate

The frozen external cohort is recorded in:

```text
ont-str-runner/configs/external_confirmation_samples.tsv
```

It contains independently genotyped Coriell samples NA13509 (`15/70`) and
NA13512 (`16/44`) from SRA study `SRP349335`. NCBI's full SRA XML maps those
identities to exact FASTQ, FAST5, and SLOW5 accessions. The raw archives are
103--293 GB each, so full downloads are not the default acquisition method.

Index an uncompressed SRA tar remotely using small HTTP Range requests:

```bash
.venv/bin/python src/algorithm/http_tar_members.py \
  --url <raw-slow5-or-fast5-object-url> \
  --output ont-str-runner/work/analysis/external_confirmation/<alias>_slow5.members.tsv
```

Then identify HTT reads without storing the run-wide FASTQ:

```bash
ont-str-runner/scripts/prepare_external_confirmation.sh GBXM106320
ont-str-runner/scripts/prepare_external_confirmation.sh GBXM077293
```

The script streams the embedded pass FASTQ to minimap2 against hg38 chr4 and
retains mapped reads. It then keeps only unique MAPQ >=20 alignments spanning both
112-bp HTT flanks and applies a deterministic truth-free cap of 128 reads. Set
`MAX_HTT_READS=0` only if an uncapped sensitivity analysis is explicitly
needed. It stores only the compressed header line for every pass and fail read;
the batch mapper recovers acquisition timestamps from this census by exact
read ID even when the SAM/BAM writer omits the original FASTQ comment.
The multi-FAST5 filenames form chronological 4,000-read batches; after adding
fail-read headers, a target read's timestamp rank identifies its batch
directly. Deposited FAST5 is raw-only and has no
basecall event/move table. The frozen CPU path uses f5c event alignment to map
the deposited FASTQ sequence to raw-signal indices; it does not re-basecall the
external reads.

Estimate and fetch the selective FAST5 batches after the alignment/header
stream completes:

```bash
.venv/bin/python src/algorithm/external_fast5_batches.py \
  --htt-read-metadata ont-str-runner/work/analysis/external_confirmation/GBXM106320/GBXM106320.htt_read_metadata.tsv \
  --headers ont-str-runner/work/analysis/external_confirmation/GBXM106320/GBXM106320.pass_fastq_headers.txt.gz \
  --headers ont-str-runner/work/analysis/external_confirmation/GBXM106320/GBXM106320.fail_fastq_headers.txt.gz \
  --fast5-member-index ont-str-runner/work/analysis/external_confirmation/GBXM106320_fast5.members.tsv \
  --output ont-str-runner/work/analysis/external_confirmation/GBXM106320/GBXM106320.fast5_batch_candidates.tsv

MAX_DISTANCE=0 ont-str-runner/scripts/fetch_external_fast5_batches.sh GBXM106320
```

First download central batches and verify exact root read IDs. Increase
`MAX_DISTANCE` to `1`, then `2`, only for reads not found in the prior stage.
Copy verified groups into a target-only raw FAST5 with:

```bash
HDF5_PLUGIN_PATH=/home/jkaranja/workdir/tools/vbz-1.0.1/ont-vbz-hdf-plugin-1.0.1-Linux/usr/local/hdf5/lib/plugin \
  .venv/bin/python src/algorithm/extract_external_fast5_reads.py \
  --batch-dir ont-str-runner/work/analysis/external_confirmation/GBXM106320/fast5_batches \
  --htt-read-metadata ont-str-runner/work/analysis/external_confirmation/GBXM106320/GBXM106320.htt_read_metadata.tsv \
  --output-fast5 ont-str-runner/work/analysis/external_confirmation/GBXM106320/selected_raw/GBXM106320.selected_raw.fast5 \
  --mapping ont-str-runner/work/analysis/external_confirmation/GBXM106320/GBXM106320.fast5_read_mapping.tsv
```

Map the published HTT read sequences to the selected raw signal with the
pinned f5c 1.6 CPU binary, then derive truth-free repeat boundaries and fixed
repeat windows:

```bash
ont-str-runner/scripts/run_external_f5c_eventalign.sh GBXM106320

.venv/bin/python src/algorithm/f5c_signal_bounds.py \
  --sample NA13509 \
  --fast5 ont-str-runner/work/analysis/external_confirmation/GBXM106320/selected_raw/GBXM106320.selected_raw.fast5 \
  --bam ont-str-runner/work/analysis/external_confirmation/GBXM106320/GBXM106320.htt.bam \
  --eventalign ont-str-runner/work/analysis/external_confirmation/GBXM106320/GBXM106320.eventalign.tsv \
  --output ont-str-runner/work/analysis/external_confirmation/GBXM106320/GBXM106320.f5c_signal_bounds.tsv

HDF5_PLUGIN_PATH=/home/jkaranja/workdir/tools/vbz-1.0.1/ont-vbz-hdf-plugin-1.0.1-Linux/usr/local/hdf5/lib/plugin \
  .venv/bin/python src/algorithm/signal_windows.py \
  --manifest ont-str-runner/work/analysis/external_confirmation/GBXM106320/GBXM106320.f5c_signal_bounds.tsv \
  --boundary-kind repeat \
  --padding 250 \
  --require-boundary-qc \
  --output ont-str-runner/work/analysis/external_confirmation/GBXM106320/GBXM106320.repeat_windows.npz \
  --index ont-str-runner/work/analysis/external_confirmation/GBXM106320/GBXM106320.repeat_windows.index.tsv
```

Run the same three commands for `GBXM077293` / biological sample `NA13512`,
then combine the two truth-free archives before prediction. f5c event positions
define approximate reference-k-mer spans, so the boundary QC requires
consistent left, repeat, and right raw-samples-per-base rates. The raw signal
itself remains the deposited signal, and no external genotype enters this
mapping step.

The confirmatory rule is frozen: fit duration and ACF calibrations on all nine
development samples, make predictions for the external samples without using
their truth, then reveal Coriell truth and report per-sample/pooled allele MAE.
No feature, lag range, threshold, or calibration choice may be changed after
the external predictions are inspected.

The final evaluator intentionally separates prediction from scoring:

```bash
.venv/bin/python src/algorithm/evaluate_external_confirmation.py predict \
  --external-index <truth-free-external-repeat-index.tsv> \
  --external-archive <external-repeat-windows.npz> \
  --output <sealed-external-predictions.tsv>

.venv/bin/python src/algorithm/evaluate_external_confirmation.py score \
  --predictions <sealed-external-predictions.tsv> \
  --output <external-scores.tsv> \
  --summary <external-score-summary.tsv>
```

The completed frozen gate used 17 QC-passing truth-free windows (NA13509 5,
NA13512 12). The sealed predictions and input checksums are under
`ont-str-runner/work/analysis/external_confirmation/`. External allele MAE was
`3.103` for duration and `2.894` for fixed ACF. The small `0.210` pooled ACF
advantage is heterogeneous: ACF MAE was `5.516` on NA13509 but `0.271` on
NA13512, while duration was `2.270` and `3.936`. Treat this as weak external
support, not a decisive ACF win, and do not tune either feature on these now-
revealed samples.

## Independent MASTR-seq HTT gate

The next frozen cohort is four Cas9-targeted HTT samples from `SRP504233` and
Zenodo record `17618429`: parental and normal controls plus engineered 56- and
72-CAG expansions. Acquisition and truth are separated in
`mastr_confirmation_acquisition.tsv` and `mastr_confirmation_truth.tsv`.
Truth is expressed as uninterrupted CAG count: `20/22`, `20/22`, `22/56`, and
`22/72`.

The raw file's `run_info` is authoritative: `FAW16852.pod5` reports
`FLO-MIN106`, `sqk-lsk109`, and 4,000 Hz. This corrects an initial paper-level
R10 assumption and makes the cohort an independent targeted-library R9.4.1
test, not a cross-chemistry test. Dorado 0.7.3 therefore uses
`dna_r9.4.1_e8_fast@v3.4` for truth-free barcode/HTT UUID selection and
`dna_r9.4.1_e8_sup@v3.6` for the sealed signal-boundary path.

```bash
ont-str-runner/scripts/prepare_mastr_confirmation.sh
ont-str-runner/scripts/select_mastr_raw_reads.sh
ont-str-runner/scripts/run_mastr_prediction.sh
# Only after the prediction file exists:
ont-str-runner/scripts/score_mastr_confirmation.sh
```

ENA FASTQ alignment confirms abundant full-flank HTT coverage but cannot
identify raw records because ENA/SRA rewrites read names to archive ordinals.
The selection script instead basecalls the complete POD5 with the FAST model,
classifies `SQK-NBD114-24` barcodes, applies the same unique MAPQ >=20 and
112-bp full-flank rule, and caps each sample deterministically at 128 UUIDs.
For bounded CPU runtime it first SHA-256-ranks raw UUIDs with seed
`mastr-raw-screen-v1` and screens 15,000 of 91,869 reads; this truth-free cap
was fixed before final UUID selection and before any genotype prediction.
FAST calls are never used as the measured feature or genotype prediction.
Before SUP, `audit_mastr_archive_mapping.sh` aligns selected raw FAST calls
back to all four public ENA read sets and requires at least three high-identity
matches plus >=90% sample concordance per barcode. This truth-free check is
important because the paper-level chemistry description and POD5 `run_info`
disagree; it verifies the barcode/sample join from sequence identity itself.

`dorado_move_signal_bounds.py` maps the SUP alignment CIGAR through Dorado's
`mv`, `ts`, and `ns` tags in original signal orientation.
`extract_pod5_signal_windows.py` then reads only those UUIDs and emits the same
truth-free NumPy/index interface used by the frozen duration and ACF features.
`evaluate_mastr_confirmation.py` requires exactly four samples and at least six
QC rows per sample. The predeclared gate is pooled fixed-ACF allele MAE <=3
and expanded long-allele absolute error <=5 for both expanded samples. Raw
duration remains diagnostic-only and cannot change the decision.

The frozen run is complete. The FAST screen selected 146 raw UUIDs. A
truth-free alignment back to the four complete ENA archives caught and
corrected a barcode09/barcode10 sample-label reversal before SUP basecalling;
the final archive concordance was 100%, 100%, 97.6%, and 100%. SUP retained
145 QC windows (27, 20, 46, and 52 by parental, normal, expanded-56, and
expanded-72 sample).

The sealed fixed-ACF predictions produced pooled allele MAE `3.186` and a
maximum expanded long-allele error of `5.781`. Both exceed the predeclared
limits (`3.000` and `5.000`), so the independent MASTR gate failed. Diagnostic
duration MAE was `4.622`. Do not retune on these four now-revealed samples.
