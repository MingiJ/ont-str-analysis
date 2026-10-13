# Thesis Defense Preparation

Plain-English rehearsal sheet for defending the HTT CAG raw-signal project in
front of a panel. Every number here was re-reproduced from code or stored
outputs on 2026-10-12 (see "Reproducibility status" at the end). Pair this with
`docs/DECISION_REVIEW_GUIDE.md` (how to review) and
`docs/ALGORITHM_EXPLANATION_FOR_REFERENCE.md` (tool-by-tool mechanics).

## 1. One-paragraph summary (your opening answer)

This thesis does two things. First, it builds a reproducible benchmark of the
three existing signal-level STR callers (WarpSTR, DeepRepeat, STRique) on nine
Huntington (HTT CAG) samples with published Sanger ground truth. Second, it
proposes and rigorously evaluates a new weakly-supervised raw-signal caller
that is trained only on each sample's unordered diploid genotype (never on
per-read labels copied from a competitor), reports calibrated uncertainty, and
can abstain. The honest headline: an independent repeat-duration physics
baseline carries real signal (leave-one-sample-out allele MAE 1.638), but the
neural residual built on top of it does not beat that baseline on held-out
samples. Two external datasets of different sequencing chemistry show the
proxy transfers but narrowly misses predeclared accuracy gates. The
contribution is a disciplined, leakage-controlled evaluation and a clean
negative result about the neural approach, not a claim of state-of-the-art
accuracy.

## 2. Results table (know every row cold)

| Result | Allele MAE | Status | What it means / does NOT mean |
|---|---:|---|---|
| Engineered NumPy MLP | 0.556 | development (tainted) | Lowest number, BUT its signal windows come from the WarpSTR-boundary archive, so it is NOT an independent win. Do not present as beating WarpSTR. |
| WarpSTR | 0.722 | comparator | Strongest published tool after correct bp/3 unit conversion. The bar to clear for an independence-agnostic accuracy claim. |
| DeepRepeat (allocation peaks) | 1.556 | comparator | Allele peaks from allocation histograms; competitive here, but DeepRepeat emits no per-read count (see Panel D) and its GMM misses the short mode in 4/9 samples. |
| Independent repeat-duration | 1.638 | development baseline (clean) | Your defensible headline. Pure physics on independently mapped boundaries; no competitor input. No uncertainty/abstention, so not yet a deployable caller. |
| STRique | 1.667 | comparator | Slightly worse than your duration baseline on these nine. |
| Fixed ACF-normalized duration | 1.414 | exploratory | Feature chosen after seeing these nine samples. NOT a benchmark win; a hypothesis needing new data. |
| Nested duration/ACF selection | 1.725 | protocol-correct diagnostic | When feature choice is made without peeking at the held-out truth, it does NOT beat plain duration (1.638). This is the honest version of the 1.414 number. |
| Weak-supervised RNN (candidate) | 5.775 | negative result | Neural residual is harmful relative to duration. A controlled negative finding, not a bug. |
| Weak-supervised RNN (resolved) | 4.400 | negative result | Error only on the 5/9 folds it did not abstain on; must always be read with its 0.556 coverage, never alone. |
| Coriell external, ACF | 2.894 | confirmatory (2 samples) | Different chemistry; proxy transfers but direction reverses between the 2 samples, so weak heterogeneous support. Now exposed. |
| Coriell external, duration | 3.103 | confirmatory (2 samples) | Companion to the above. |
| MASTR external, ACF | 3.186 | confirmatory (4 samples) | FAILED predeclared pooled gate (<=3.0) and the expanded-72 long-allele error was 5.781 (gate <=5.0). A clean, frozen negative confirmation. |
| MASTR external, duration | 4.622 | diagnostic only | Worse than ACF; by design cannot change the frozen decision. |

## 3. What you CLAIM vs what you explicitly do NOT claim

You CLAIM:
- A reproducible nine-sample benchmark of WarpSTR, DeepRepeat, STRique with a
  documented one-time per-tool unit conversion (WarpSTR/basecall bp/3; STRique
  and DeepRepeat already counts).
- An independent raw-signal boundary mapper (BAM CIGAR -> native FAST5 events
  -> raw samples) that does not inherit WarpSTR coordinates, read-success, or
  per-read allele groups.
