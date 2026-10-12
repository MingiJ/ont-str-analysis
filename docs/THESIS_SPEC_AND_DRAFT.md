# Thesis Specification and Draft

Title: **Direct Estimation of Short Tandem Repeat Expansions from Raw Nanopore Signals using a Deep Recurrent Neural Network**

Document type: Thesis submitted in partial fulfilment of the requirements for the degree of Master of Science in Computer Science.

Institution: Warsaw University of Technology, Warsaw, Masovian Voivodeship, Poland.

Author: Jeff Kimingi Karanja, ID 342068.

Supervisor: Kuśmirek Wiktor.

## Abstract

To be completed after the thesis is finalized.

## 1. Introduction

Short Tandem Repeats (STRs) are genomic regions made up of repeating motifs of 2-6 base pairs. The number of repeat units can vary substantially across individuals, and expansions beyond healthy ranges are a known cause of more than fifty neurological and developmental disorders, including Huntington's disease (HTT CAG), Fragile X syndrome, and various ataxias. Accurate repeat counting is therefore essential for diagnosis, prognosis, and research into disease mechanisms.

Oxford Nanopore Technologies (ONT) sequencing offers a major advantage for STR analysis because long reads can span entire repeat tracts and their flanking regions. However, STRs are precisely the regions where basecalling is most error-prone. The repetitive signal patterns create insertion/deletion errors in the basecalled sequence, and these errors propagate into inaccurate repeat length estimates. Tools that rely on basecalled sequences can therefore be fundamentally limited for long, homogeneous repeats.

This thesis targets a different approach: direct estimation of repeat length from raw nanopore signal. The central hypothesis is that the periodic nucleotide sequence of an STR creates a corresponding periodic pattern in the electrical current. A model that learns these patterns directly from signal should reduce the error introduced by basecalling and improve repeat length estimation.

Purpose and scope. The primary goal of this thesis is to develop and evaluate a novel deep recurrent neural network (RNN) that predicts STR repeat counts directly from raw nanopore signal. The initial scope focuses on the HTT CAG locus because it is clinically relevant, has published ground-truth allele sizes, and provides a well-defined benchmark for evaluating new methods.

Why benchmarks appear in this report. Before proposing a new algorithm, it is essential to establish a reproducible baseline: how do existing signal-level methods perform on the same data and ground truth? This baseline work is not the final objective; it is a prerequisite that validates the dataset and evaluation pipeline, reveals current failure modes, and defines the performance targets the novel algorithm must exceed. The benchmark pipeline and initial results presented later in this thesis therefore serve as a foundation for the planned RNN model.

Thesis contributions to date:

- A reproducible runner for WarpSTR, DeepRepeat, and STRique that standardizes inputs and outputs.
- A multi-sample evaluation on HTT CAG ground-truth data.
- Quantitative baseline metrics and failure-mode analysis that guide algorithm design.

Planned contribution in progress: the deep RNN model for direct signal-level repeat counting, trained and evaluated using the same dataset and metrics described here.

## 2. Literature Review

This section is to be completed with a review of existing research on STR analysis, nanopore sequencing, and deep learning applications in genomics.

STR expansions are a common cause of inherited neurological disorders, including Huntington's disease, Fragile X syndrome, and several ataxias. Accurately quantifying repeat length is essential for diagnosis and for understanding genotype-phenotype relationships. Short-read sequencing has difficulty spanning long repeats, making long-read technologies such as Oxford Nanopore Technologies (ONT) attractive for STR analysis.

However, repeat tracts are challenging for basecalling due to homopolymer-like signal patterns, leading to insertions/deletions and inaccurate repeat counts. This has motivated signal-level methods that bypass or reduce dependence on basecalled sequences. STRique uses nanopore signal and flanking sequence anchors to count repeats directly. DeepRepeat applies deep learning to identify repeat regions and provides per-read quality metrics that can be used for downstream inference. WarpSTR aligns raw signal to an expected repeat pattern using a finite-state model and DTW, then clusters per-read counts into alleles.

