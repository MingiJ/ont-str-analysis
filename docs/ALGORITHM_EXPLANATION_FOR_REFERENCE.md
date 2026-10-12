# Plain-English Reference: STR Algorithms and Proposed Thesis Method

This document is a reference for understanding the existing STR tools, the benchmark results, and the planned thesis algorithm.

Thesis title: **Direct Estimation of Short Tandem Repeat Expansions from Raw Nanopore Signals using a Deep Recurrent Neural Network**.

Main thesis goal: build a new raw-signal algorithm that estimates STR repeat counts better and more reliably than WarpSTR, DeepRepeat, and STRique, then compare all four methods on the same HTT CAG benchmark data.

## 1. The Biological Problem

Short Tandem Repeats (STRs) are DNA regions where a short motif repeats many times.

For Huntington's disease, the important repeat is `CAG` in the `HTT` gene.

Example:

```text
CAG CAG CAG CAG CAG ...
```

Each `CAG` block is one repeat unit.

If the DNA contains 17 copies of `CAG`, the allele size is 17 repeats. If it contains 57 copies, the allele size is 57 repeats.

The clinical problem is that large expansions can cause disease. Therefore, we need to estimate the number of repeats accurately.

For this thesis, the main benchmark locus is:

```text
HTT CAG locus: chr4:3074876-3074933
Motif: CAG
```

Ground truth examples:

- `ND33392`: expected `57/17` CAG repeats.
- `GM04723`: expected `72/17` CAG repeats.
- `ND30626`: expected `41/21` CAG repeats.

The two numbers represent the two inherited alleles: one from each parent.

## 2. Why Nanopore STR Counting Is Hard

Oxford Nanopore sequencing reads DNA by measuring electrical current as DNA passes through a nanopore.

The machine records a raw signal, not letters directly.

The usual pipeline is:

```text
raw electrical signal -> basecaller -> DNA letters -> repeat counting
```

The problem is that repeats are difficult for basecallers.

An analogy: imagine listening to a drum beat that goes `tap tap tap tap tap` many times. If the rhythm is long and repetitive, it becomes hard to count exactly how many taps happened. You may miss one or add one by mistake.

For STRs, the basecaller can insert or delete bases inside the repeat tract. That can change the estimated repeat count.

This is why signal-level methods exist. They try to use the raw nanopore signal directly instead of relying only on basecalled DNA letters.

## 3. Important Unit Clarification

This is very important for interpreting benchmark results.

Different tools report different units.

### WarpSTR Units

WarpSTR `overview.csv` fields:

- `results`: length of the WarpSTR-predicted repeat-region sequence in bases.
- `orig`: length of the original/basecall-derived repeat-region sequence in bases.

WarpSTR `predictions/alleles.csv` fields:

- `WarpSTR_allele1`, `WarpSTR_allele2`: allele lengths in bases.
- `basecall_allele1`, `basecall_allele2`: basecall-derived allele lengths in bases.

For HTT CAG, one repeat unit is 3 bases. Therefore:

```text
CAG repeat count = WarpSTR length / 3
```

Example:

```text
WarpSTR allele length = 52 bases
52 / 3 = 17.3, approximately 17 CAG repeats
```

So a WarpSTR value of `52` does **not** mean 52 CAG repeats. It means about 17 CAG repeats.

This was confirmed from WarpSTR source code inside the Docker image:

- `results` is written as `len(seq_results[idx][1])`.
- `orig` is written as `len(seq_results[idx][0])`.
- basecall allele values come from `row.r_seq_start - row.l_seq_end`.

These are base lengths, not repeat counts.

### STRique Units

STRique reports repeat counts directly.

Example:

```text
STRique count = 59
```

This means about 59 CAG repeats.

Do not divide STRique counts by 3.

### DeepRepeat Units

DeepRepeat does not emit a clean allele-count CSV like WarpSTR or STRique.

In this project, DeepRepeat values are parsed from logs:

- GMM peaks.
- Allocation histogram (`allocr`).

These values appear to represent repeat-count estimates, not base lengths.

Example:

```text
ND33392 DeepRepeat GMM: 18,58
```

This is close to the truth `17/57`.

Do not divide DeepRepeat GMM/allocr values by 3.

## 4. What WarpSTR Does

WarpSTR is a signal-alignment method.

Plain-English summary:

> WarpSTR builds an expected signal pattern for the repeat and tries to align each read's raw signal to that expected pattern. It then estimates how long the repeat region is.

### Step-by-Step

1. WarpSTR takes the reference locus and motif.

For HTT CAG:

```text
chr4:3074876-3074933
motif: CAG
```

2. It builds a model of the expected nanopore signal.

Nanopore current depends on short DNA words called k-mers. WarpSTR uses a pore model to estimate what signal should be produced by the repeat and flanking regions.

3. It extracts raw signal around the target repeat.

It uses BAM alignment and FAST5 files to find the signal segment that corresponds to the HTT CAG region.

4. It aligns observed signal to expected signal using DTW.

DTW means Dynamic Time Warping.

Simple analogy: imagine two versions of the same song, one played faster and one slower. DTW stretches and compresses time so matching parts line up. WarpSTR uses this idea to align noisy nanopore signal to an expected STR signal pattern.

5. It converts the alignment into a predicted sequence length.

This is where the unit issue matters. WarpSTR outputs the length of the predicted repeat-region sequence in bases.

6. It clusters read-level estimates into allele peaks.

Humans usually have two alleles. WarpSTR tries to find one or two clusters of repeat lengths across reads.

### WarpSTR Strengths

- Uses raw signal directly.
- Can work without trusting basecalled repeat sequence too much.
- In the historical benchmark, it produced strong multi-sample allele-level accuracy after converting base lengths to repeat counts by dividing by 3.

### WarpSTR Weaknesses

- Boundary detection can be wrong.
- If it chooses repeat start/end incorrectly, the count shifts.
- It can miss one allele if most usable reads support only one cluster.
- It reports base lengths, so users must convert to repeat counts correctly.

### Example: ND33392 Small WarpSTR Subset

Truth:

```text
ND33392 = 57/17 CAG repeats
```

Small WarpSTR subset:

```text
WarpSTR allele = 52 bases
52 / 3 = about 17 CAG repeats
```

Interpretation:

```text
This small subset detected the short allele, not the expanded 57-repeat allele.
```

That means the earlier interpretation that WarpSTR detected a 52-repeat expanded allele was incorrect.

## 5. What STRique Does

STRique is also a signal-level STR counting method.

Plain-English summary:

> STRique uses flanking sequences to find the repeat region and then counts how many repeat units fit into the raw signal.

### Step-by-Step

1. STRique uses known flanking regions around the repeat.

Flanks are the DNA sequences before and after the STR.

Analogy: if the repeat is a row of identical tiles, the flanks are the unique floor patterns before and after the tile row. They help locate where the repeat starts and ends.

2. It extracts signal between the flanks.

3. It uses a pore model to interpret signal patterns.

4. It estimates repeat counts per read.

5. A sample-level allele estimate is obtained by looking at the distribution of per-read counts.

### STRique Strengths

- Reports repeat counts directly.
- Often captures short/normal alleles well.
- Provides per-read count output, which is useful for histograms and comparison.

### STRique Weaknesses

- Can produce extreme outliers.
- Can overestimate long alleles.
- Depends strongly on finding the flanking regions correctly.
- If boundaries are wrong, repeat counts become wrong.

### Example: ND33392

Truth:

```text
57/17
```

STRique available output:

```text
59/18
```

Interpretation:

```text
Very close to truth, but slightly high for both alleles.
```

## 6. What DeepRepeat Does

DeepRepeat is a deep-learning-based signal method.

Plain-English summary:

> DeepRepeat uses a trained model to identify repeat-like signal regions and produce model-derived repeat information, but its final allele reporting is less direct than WarpSTR or STRique.

### Step-by-Step

1. DeepRepeat takes FAST5 signal, BAM alignment, repeat coordinates, and a trained model.

2. It identifies signal positions that look like repeat sequence.

3. It reports logs with information such as:

- Per-read processing details.
- Warnings.
- GMM peaks.
- Allocation histogram (`allocr`).

4. In this repository, we parse the log to recover approximate allele peaks.

### What GMM Means

GMM means Gaussian Mixture Model.

Plain-English analogy: suppose you have many per-read estimates. Some cluster around 17 and others cluster around 57. A GMM tries to fit two bell-shaped curves to these values and call them alleles.

### DeepRepeat Strengths