- That independently mapped repeat DURATION is a genuine, physically meaningful
  predictor of CAG count (1.638 LOSO), reproducible by a frozen script.
- A leakage-controlled nested LOSO protocol, with unit tests proving training
  never consults per-read competitor labels.
- A rigorous NEGATIVE result: the proposed Conv-BiRNN residual does not improve
  on the duration baseline under the same protocol.

You do NOT claim:
- State-of-the-art accuracy, or that you beat WarpSTR on raw error.
- That the 0.556 MLP is an independent result (it uses WarpSTR-derived windows).
- That the ACF periodicity feature is a confirmed win (it is exploratory).
- That the external samples pass clinical validity; they are small transfer
  tests, one of which failed its predeclared gate.
- First-ever raw-signal / neural / sample-level STR caller (see novelty below).

## 4. The four most likely panel attacks and your answers

Attack 1 -- "Raw-signal STR calling is already done (NanoSatellite, STRique,
DeepRepeat, WarpSTR). What is new?"
Answer: Agreed, and the prior-art audit in PROPOSED_RNN_ALGORITHM_PLAN.md says
so explicitly. The claim is NOT "first neural raw-signal caller." It is the
narrow combination: unordered sample-level diploid supervision + latent
per-read allele assignment + a train-only physical duration prior + calibrated
heteroscedastic uncertainty with abstention + nested sample-disjoint
evaluation. Defend the combination and the evaluation discipline, never the
broad idea.

Attack 2 -- "Only nine samples. How can anything generalize?"
Answer: That is exactly why the unit of splitting is the SAMPLE, not the read.
Reads from one person share genotype, prep, and flow-cell, so a random read
split leaks and inflates the score. We use leave-one-sample-out, nested LOSO
whenever any threshold/epoch/feature is chosen, and unit tests that confirm
changing the per-read group label does not change training. We also went and
acquired two independent external cohorts (Coriell, MASTR) of different
chemistry to test transfer rather than resting on the nine.

Attack 3 -- "Your table shows 0.556, lower than WarpSTR's 0.722. So you won."
Answer: No, and I want to be the one to say so. That 0.556 MLP draws its signal
windows from the WarpSTR-boundary archive, so it partly re-uses the tool it is
meant to beat. I do not present it as an independent result. My defensible
independent number is the duration baseline at 1.638, produced from boundaries
mapped without any WarpSTR input. Owning this distinction is the point of the
independence discipline.

Attack 4 -- "Your neural model failed. Why is that a thesis?"
Answer: Because it failed under a trustworthy protocol, which makes it a result,
not a bug. The duration physics is strong; the neural residual was measured
under identical nested LOSO folds and shown to be harmful (candidate MAE 5.775
vs duration 1.638), and the corrected model-selection protocol detects and
rejects that degradation (7 of 9 folds fall back to the untrained epoch-0
duration prior). The known failure mode is concrete: soft assignment collapses
to the genotype midpoint; hard assignment compresses expanded counts toward
~40. A rigorous negative result saves the next researcher a year.

## 5. Limitations to state before the panel does

- Single locus only (HTT CAG). No claim beyond it.
- Nine development samples; the engineered MLP and the ACF feature were shaped
  by looking at those nine, so their numbers are development, not confirmatory.
- ND33392 influenced design decisions and is no longer an untouched holdout.
- Both external gates: Coriell gives only weak, direction-reversing support;
  MASTR FAILED its predeclared thresholds (pooled 3.186 > 3.0; expanded-72
  error 5.781 > 5.0). Present these as a passed PROCESS with a missed accuracy
  target, not as a pass.
- The duration baseline has no uncertainty model or abstention, so it is a
  physics sanity check, not a deployable clinical caller.

## 6. Reproducibility story (lead with this; it is a genuine strength)

- 68 focused unit tests pass under `.venv/bin/python -m unittest discover -s
  src/algorithm -p 'test_*.py'`, including leakage tests (changing group_label
  does not change training or baseline predictions) and LOSO holdout
  disjointness.
- The 1.638 duration result and the 1.414/1.725 periodicity results are
  regenerated by frozen scripts (evaluate_repeat_duration_loso.py,
  evaluate_repeat_periodicity_loso.py).
- The benchmark (0.556/0.889 WarpSTR, 1.889/1.444 STRique, 4/9 DeepRepeat
  missed-short, zero failures) regenerates from compare_ground_truth.py and
  writes a failure table so partial outputs can never silently become evidence.