Ground-truth HTT CAG sizes for the samples in this thesis are taken from Supplementary Table S4 of Monteys et al. (2017), providing reliable labels for tool benchmarking and error analysis.

## 3. Proposed Methodology and Implementation

This section separates completed baseline work from the planned deep RNN algorithm. The baseline establishes the evaluation framework and current state-of-the-art performance, while the RNN implementation is the intended core contribution of the thesis.

### 3.1 Baseline Evaluation Pipeline (Completed)

#### 3.1.1 Data and Locus

The baseline evaluation focuses on HTT CAG repeats at `chr4:3074876-3074933` with motif `CAG`. Nine samples with published ground-truth allele sizes are used: GM04723, ND30015, ND30016, ND30047, ND30422, ND30626, ND31551, ND33392, and ND33947. Ground-truth allele sizes are taken from Supplementary Table S4 in Monteys et al. (2017).

Each sample contains:

- Raw signal in single FAST5 files.
- BAM alignments.
- Reference genome context for locus localization.
- Optional f5index files for DeepRepeat.

#### 3.1.2 Runner Architecture

A reproducible runner is implemented to execute each tool consistently:

- WarpSTR: auto-generated config per sample; outputs per-read repeat calls and allele peaks.
- DeepRepeat: validates f5index, filters BAM reads to ensure index consistency, and parses logs for GMM peaks and allocation histograms.
- STRique: configured by locus TSV; outputs per-read counts.

Outputs are standardized and stored under `ont-str-runner/work/` with tool-specific folders for cross-tool comparisons.

#### 3.1.3 Baseline Metrics

Allele-level accuracy is measured using mean absolute error (MAE) between predicted and ground-truth repeat counts, evaluated separately for the long and short alleles. To normalize tools with different outputs:

- WarpSTR/basecall peaks in the historical benchmark manuscript were converted to repeat counts by dividing base-pair length by 3 and rounding.
- STRique per-read counts are filtered for zeros and extreme outliers before peak calling.
- DeepRepeat does not emit repeat counts; its performance is assessed by examining log-derived GMM peaks and allocation histograms.

Note: later repository analysis found that some WarpSTR/basecall outputs may already be repeat counts in the current output format. The historical benchmark manuscript is preserved in `paper/htt_cag_multisample_acm_bcb.tex`; current regenerated comparisons should document which interpretation is being used.

### 3.2 Proposed Deep RNN Algorithm (In Progress)

#### 3.2.1 Core Concept

The novel method treats STR quantification as a signal-pattern recognition task. A repetitive nucleotide motif produces a periodic waveform in the nanopore current. By learning the periodicity and boundaries of that waveform, the model can estimate repeat length directly from raw signal, bypassing basecalling.

#### 3.2.2 Input and Pre-processing (Planned)

- Extract raw signal from FAST5/POD5 using `ont-fast5-api` or `pod5`.
- Identify reads overlapping the target locus using BAM alignments.
- Extract and normalize the signal segment corresponding to the STR locus using z-score or robust normalization.
- Optionally use sliding windows or segmentation to stabilize signal length across reads.

#### 3.2.3 Model Architecture (Planned)

A recurrent neural network (LSTM or GRU) is proposed due to its strength in sequential data and its ability to capture periodic patterns over long ranges. The model will ingest normalized signal and output either:

- A direct regression estimate of repeat count.
- A boundary-aware estimate where repeat start/end are detected and the count is derived from the signal length.

#### 3.2.4 Training Labels (Planned)

Labels will be derived from ground-truth allele sizes associated with each sample. If per-read allele assignment is ambiguous, probabilistic labeling or a mixture model will be used to account for the two alleles.

#### 3.2.5 Integration with Baseline Framework (Planned)

The RNN model will be evaluated on the same dataset and with the same metrics as the baselines to ensure fair comparison. The baseline pipeline ensures that improvements are measured against state-of-the-art signal-level approaches rather than against basecall-only methods.