- Uses deep learning.
- Can work well on some samples.
- For ND33392, it produced GMM peaks close to truth:

```text
DeepRepeat: 18,58
Truth:      17,57
```

### DeepRepeat Weaknesses

- Does not provide a clean standard repeat-count CSV in this workflow.
- Requires log parsing.
- GMM peak selection can miss short alleles even when allocation evidence exists.

Historical benchmark observation:

```text
In 4/9 labeled samples, DeepRepeat showed a short-allele allocation peak but GMM peaks stayed long-only.
```

Interpretation:

```text
The model may detect useful signal, but the final allele-selection step can fail.
```

## 7. Why Existing Tools Are Not Enough

The benchmark results suggest that no existing tool is perfect.

WarpSTR:

- Good signal alignment.
- But boundary errors and unit interpretation are risks.
- Can miss an allele in subsets.

STRique:

- Good direct repeat-count output.
- But outliers and long-allele overestimation occur.

DeepRepeat:

- Deep learning is promising.
- But output format and GMM peak selection are weak points.

Basecalling:

- Useful as weak evidence.
- But unreliable inside long homogeneous repeats.

Therefore, the thesis algorithm should combine the strengths and avoid the weaknesses.

## 8. Intended Thesis Solution

The intended solution is a deep recurrent neural network that estimates repeat counts directly from raw nanopore signal.

Plain-English summary:

> Instead of first converting the signal into DNA letters, the model learns the signal pattern of CAG repeats directly and predicts the repeat count from the raw current trace.

The model should answer two questions for each read:

1. Where is the repeat region in the signal?
2. How many repeat units does it contain?

## 9. Proposed Model Design

The planned algorithm is a boundary-aware RNN model.

### Input

For each read:

- Raw nanopore signal around HTT CAG.
- Alignment-derived position information.
- Strand direction.
- Optional quality features such as MAPQ and soft clipping.
- Optional weak basecalled motif count.

The raw signal is normalized before being passed to the model.

Normalization means making signal values comparable across reads.

Example:

```text
raw current values -> subtract median -> divide by scale
```

### Neural Network

The proposed architecture:

```text
raw signal window
  -> 1D convolution layers
  -> BiLSTM or BiGRU recurrent layers
  -> output heads
```

### Why 1D Convolution First?

The convolution layers learn local signal patterns.

Analogy: they learn small building blocks of the nanopore signal, like short rhythm fragments in music.

For CAG, local signal patterns repeat many times.

### Why LSTM or GRU?

LSTM and GRU are recurrent neural networks designed for sequences.

They can learn long-range patterns and periodicity.

This matters because an STR is not one isolated signal event. It is a repeated pattern over a long signal segment.

### Outputs

The model should output:

- Per-read repeat-count estimate.
- Confidence score.
- Optional repeat-start and repeat-end boundary probabilities.

Boundary-aware output is important because boundary errors are a major failure mode in existing tools.

## 10. How Our Method Supplants Existing Tools

The proposed method is intended to improve on each tool in a specific way.

### Improvement Over WarpSTR

WarpSTR aligns signal to an expected model using DTW.

Our method should learn directly from data instead of relying only on a fixed expected signal model.

Expected advantages:

- Better tolerance of real nanopore noise.
- Learned boundary detection.
- Direct repeat-count output instead of base-length output.
- Confidence score per read.

### Improvement Over STRique

STRique depends on flanking sequence anchors and signal counting.

Our method should still use flank/alignment information but not rely entirely on hand-designed counting rules.

Expected advantages:

- Fewer outliers.
- Better learned correction for noisy signal windows.
- Confidence-based filtering of bad reads.

### Improvement Over DeepRepeat

DeepRepeat uses deep learning, but in this workflow its final repeat-count output is indirect and log-based.

Our method should produce clean outputs by design:

```text
read_id, repeat_count, confidence, allele_assignment
```

Expected advantages:

- Direct repeat-count output.
- Explicit allele clustering.
- Designed evaluation against ground truth.
- Avoids hidden GMM peak-selection failures by reporting uncertainty and allocation support.

## 11. Planned Pipeline

The final thesis pipeline should look like this:

```text
FAST5/POD5 + BAM + reference
  -> select reads overlapping STR locus
  -> extract raw signal window
  -> normalize signal
  -> RNN predicts per-read repeat count + confidence
  -> cluster per-read predictions into alleles
  -> compare alleles with ground truth and existing tools
```