- External and MASTR confirmations use split predict/score scripts: prediction
  inputs and code are SHA-256 hashed, predictions are sealed, and the truth
  manifest is only opened by the score step AFTER the prediction hash verifies.

## 7. Mock defense -- the ten reviewer questions, with model answers

These mirror section 7 of DECISION_REVIEW_GUIDE.md. Practice saying each answer
out loud for each result.

1. Truth: what is trusted and in what unit? Sanger CAG repeat counts per sample
   (unordered diploid pair). All tool outputs are converted once into CAG
   repeats before comparison; WarpSTR/basecall divide by 3, STRique/DeepRepeat
   are already counts.
2. Independence: did a competitor provide windows, labels, counts, or filtering?
   For the 1.638 duration result, no -- boundaries come from BAM/CIGAR/native
   FAST5. For the 0.556 MLP, yes -- it uses WarpSTR-boundary windows, which is
   why I do not claim it as independent.
3. Split: are all reads of a test sample absent from fitting and selection? Yes.
   Evaluation is leave-one-sample-out; the held-out person contributes nothing
   to fitting or to model/feature/epoch choice.
4. Selection: was the feature/epoch/threshold chosen using only inner
   train/validation samples? Yes for the nested results. The fixed 1.414 ACF is
   flagged as exploratory precisely because it was chosen after seeing all nine.
5. Baseline: does it beat raw mapped-repeat duration under identical folds? The
   neural residual does not (5.775 vs 1.638); the nested ACF selector does not
   (1.725 vs 1.638). That is the core negative finding.
6. Coverage: did accuracy improve only by abstaining on hard samples? The RNN
   resolved only 5/9 folds, so its 4.400 resolved MAE must be read with 0.556
   coverage. Low error by rejecting the expanded samples is not success.
7. Per-fold behavior: does any improvement hold across expanded and normal
   alleles, or ride on one sample? The 1.414 vs 1.725 gap is dominated by one
   sample (GM04723), which is why the fixed number is not trusted.
8. Reproducibility: is there a command, frozen manifest, output table, leakage
   test, and seed? Yes for every headline number (see section 6).
9. Novelty: is the claim the precise combination, not the broad published idea?
   Yes -- see Attack 1. The broad idea is explicitly credited to prior work.
10. Status language: is each number labeled development, confirmatory, or
    negative? Yes -- that labeling is the table in section 2 and is enforced in
    the docs.


## 8. Latest comparison figures and efficiency (2026-10-13)

Added the supervisor-requested comparisons (DeepRepeat Fig. 4 A/D style),
generated reproducibly by `src/algorithm/make_comparison_figures.py`:

- **Panel A** (`paper/figures/panel_a_error_vs_length.png`): allele error vs.
  true repeat length across the nine samples. The proposed caller's error grows
  on the expansions (57 -> ~4, 72 -> ~8 repeats) while WarpSTR stays flat. Mean
  absolute allele error: WarpSTR 0.722, DeepRepeat 1.556, Proposed 1.638,
  STRique 1.667.
- **Panel D** (`paper/figures/panel_d_single_read_distribution.png`):
  density-normalised per-read estimate distributions for ND33392 (17/57) and
  GM04723 (17/72). WarpSTR and STRique show sharp bimodal peaks; the proposed
  caller separates the two alleles per read (directly answering the supervisor's
  ND33392 "half the reads ~17, half ~57" note) but with a noisier long-allele
  mode, consistent with the duration-ruler limitation. DeepRepeat is omitted
  here because its `fs.more` output carries only an allele assignment, not a
  per-read count.
- **Runtime / RAM** (`paper/figures/runtime_memory_comparison.md`): the proposed
  caller runs the full nine-fold LOSO in 2.05 s wall / 222 MB peak RAM
  (measured); the signal-DTW tools are minutes-to-hours and GB-scale. A
  controlled same-hardware tool runtime/RAM benchmark remains a supplementary
  TODO.

Panel-talking point: the proposed caller is competitive with DeepRepeat/STRique,
fully independent of WarpSTR's boundaries, and orders of magnitude lighter, but
does not beat WarpSTR on raw accuracy. Its remaining error is concentrated on
the expanded alleles (Panel A), which is the duration-ruler limitation and the
natural target of future work.
