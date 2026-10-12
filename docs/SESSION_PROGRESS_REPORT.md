# Session Progress Report

Generated from `SESSION_STATE.md` and current workspace checks.

## Current Truth-Benchmark Note

As of 2026-06-05, the published HTT CAG truth benchmark is complete:
WarpSTR 9/9, DeepRepeat 9/9, STRique 9/9, and 0 failure/incomplete records.
Use `ont-str-runner/work/analysis/ground_truth_comparison.csv` and
`ont-str-runner/work/analysis/benchmark_report.md` as the final benchmark
sources. Older partial-run notes in this report are historical debugging
context, not final thesis metrics.

## Plain-English Takeaway

The project has moved from tool benchmarking into the first working prototype of the new thesis algorithm. The current pipeline can build per-read evidence tables, extract normalized raw-signal windows, train a simple ridge baseline, and train a lightweight NumPy neural baseline. The neural prototype slightly improves overall test MAE versus the ridge baseline, but it still fails badly on rare long-allele reads, so the next important step is improving data balance and model structure.

## Current Workspace State

Tracked files modified:

- `ont-str-runner/scripts/compare_ground_truth.py`
- `ont-str-runner/scripts/make_warpstr_config.sh`
- `ont-str-runner/scripts/run_deeprepeat.sh`
- `ont-str-runner/scripts/run_warpstr.sh`
- `src/algorithm/README.md`

New or untracked important files:

- `SESSION_STATE.md`
- `docs/ALGORITHM_EXPLANATION_FOR_REFERENCE.md`
- `docs/PROPOSED_RNN_ALGORITHM_PLAN.md`
- `docs/THESIS_SPEC_AND_DRAFT.md`
- `docs/SESSION_PROGRESS_REPORT.md`
- `src/algorithm/evidence_table.py`
- `src/algorithm/signal_windows.py`
- `src/algorithm/dataset.py`
- `src/algorithm/baseline.py`
- `src/algorithm/neural_baseline.py`
- `ont-str-runner/configs/rel3_htt_cag.bed`
- `ont-str-runner/configs/rel3_htt_region.bed`

Disk state at the time of this report:

- `/home/jkaranja/workdir` has about `36G` free.
- `ont-str-runner/data/ND33392` uses about `7.5G`.
- `ont-str-runner/data/ND33392_WARPSTR_SMALL` uses about `166M`.
- `ont-str-runner/work/analysis` uses about `4.2M`.

## Benchmarking Work Completed

### REL3 Setup

- Downloaded and prepared REL3 chr4 BAM and index.
- Extracted FAST5 archive under `/home/jkaranja/workdir/rel3/${chr}/${fn}/`.
- Created HTT BED files:
  - `ont-str-runner/configs/rel3_htt_region.bed`
  - `ont-str-runner/configs/rel3_htt_cag.bed`
- Built REL3 HTT subset BAMs:
  - Broad region: `1259` reads.
  - Exact CAG region: `179` reads.
- Created and repaired a matched filtered benchmark set: `REL3_WARPSTR_OK`.

### REL3 Tool Results

- WarpSTR completed for `REL3_WARPSTR_OK`.
- STRique completed or is available for `REL3_WARPSTR_OK`.
- DeepRepeat completed for `REL3_WARPSTR_OK`.

Current REL3 summary from `ont-str-runner/work/rel3/benchmark_summary.tsv`:

- WarpSTR rows: `54`.
- WarpSTR saved rows: `49`.
- WarpSTR main-range median: `49`.
- WarpSTR outliers above `100`: `14`.
- STRique rows: `53`.
- STRique nonzero rows: `31`.
- STRique main-range median: `18`.
- STRique outliers above `100`: `6`.
- DeepRepeat status: `Testing Finished!`.
- DeepRepeat `fs.more` rows: `48`.
- DeepRepeat GMM: `REL3_WARPSTR_OK_htt-CAG [0, 0]`.
- DeepRepeat allocation mode: `2:19`.

### REL3 Interpretation

- WarpSTR main-range results support a long-like count around `49`.
- STRique main-range results support a normal-length count around `18`.
- DeepRepeat completed but its GMM output is not a reliable allele call here because it reports `[0, 0]`.
- Outlier analysis showed WarpSTR and STRique fail on different reads.
- Alignment context suggests WarpSTR extreme outliers are mostly low-MAPQ or soft-clipped reads.
- Basecalled motif context for main disagreement reads supports short/normal CAG runs more than a long `~52` CAG allele.
- Current interpretation: REL3 is a useful failure-mode case for testing boundary robustness and outlier handling.

## ND33392 Work Completed

### Data Preparation

- Downloaded `ND33392` archive to `ont-str-runner/data/ND33392/ND33392.tar.gz.1`.
- Verified the archive with `gzip -t`.
- Extracted files include:
  - `3971` FAST5 files.
  - `ND33392.bam`.
  - `ND33392.bam.bai`.
  - `htt.f5index`.
  - `workspace/pass/ND33392.fq`.