## 12. Evidence Table First

Before training the model, the first practical implementation step should be an evidence table.

One row per read:

```text
sample
read_id
truth_long
truth_short
mapq
strand
softclip
signal_window_start
signal_window_end
signal_len
basecalled_cag_count
warpstr_bp_length
warpstr_repeat_count
strique_repeat_count
group_label
```

Why this matters:

- It makes the data understandable.
- It allows debugging before training a neural network.
- It shows whether failures are caused by mapping, signal extraction, boundary errors, or model prediction.

## 13. Training Labels

The hardest part is per-read labeling.

We know sample-level truth, such as:

```text
ND33392 = 57/17
```

But each individual read comes from only one allele, and we may not know which allele it came from.

Possible strategy:

1. Use high-confidence reads first.
2. Use baseline tools and clustering to assign likely allele labels.
3. Use soft labels when uncertain.
4. Train the model to predict repeat counts while accounting for allele ambiguity.

Soft-label example:

```text
read A: 80% likely short allele, 20% likely long allele
```

This is better than forcing a possibly wrong hard label.

## 14. Allele Calling

After the model predicts per-read counts, we need sample-level allele calls.

Example per-read predictions:

```text
17, 18, 17, 58, 57, 59, 18, 57
```

These cluster into:

```text
short allele: around 17-18
long allele: around 57-59
```

The model should report:

```text
allele1 = 57, support = N reads, confidence = high
allele2 = 17, support = N reads, confidence = high
```

This avoids depending only on a plain GMM peak without checking support and confidence.

## 15. Evaluation Plan

The new method should be compared against:

- WarpSTR.
- DeepRepeat.
- STRique.
- Basecall-derived estimates where available.

Use the same samples, same ground truth, and same metrics.

Important metrics:

- Long-allele mean absolute error.
- Short-allele mean absolute error.
- Overall allele mean absolute error.
- Missed short-allele rate.
- Outlier rate.
- Clinical category accuracy.
- Number of usable reads.

## 16. How to Explain the Thesis Contribution

A simple way to explain the contribution:

> Existing tools show that raw nanopore signal contains enough information to estimate STR length, but their failures come from boundary ambiguity, outliers, indirect output formats, and weak allele clustering. This thesis proposes a deep recurrent neural network that learns repeat-pattern structure directly from normalized raw signal and emits per-read repeat counts with confidence, followed by uncertainty-aware allele clustering.

Even simpler:

> The thesis builds a model that listens directly to the nanopore signal rhythm of repeated `CAG` units and counts the repeats without depending on noisy basecalled letters.

## 17. Current Interpretation of Key Results

### ND33392

Truth:

```text
57/17
```

DeepRepeat:

```text
18/58
```

Interpretation: close to truth.

STRique:

```text
18/59
```

Interpretation: close to truth, slightly high.

WarpSTR small subset:

```text
52 bases / 3 = about 17 repeats
60 bases / 3 = about 20 repeats for basecall-derived estimate
```

Interpretation: this small subset captures mainly the short allele and misses the expanded allele.

### REL3_WARPSTR_OK

This is not one of the Monteys et al. ground-truth HD samples. It is useful as a disagreement/failure-mode case.

Observed behavior:

- WarpSTR and STRique disagree strongly.
- Some WarpSTR outliers are associated with poor mapping or soft clipping.
- Basecalled sequence context supports shorter repeats in some reads where WarpSTR appeared high before unit conversion.

Interpretation:

REL3 is useful for studying failure modes, but it should not be treated as a clean ground-truth validation sample unless independent truth is available.

## 18. Checklist for Future Work

Before writing final thesis results:

- Confirm units for every tool output.
- Convert WarpSTR/basecall base lengths to CAG repeat counts by dividing by 3.
- Do not divide STRique counts by 3.
- Do not divide DeepRepeat GMM/allocr values by 3.
- Regenerate all comparison tables from current outputs.
- Clearly label downsampled results separately from full-sample results.
- Avoid treating partial or interrupted tool runs as clean full results unless documented.

Before implementing the RNN:

- Build the per-read evidence table.
- Verify signal-window extraction on a few reads manually.
- Start with ND33392 as a positive-control sample.
- Use REL3 as a failure-mode/debugging sample, not as primary ground truth.