### 3.3 Implementation Status

- Completed: baseline pipeline, dataset organization, reproducibility documentation, and initial baseline analysis.
- In progress: signal windowing strategy, model implementation, and training pipeline.
- Planned: full RNN training, hyperparameter optimization, and benchmark comparison.

## 4. Testing and Validation Strategy

A rigorous validation strategy is essential to demonstrate the superiority of the proposed method. Evaluation will be multi-faceted, assessing both quantitative accuracy and clinical relevance.

### 4.1 Performance Metrics

Quantitative accuracy will be evaluated using standard regression metrics.

Mean Absolute Error:

`MAE = (1/n) * sum(|yi - yhat_i|)`

This provides a clear, interpretable measure of the average error in repeat count estimation.

Clinical relevance will be measured using classification accuracy. For a given STR disorder, clinically relevant thresholds will define normal, intermediate/premutation, and full-mutation/pathogenic ranges. Predictions will be classified into these categories, because clinical category can be more important than exact repeat count.

### 4.2 Benchmarks for Comparison

The novel algorithm will be benchmarked against:

- WarpSTR.
- DeepRepeat.
- STRique.
- Basecall-derived repeat estimates where available.

These comparisons test whether direct raw-signal modeling improves over existing signal-level and basecall-dependent approaches.

### 4.3 Validation Process

The dataset will be partitioned into three distinct, non-overlapping sets:

- Training set, 70%: used to train neural network parameters.
- Validation set, 15%: used for hyperparameter tuning and overfitting control.
- Test set, 15%: held out until final evaluation and used for final reported accuracy/generalization.

## 5. Data Requirements

The project requires high-quality training and testing data, comprising both simulated and real-world examples.

### 5.1 Real-World Data

Purpose: ensure the model is robust and performs well on real, noisy experimental data from human samples.

Public sources: publicly available, high-coverage nanopore sequencing datasets.

Required components for each real-world sample:

- Raw signal data: complete raw FAST5 or POD5 files from nanopore sequencing runs.
- Alignment data: BAM/CRAM files for locating reads overlapping the STR locus.
- Ground-truth allele sizes where available.

## 6. Results

This section reports baseline results from existing signal-level tools. These results are not the final thesis outcome but establish the reference point that the novel RNN model must exceed.

### 6.1 Baseline Performance on HTT CAG Samples

Across nine ground-truth HTT CAG samples:

- WarpSTR allele peaks align most closely with ground truth, with MAE of 0.56 repeats for the long allele and 0.89 for the short allele.
- Basecall-derived peaks are less accurate, with MAE 1.56 long and 2.22 short, confirming the limitations of basecalling for homogeneous repeats.
- STRique reports repeat counts for all samples but shows higher error, with MAE 1.89 long and 1.44 short, and a tendency to overestimate long alleles.

### 6.2 DeepRepeat Observations

DeepRepeat does not directly output repeat counts. Instead, log-derived GMM peaks and allocation histograms are analysed. In 4 of 9 samples, the log shows a clear short-allele allocation peak that is not reflected in the reported GMM peaks. This suggests a weakness in peak selection/clustering rather than a failure of repeat detection.

### 6.3 Summary of Baseline Findings

These baseline results establish three key observations:

- Signal-level alignment with WarpSTR currently yields the best allele-level accuracy.
- Basecalling-dependent approaches show higher error in long, homogeneous repeats.
- Failure modes are concentrated in boundary ambiguity and allele-peak selection.

These observations define explicit targets for the planned RNN model: improved boundary detection, more robust allele separation, and a direct signal-based repeat estimate that reduces reliance on basecalling.

## 7. Discussion

This section is to be completed with an interpretation of the results, including analysis of limitations and future directions.

## 8. Conclusion

This section is to be completed summarizing the findings and contributions of the thesis.

## References

This section is to be completed with all cited works in proper citation format.

## Appendices

This section is to be completed with supplementary material, such as code listings or detailed data tables.