Ground truth:

- ND33392 expected HTT CAG alleles are `57/17`.

### DeepRepeat

- Completed successfully.
- Log: `ont-str-runner/work/deeprepeat/ND33392/htt.log`.
- Completion marker: `Testing Finished!`.
- `ND33392.fs.more` has `3756` rows.
- GMM peaks: `18,58`, very close to truth `17,57`.

### STRique

- Output exists at `ont-str-runner/work/strique/ND33392.txt`.
- Current comparison file reports:
  - `3804` rows.
  - Filtered short peak `18`.
  - Filtered long peak `59`.
- Caveat: this output was not observed completing cleanly in-session, so it should be described carefully.

### WarpSTR Full Sample

- Full ND33392 WarpSTR run did not complete within timeout.
- Partial output exists at `ont-str-runner/work/warpstr/ND33392/HTT_CAG/overview.csv`.
- The partial output has `3725` rows, but only early columns.
- No completed `predictions/alleles.csv` exists for full ND33392.

### WarpSTR Small Subset

- Created `ND33392_WARPSTR_SMALL` as a matched downsampled subset.
- Selected `240` FAST5 entries using symlinks rather than copying data.
- Created filtered/indexed BAM:
  - `ND33392_WARPSTR_SMALL.bam`
  - `ND33392_WARPSTR_SMALL.bam.bai`
- WarpSTR completed on this subset.
- Output:
  - `overview.csv` has `212` rows.
  - `predictions/alleles.csv` reports WarpSTR allele field `52`, basecall allele field `60`.
- Important correction: verified WarpSTR outputs are sequence/base lengths in this context and should be divided by `3` for CAG repeat count.
- Therefore `ND33392_WARPSTR_SMALL` corresponds roughly to `17/20`, not a reliable long-allele call.

Current ND33392 conclusion:

- DeepRepeat and STRique best match the expected `57/17`.
- Full-sample WarpSTR is incomplete.
- Small-subset WarpSTR does not recover the long allele correctly.

## Script Fixes Completed

### `run_warpstr.sh`

- Removed dependency on `rg` for parsing `reference_path`.
- Replaced it with Bash regex parsing so the script works in this environment.

### `run_deeprepeat.sh`

- Replaced local `python` calls with `python3` because this VM has no `python` command.
- Kept robustness around f5index/BAM filtering from earlier work.

### `make_warpstr_config.sh`

- Replaced `python` with `python3`.

### `compare_ground_truth.py`

- Added parsing for one-allele WarpSTR output where the missing allele is `-`.
- Corrected WarpSTR/basecall unit handling after checking WarpSTR source in Docker:
  - WarpSTR/basecall allele fields are base/sequence lengths.
  - Convert to CAG repeat counts by dividing by `3` and rounding.
- Regenerated `ont-str-runner/work/analysis/ground_truth_comparison.csv`.

## Current Ground-Truth Comparison

Current key rows from `ont-str-runner/work/analysis/ground_truth_comparison.csv`:

### `ND33392`

- Truth: `57/17`.
- DeepRepeat GMM: `18,58`.
- STRique peaks: `18,59`.
- WarpSTR full sample: incomplete.

### `ND33392_WARPSTR_SMALL`

- Truth inherited from ND33392: `57/17`.
- WarpSTR/basecall converted estimates: about `17/20`.
- This should be treated only as a downsampled feasibility result, not a full-sample result.

Most other listed samples are currently present in the comparison table but do not yet have newly generated result rows in this workspace.

## Thesis and Documentation Work Completed

Created thesis planning and reference documents:

- `docs/THESIS_SPEC_AND_DRAFT.md`
- `docs/PROPOSED_RNN_ALGORITHM_PLAN.md`
- `docs/ALGORITHM_EXPLANATION_FOR_REFERENCE.md`

The thesis goal is now explicitly captured:

- Title: `Direct Estimation of Short Tandem Repeat Expansions from Raw Nanopore Signals using a Deep Recurrent Neural Network`.
- Main objective: build a novel raw-signal STR caller better than WarpSTR, DeepRepeat, and STRique.
- Benchmarking is framed as prerequisite baseline work, not the final contribution.

The proposed algorithm direction is:

- Raw-signal input around the HTT CAG locus.
- Boundary-aware recurrent model.
- Per-read repeat count prediction.
- Confidence or uncertainty output.
- Sample-level allele clustering.

## Algorithm Pipeline Implemented

### Evidence Table

Implemented:

- `src/algorithm/evidence_table.py`

Output:

- `ont-str-runner/work/analysis/evidence_table.tsv`

Purpose:

- Join per-read evidence from f5index, WarpSTR, STRique, DeepRepeat, truth labels, and REL3 alignment context.
- Provide the manifest for later signal extraction and model training.

Current result:

- Wrote `4265` rows for:
  - `ND33392`
  - `ND33392_WARPSTR_SMALL`
  - `REL3_WARPSTR_OK`

### Signal Windows

Implemented:

- `src/algorithm/signal_windows.py`

Outputs:

- `ont-str-runner/work/analysis/signal_windows.npz`
- `ont-str-runner/work/analysis/signal_windows.index.tsv`

Details:

- Uses `.venv/bin/python` because system `python3` lacks `h5py`.
- Opens FAST5 files via `h5py`.
- Extracts signal windows using known raw-signal boundaries.
- Adds padding.
- Normalizes with median/MAD.
- Stores fixed-width arrays.

Current extraction result:

- `266` signal windows total.
- `212` from `ND33392_WARPSTR_SMALL`.
- `54` from `REL3_WARPSTR_OK`.
- With `--max-signal-len 20000`, truncation was:
  - `0/212` for `ND33392_WARPSTR_SMALL`.
  - `13/54` for `REL3_WARPSTR_OK`.

### Dataset Loader

Implemented:

- `src/algorithm/dataset.py`

It:

- Loads `signal_windows.npz`.
- Loads `signal_windows.index.tsv`.
- Maps weak labels:
  - `short_like`
  - `long_like`
  - `unknown_truth`
- Computes compact signal-summary features.

Current labeled dataset:

- `266` rows total.
- `212` labeled rows.
- `54` unknown-truth rows from REL3.
- Labeled split is highly imbalanced:
  - `201` short-like.
  - `11` long-like.

### Ridge Baseline

Implemented:

- `src/algorithm/baseline.py`

Outputs:

- `ont-str-runner/work/analysis/baseline_predictions.tsv`
- `ont-str-runner/work/analysis/baseline_summary.tsv`

Current ridge baseline result:

- Rows total: `266`.
- Labeled rows: `212`.
- Train rows: `170`.
- Test rows: `42`.
- Test MAE: `6.937`.
- Short-like test MAE: `6.645`.
- Long-like test MAE: `12.784`.

Interpretation:

- This is a weak baseline.
- It struggles, especially on long alleles.
- It is useful as a sanity-check comparator for the RNN.

### NumPy Neural Prototype

Implemented:

- `src/algorithm/neural_baseline.py`

Outputs:

- `ont-str-runner/work/analysis/neural_baseline_predictions.tsv`
- `ont-str-runner/work/analysis/neural_baseline_summary.tsv`

Architecture:

- One-hidden-layer MLP.
- Downsampled raw-signal windows.
- Inverse-label weighting.
- Adam optimizer.
- Internal validation split.
- No PyTorch/TensorFlow/JAX dependency.

Current neural baseline result:

- Rows total: `266`.
- Labeled rows: `212`.
- Train rows: `170`.
- Fit rows: `145`.
- Validation rows: `25`.
- Test rows: `42`.
- Best epoch: `58`.
- Validation MAE at best epoch: `5.507`.
- Test MAE: `5.746`.
- Short-like test MAE: `4.413`.
- Long-like test MAE: `32.418`.

Interpretation:

- The neural prototype improves total MAE compared with ridge: `5.746` vs `6.937`.
- It performs much worse on rare long-like reads: `32.418` long-like test MAE.
- This means it is not thesis-ready.
- The current bottleneck is data imbalance and weak per-read labeling.

## Verification Completed

Compilation passed for:

- `src/algorithm/evidence_table.py`
- `src/algorithm/signal_windows.py`
- `src/algorithm/dataset.py`
- `src/algorithm/baseline.py`
- `src/algorithm/neural_baseline.py`
- `ont-str-runner/scripts/compare_ground_truth.py`

## Important Caveats

The biggest scientific caveat:

- Current per-read labels are weak labels derived from sample-level truth and tool-derived grouping.
- They are not manual per-read allele labels.

The biggest data caveat:

- The labeled signal-window set is dominated by short-like reads:
  - `201` short-like.
  - `11` long-like.

The biggest modeling caveat:

- The NumPy MLP uses coarse downsampling.
- It likely loses local repeat-boundary structure.
- A real sequence model or convolutional/recurrent boundary-aware model is still needed.

The biggest benchmark caveat:

- Full ND33392 WarpSTR did not complete.
- STRique ND33392 output exists and looks good, but completion was not cleanly observed.
- `ND33392_WARPSTR_SMALL` is only a downsampled subset and should not replace full-sample results.

## Recommended Next Step

Focus on improving the algorithm dataset before making the model more complex.

Best next concrete options:

1. Add more labeled long-allele signal windows from completed samples like ND33392 or other Monteys HTT samples.
2. Build a better weak-label assignment method using DeepRepeat/STRique/WarpSTR agreement rather than sample-level truth alone.
3. Add augmentation or oversampling for long-like reads.
4. Replace the MLP with a small sequence-preserving model, ideally a 1D CNN plus GRU/BiGRU.
5. Add sample-level allele clustering from per-read predictions so the model outputs thesis-relevant allele calls, not just per-read regression.
