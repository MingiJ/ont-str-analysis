# OpenCode Session State

Last updated: 2026-06-05

## Current Truth-Benchmark Note

The nine-sample published HTT CAG truth benchmark is now complete and supersedes
older partial-run notes in this file for thesis/paper metrics.

- Final comparison: `ont-str-runner/work/analysis/ground_truth_comparison.csv`
- Final report: `ont-str-runner/work/analysis/benchmark_report.md`
- Failure table: `ont-str-runner/work/analysis/benchmark_failures.tsv`
- Completion: WarpSTR 9/9, DeepRepeat 9/9, STRique 9/9, failures 0

Plain-English takeaway: WarpSTR is strongest overall, STRique completes all
samples but overestimates more often, and DeepRepeat has useful
signal/allocation evidence but weak GMM peak selection for short alleles.

The historical REL3 notes below are still useful for debugging that exploratory
dataset, but they should not be treated as the current truth-benchmark state.

## Goal

Benchmark ONT signal-level STR tools on the REL3 chromosome 4 nanopore human WGS dataset at the HTT CAG repeat.

## Current Checkpoint

- Full chr4 BAM is downloaded: `ont-str-runner/data/REL3/bam/chr4.sorted.bam` (`8.6G`).
- BAM index is downloaded: `ont-str-runner/data/REL3/bam/chr4.sorted.bam.bai`.
- Original FAST5 tar is downloaded: `/home/jkaranja/workdir/rel3-fast5-chr4.part01.tar` (`424G`).
- FAST5 tar has been extracted under `/home/jkaranja/workdir/rel3/${chr}/${fn}/`. The literal `${chr}/${fn}` directory names are unusual, but FAST5 files are present and usable.
- Broad HTT region BED exists: `ont-str-runner/configs/rel3_htt_region.bed` with `chr4 3070000 3240000`.
- Exact HTT CAG BED exists: `ont-str-runner/configs/rel3_htt_cag.bed` with `chr4 3074876 3074933`.
- Broad HTT region subset BAM exists: `ont-str-runner/data/REL3/bam/chr4.sorted.htt_region.bam` with `1259` reads.
- Exact CAG subset BAM exists: `ont-str-runner/data/REL3/bam/chr4.sorted.htt_cag.bam` with `179` reads.
- `REL3.bam` is currently a symlink to `chr4.sorted.htt_cag.bam`.
- CAG motif summary exists: `ont-str-runner/work/rel3/htt_cag_sequence_motif_summary.tsv`.
- FAST5 mapping for CAG reads exists: `ont-str-runner/work/rel3/htt_cag.fast5_map.tsv`.
- `REL3` and `REL3_BENCH` each have `172` selected FAST5 files in `workspace/pass/0`.
- `REL3_WARPSTR_OK` has `54` selected FAST5 files and completed WarpSTR/STRique output.

## Existing Benchmark Results

- `REL3_WARPSTR_OK` completed WarpSTR:
  - `ont-str-runner/work/warpstr/REL3_WARPSTR_OK/HTT_CAG/overview.csv` has `54` result rows.
  - `predictions/alleles.csv` reports WarpSTR allele peak `52`, basecall allele peak `53`.
- `REL3_WARPSTR_OK` completed STRique:
  - `ont-str-runner/work/strique/REL3_WARPSTR_OK.txt` has `53` result rows.
- Summary file exists: `ont-str-runner/work/rel3/benchmark_summary.tsv`.
- `REL3_BENCH` WarpSTR output is incomplete: `overview.csv` has rows but only early columns, no repeat counts.
- `REL3` WarpSTR output is effectively empty: only the `overview.csv` header exists.

## Next Step

Diagnose why `REL3_BENCH` did not finish final WarpSTR repeat calling/genotyping. Prefer repairing or rerunning the 179-read benchmark if feasible. Use `REL3_WARPSTR_OK` as the known-good baseline.

## 2026-05-04 Progress

- Created this session state file for future handoff.
- Found `REL3_BENCH` has only `59` WarpSTR-extracted FAST5 files and `54` annotated FAST5 files, matching the size of the successful `REL3_WARPSTR_OK` benchmark.
- Updated `ont-str-runner/configs/warpstr_REL3_BENCH.yaml` to set `single_read_extraction: False` and `guppy_annotation: False`, mirroring the known-good `REL3_WARPSTR_OK` reuse mode.
- First rerun attempt stopped immediately because `ont-str-runner/scripts/run_warpstr.sh` used `rg`, which is not installed in the shell environment.
- Patched `run_warpstr.sh` to parse `reference_path:` using Bash regex instead of `rg`.
- Second rerun reached TR extraction but failed because 5 FAST5 files existed in the `REL3_BENCH` work list without corresponding files under `fast5/REL3_BENCH/annot/`.
- Copied the 5 missing FAST5 files into `annot/` using Docker because the WarpSTR output directory is root-owned.
- Patched FAST5 analysis aliases in `annot/`: added missing `Basecall_1D_001` aliases from `Basecall_1D_000`, added missing `Segmentation_000` aliases from `Segment_Linear_000`, and ensured per-basecall `Segmentation_<tag>` groups exist.
- Third rerun failed because those 5 copied FAST5 files lack the required `BaseCalled_template/Move` dataset. This cannot be safely fabricated.
- Removed those 5 unusable copies from `work/warpstr/REL3_BENCH/HTT_CAG/fast5/REL3_BENCH/` and its `annot/` subdirectory, leaving the 54 valid annotated reads.
- Fourth rerun still referenced the removed files because `overview.csv` is reused as WarpSTR's read list.
- Removed those 5 read IDs from `work/warpstr/REL3_BENCH/HTT_CAG/overview.csv`, leaving 54 rows.
- Reran WarpSTR for `REL3_BENCH`; it completed in about 8 minutes.
- Completed output: `work/warpstr/REL3_BENCH/HTT_CAG/overview.csv` now has 54 result rows with final columns `saved`, raw/sequence boundaries, `results`, `orig`, and DTW costs.
- Completed allele summary: `work/warpstr/REL3_BENCH/HTT_CAG/predictions/alleles.csv` reports WarpSTR allele `52` and basecall allele `53`.
- State similarity summary exists: `work/warpstr/REL3_BENCH/HTT_CAG/summaries/state_similarity.csv`.
- Important benchmark-set clarification: the clean matched filtered benchmark set is `REL3_WARPSTR_OK`, not `REL3_BENCH`. `REL3_WARPSTR_OK` has 54 f5index entries and 54 WarpSTR result rows. `REL3_BENCH` still has 179 BAM reads and 172 FAST5 files, so tools run directly on it are not matched to the final WarpSTR-valid set unless further filtered.
- A STRique run was accidentally started for `REL3_BENCH`; it was stopped via Docker because it was not the matched filtered benchmark set.
- DeepRepeat has not completed for REL3 yet. The local model archive `/home/jkaranja/workdir/models/trainedmod_32_0.2.tar.gz` fails `gzip -t` with `unexpected end of file`, so it is corrupted/incomplete and must be redownloaded before DeepRepeat can run.
- Started resuming/redownloading the DeepRepeat model from `https://www.openbioinformatics.org/hx1/drmodel/trainedmod_32_0.2.tar.gz` with `wget -c`.
- Download command timed out after 30 minutes at around 47%; no `wget` process remains. Current archive size is about `11G`, still likely incomplete until `gzip -t` succeeds.
- Continued the download with a longer timeout. Download completed: `/home/jkaranja/workdir/models/trainedmod_32_0.2.tar.gz` is `21G` and `gzip -t` passed.
- Extracted model to `/home/jkaranja/workdir/models/trainedmod_32_0.2` (`32G`). Disk is now tight: about `29G` free on `/home/jkaranja/workdir`.
- First DeepRepeat run attempt stopped immediately because `ont-str-runner/scripts/run_deeprepeat.sh` called `python`, but only `python3` is installed on this VM.
- Patched `run_deeprepeat.sh` to use `python3` for local helper snippets.
- Second DeepRepeat run attempt stopped because the filtered sample index is named `htt.f5index`, while the runner expects `HTT_CAG.f5index` when `REPEAT_NAME=HTT_CAG`.
- Added symlink: `ont-str-runner/data/REL3_WARPSTR_OK/HTT_CAG.f5index -> htt.f5index`.
- Patched remaining local `python` calls in `run_deeprepeat.sh` to `python3`.
- DeepRepeat then started with `REPEAT_NAME=HTT_CAG` but failed at model lookup: it searched for `trainedmod_32_0.2/HTT_CAG/AGC_3/50_v0.2motif32/np_dl_3.meta`, which does not exist.
- Docs confirm DeepRepeat should be invoked with repeat/gene name `htt`, not `HTT_CAG`: `run_deeprepeat.sh <SAMPLE> htt chr4:3074876-3074933 CAG`.
- Reran DeepRepeat with the correct repeat/gene name: `DEEPREPEAT_MODEL_DIR=/home/jkaranja/workdir/models/trainedmod_32_0.2 bash ont-str-runner/scripts/run_deeprepeat.sh REL3_WARPSTR_OK htt chr4:3074876-3074933 CAG`.
- DeepRepeat completed successfully. Log: `ont-str-runner/work/deeprepeat/REL3_WARPSTR_OK/htt.log`.
- Completion marker in log: `Testing Finished!`.
- DeepRepeat read-list output: `ont-str-runner/work/deeprepeat/REL3_WARPSTR_OK/REL3_WARPSTR_OK.fs.more` has 48 rows.
- Final GMM line in log: `GMM: REL3_WARPSTR_OK_htt-CAG [0, 0] allocr:2:19, 4:1, 5:2, 6:2, 7:4, 12:1, 15:1, 17:1, 18:2, 20:2, 21:1, 22:1, 24:1, 27:1, 28:3, 29:1, 30:1, 32:3, 254:1,`.
- Updated benchmark summary: `ont-str-runner/work/rel3/benchmark_summary.tsv` now includes DeepRepeat status, fs.more row count, GMM, and allocation counts.
- Disk is tight after model extraction: about 28G free on `/home/jkaranja/workdir`.
- The compressed model archive still exists at `/home/jkaranja/workdir/models/trainedmod_32_0.2.tar.gz` (`21G`). If disk pressure matters, this archive can be deleted after confirming the extracted model directory is enough.
- Compared `REL3_WARPSTR_OK` tool outputs and added robust outlier-aware metrics to `ont-str-runner/work/rel3/benchmark_summary.tsv`.
- Plain-English comparison: WarpSTR strongly supports a long HTT CAG allele around `49-52`; STRique mostly supports the expected normal-length allele around `18-19`; DeepRepeat completed but its GMM/allocation output is not a reliable allele call here because it peaks at `2` and reports `[0, 0]`.
- Outliers are substantial and explain misleading raw means: WarpSTR has `14/49` saved calls above `100`, STRique has `6/31` nonzero calls above `100`, and DeepRepeat has one allocation outlier at `254`.
- Robust main-range summaries: WarpSTR `0-100` median `49`, mean `48.4`; STRique nonzero `1-100` median `18`, mean `19.24`; DeepRepeat allocation `0-100` median `6`, mean `11.60`, mode `2:19`.
- Current interpretation: this REL3 matched subset does not produce concordant biallelic HTT calls across tools. WarpSTR captures the long allele signal, STRique captures the short allele signal, and DeepRepeat's reported GMM misses both meaningful alleles.
- Created read-level join table: `ont-str-runner/work/rel3/rel3_warpstr_ok_read_join.tsv`.
- Join-table coverage: `54` unique read IDs, `47` present in all three tool outputs, `52` in both WarpSTR and STRique, `47` in WarpSTR and DeepRepeat, `47` in STRique and DeepRepeat. There are `2` WarpSTR-only reads and no STRique-only or DeepRepeat-only reads.
- Join-table outlier check: WarpSTR has `14` reads above `100`, STRique has `6`, and none of the outliers overlap between WarpSTR and STRique. This suggests the two tools fail on different reads rather than agreeing on extreme expansions.
- Join-table concordance check: `16` reads have WarpSTR in `45-60` and STRique in `15-25`, meaning the same reads can carry the long-allele signal in WarpSTR while STRique reports normal-length counts.
- Suggested next step: inspect the `16` concordant long-vs-short reads and the separate WarpSTR/STRique outlier reads against alignment/strand/raw-signal context to decide whether WarpSTR is measuring the expanded allele or systematically overcounting this REL3 subset.
- Extracted read-group TSVs under `ont-str-runner/work/rel3/`: `concordant_warpstr_long_strique_short.tsv` (`16` reads), `warpstr_outliers_gt_100.tsv` (`14` reads), `strique_outliers_gt_100.tsv` (`6` reads), and `both_main_discordant.tsv` (`26` reads).
- Created BAM alignment context table: `ont-str-runner/work/rel3/rel3_warpstr_ok_alignment_context.tsv`.
- Alignment context for the `16` WarpSTR-long/STRique-short reads: all have BAM MAPQ `60`; median HTT-locus reference overlap is `50.5` bp; median locus insertion is `0` bp; median locus deletion is `6.5` bp; strand split is balanced (`9` reverse, `7` forward). This means the long-vs-short disagreement is not explained by low mapping quality.
- Alignment context for WarpSTR outliers: median MAPQ is only `2.5`, median soft clipping is `1715.5` bp, and several reads have very low MAPQ (`1-7`). These outliers look mapping/context driven and should be excluded from allele summaries.
- Alignment context for STRique outliers: `5/6` have MAPQ `60`, all are forward-strand, and they do not overlap WarpSTR outliers. These look like a separate STRique-specific failure mode.
- Created basecalled sequence context table: `ont-str-runner/work/rel3/rel3_warpstr_ok_sequence_context.tsv`.
- Basecalled sequence context for the `16` WarpSTR-long/STRique-short reads: median longest uninterrupted `CAG` run is `15`, maximum is `18`; median total `CAG` triplets in the local query window is `25`. The BAM/basecalled sequence therefore supports a short/normal HTT allele much more than a ~`52` CAG allele for these reads.
- Current interpretation after read-context inspection: REL3_WARPSTR_OK likely demonstrates a WarpSTR signal-level overcount or calibration/boundary issue on this subset rather than a clear expanded HTT allele. STRique's main `18-19` calls match the basecalled motif runs better, while WarpSTR's extreme outliers are mostly low-MAPQ/soft-clipped reads.
- Suggested next step: inspect WarpSTR per-read raw-signal boundary outputs for the `16` high-MAPQ disagreement reads, especially `l_start_raw`, `r_end_raw`, DTW costs, and any generated SVG/plot files, to identify why WarpSTR converts short basecalled CAG runs into ~`49-58` signal repeat counts.

## ND33392 Checkpoint

- User provided SRA source archive links for HD fibroblast samples and asked to start with `ND33392` only.
- Disk before download was tight: `/home/jkaranja/workdir` had about `28G` free.
- Downloaded `ND33392` archive from `https://sra-pub-src-2.s3.amazonaws.com/SRR13068459/ND33392.tar.gz.1` to `ont-str-runner/data/ND33392/ND33392.tar.gz.1` (`2.4G`).
- `gzip -t` passed.
- Archive contents: `3971` FAST5 files, `ND33392.bam`, `ND33392.bam.bai`, `htt.f5index`, and `workspace/pass/ND33392.fq`; uncompressed size about `2.58 GiB`.
- Extracted under `ont-str-runner/data/ND33392/`.
- Current free disk after extraction and partial runs was about `23G`; the compressed archive still exists and can be deleted to recover about `2.4G` if needed.
- ND33392 expected HTT CAG reference values from user-provided table: `57/17`.
- `samtools idxstats` confirms hg38/UCSC naming with `chr4`; `samtools view -c ont-str-runner/data/ND33392/ND33392.bam chr4:3074876-3074933` reported `3763` overlapping reads.
- `htt.f5index` has `3971` rows and all referenced FAST5 paths exist.
- Patched `ont-str-runner/scripts/make_warpstr_config.sh` to use `python3` instead of `python` in its path helper because this VM has no `python` command.
- STRique was started with `DATA_ROOT=/home/jkaranja/workdir/ont-str-analysis/ont-str-runner/data bash ont-str-runner/scripts/run_strique.sh ND33392`.
- STRique did not finish within the 30-minute tool timeout and left a still-running Docker container, which was stopped manually. Partial output exists at `ont-str-runner/work/strique/ND33392.txt` with `309` result rows plus header at the time checked. This is partial output, not a completed full-sample STRique result.
- DeepRepeat completed successfully with `DEEPREPEAT_MODEL_DIR=/home/jkaranja/workdir/models/trainedmod_32_0.2 DATA_ROOT=/home/jkaranja/workdir/ont-str-analysis/ont-str-runner/data bash ont-str-runner/scripts/run_deeprepeat.sh ND33392 htt chr4:3074876-3074933 CAG`.
- DeepRepeat output log: `ont-str-runner/work/deeprepeat/ND33392/htt.log`.
- DeepRepeat completion marker: `Testing Finished!`.
- DeepRepeat `ND33392.fs.more` has `3756` rows.
- DeepRepeat GMM result: `ND33392_htt-CAG [18, 58]`, close to expected `17/57`.
- WarpSTR was started with `REFERENCE_FASTA=/home/jkaranja/workdir/references/hg38.chr4.fa DATA_ROOT=/home/jkaranja/workdir/ont-str-analysis/ont-str-runner/data bash ont-str-runner/scripts/run_warpstr.sh ND33392`.
- WarpSTR generated `ont-str-runner/configs/warpstr_ND33392.yaml`, converted single FAST5 to multi FAST5, then entered Guppy annotation for `3725` FAST5 files.
- WarpSTR did not finish within the 1-hour tool timeout and left a still-running Docker container, which was stopped manually.
- Partial WarpSTR output exists at `ont-str-runner/work/warpstr/ND33392/HTT_CAG/overview.csv` with `3725` read rows plus header but only early columns (`read_name,sample,run_id,reverse,sam_dist`). `predictions/alleles.csv` and `summaries/state_similarity.csv` do not exist yet.
- Current ND33392 interpretation: DeepRepeat is the only completed full-tool result so far and matches the expected allele sizes well. STRique and WarpSTR need longer runs or a filtered/downsampled benchmark subset to complete comfortably on this VM.
- Suggested next step for ND33392: parse the DeepRepeat result into a summary table, then decide whether to rerun STRique/WarpSTR on all `~3971` reads with longer timeouts or create a matched smaller FAST5/BAM/f5index subset for faster reproducible benchmarking.

## 2026-05-06 Progress

- Resumed from this handoff file and checked current runtime state.
- No Docker containers or STR tool processes were running.
- Disk is now very tight: `/home/jkaranja/workdir` has about `16G` free.
- Repo working tree has prior uncommitted script patches: `ont-str-runner/scripts/make_warpstr_config.sh`, `ont-str-runner/scripts/run_deeprepeat.sh`, and `ont-str-runner/scripts/run_warpstr.sh`; `.venv/`, `SESSION_STATE.md`, and REL3 BED files are untracked.
- ND33392 DeepRepeat remains complete: `ont-str-runner/work/deeprepeat/ND33392/htt.log` contains the completed run, and `ND33392.fs.more` has `3756` rows.
- ND33392 WarpSTR remains partial: `ont-str-runner/work/warpstr/ND33392/HTT_CAG/overview.csv` has `3725` read rows but only early columns (`read_name,sample,run_id,reverse,sam_dist`); `predictions/alleles.csv` and `summaries/state_similarity.csv` are still missing.
- ND33392 STRique output is now much larger than the earlier checkpoint: `ont-str-runner/work/strique/ND33392.txt` has `3804` result rows plus header. Treat this as current output, but note it was not produced by a clean observed completion in this session.
- Regenerated `ont-str-runner/work/analysis/ground_truth_comparison.csv` with `python3 ont-str-runner/scripts/compare_ground_truth.py`.
- Current ND33392 comparison against expected `57/17`:
  - DeepRepeat GMM peaks: `18,58`, close to truth; allocation short peak `19` and long peak `55`.
  - STRique filtered peaks: short `18` (`+1` from truth) and long `59` (`+2` from truth), also close to truth.
  - WarpSTR has no allele peaks yet because final genotyping output is missing.
- Current recommendation: do not start another full WarpSTR rerun until disk pressure is addressed or a smaller matched ND33392 subset is created. The full WarpSTR config has `force_overwrite: True` and may redo expensive work.
- Suggested next step: either delete/archive safe large intermediates to recover disk, or create a matched downsampled ND33392 benchmark subset and run WarpSTR on that subset to get comparable allele calls quickly.
- Created matched small subset `ND33392_WARPSTR_SMALL` to avoid a risky full rerun under low disk:
  - Data folder: `ont-str-runner/data/ND33392_WARPSTR_SMALL/`.
  - Selected `240` existing FAST5 entries from `ND33392/htt.f5index` and created symlinks under `workspace/pass/0` instead of copying FAST5 data.
  - Wrote `read_ids.txt` and filtered/indexed BAM as `ND33392_WARPSTR_SMALL.bam` / `.bai`; BAM contains `243` alignments for selected read IDs.
  - Generated config: `ont-str-runner/configs/warpstr_ND33392_WARPSTR_SMALL.yaml`.
- Ran WarpSTR on `ND33392_WARPSTR_SMALL`; it completed in about `15` minutes.
- Small-subset WarpSTR outputs:
  - `ont-str-runner/work/warpstr/ND33392_WARPSTR_SMALL/HTT_CAG/overview.csv` has `212` result rows.
  - `ont-str-runner/work/warpstr/ND33392_WARPSTR_SMALL/HTT_CAG/predictions/alleles.csv` reports WarpSTR allele `52` with `201` reads and basecall allele `60` with `200` reads.
  - `ont-str-runner/work/warpstr/ND33392_WARPSTR_SMALL/HTT_CAG/summaries/state_similarity.csv` exists.
- Small-subset per-read distribution: WarpSTR median `52`, top counts `52:78`, `49:29`, `55:28`, `58:24`; `orig`/basecall median `55`, top counts `52:54`, `49:32`, `55:26`, `58:17`.
- Interpretation update: on a manageable ND33392 subset, WarpSTR detects the expanded HTT allele signal but undercalls the expected long allele (`52` vs truth `57`) and does not report the short allele. DeepRepeat and STRique full-sample outputs both remain closer to expected biallelic `57/17`.
- Disk after subset WarpSTR is about `15G` free on `/home/jkaranja/workdir`.
- Suggested next step: if full WarpSTR is still desired, free disk first and consider changing full-sample config/retry strategy so completed expensive steps are reused rather than overwritten. For paper/results, use `ND33392_WARPSTR_SMALL` only as a downsampled feasibility/comparison result, not as a full-sample replacement.

## 2026-05-07 Progress

- Continued from the ND33392 checkpoint without launching another full WarpSTR run because disk is still very tight: `/home/jkaranja/workdir` has about `15G` free.
- Patched `ont-str-runner/scripts/compare_ground_truth.py` so it can parse one-allele WarpSTR outputs where the missing second allele is recorded as `-`.
- Added `ND33392_WARPSTR_SMALL` to `ground_truth_comparison.csv` as an explicitly named downsampled row using ND33392 truth (`57/17`).
- Corrected the comparison script's WarpSTR/basecall delta logic: WarpSTR/basecall allele fields are already CAG repeat counts, so they should not be divided by 3.
- Regenerated `ont-str-runner/work/analysis/ground_truth_comparison.csv`.
- Current ND33392 comparison:
  - Full-sample DeepRepeat: GMM peaks `18,58`, close to expected `17,57`.
  - Full/available STRique output: filtered peaks `18` and `59`, close to expected `17,57`; still note the run was not observed completing cleanly in-session.
  - Downsampled WarpSTR row `ND33392_WARPSTR_SMALL`: WarpSTR peak `52` (`-5` from expected long allele), basecall peak `60` (`+3` from expected long allele), no short allele reported.
- Plain-English takeaway: for ND33392, DeepRepeat and STRique best match the known biallelic truth. The small WarpSTR subset detects the expanded allele but undercalls it and misses the short allele.
- Suggested next step: keep using `ND33392_WARPSTR_SMALL` only as a labeled downsampled feasibility result, or free disk before attempting a full WarpSTR completion/retry.
- Deleted the completed DeepRepeat model archive `/home/jkaranja/workdir/models/trainedmod_32_0.2.tar.gz` after confirming the extracted directory exists. Free disk increased from about `15G` to about `36G` on `/home/jkaranja/workdir`.
- User clarified the main thesis goal: create a novel algorithm better than existing alternatives, then compare it against WarpSTR, DeepRepeat, and STRique.
- Persisted the thesis specification and draft content in `docs/THESIS_SPEC_AND_DRAFT.md`.
- Persisted the proposed deep RNN algorithm plan in `docs/PROPOSED_RNN_ALGORITHM_PLAN.md`.
- The benchmark ACM-style manuscript already exists at `paper/htt_cag_multisample_acm_bcb.tex`; it contains the historical benchmark results the user pasted.
- Important note for future writing: the historical ACM benchmark text says WarpSTR/basecall peaks are converted by `bp/3`, but a later script correction treated current WarpSTR/basecall allele outputs as repeat counts already. Be explicit about which output format/interpretation is used before finalizing thesis metrics.
- Rechecked WarpSTR source inside Docker image `wkusmirek/warpstr:0.3.2`; the historical `bp/3` interpretation is correct for WarpSTR/basecall. WarpSTR `results`, `orig`, and `predictions/alleles.csv` values are sequence/base lengths, not CAG repeat counts. Convert them to CAG repeat counts by dividing by 3 and rounding. STRique and DeepRepeat parsed GMM/allocr values should not be divided by 3.
- Persisted a detailed plain-English reference explaining WarpSTR, STRique, DeepRepeat, units, failure modes, and the proposed RNN solution at `docs/ALGORITHM_EXPLANATION_FOR_REFERENCE.md`. This should be the first reference to open when the user needs to understand or explain the algorithms.
- Corrected `ont-str-runner/scripts/compare_ground_truth.py` back to the verified WarpSTR unit convention: WarpSTR/basecall allele fields are converted to CAG repeat counts by dividing by 3 and rounding.
- Regenerated `ont-str-runner/work/analysis/ground_truth_comparison.csv`. Under the verified unit convention, `ND33392_WARPSTR_SMALL` has WarpSTR/basecall repeat estimates `17/20`, so it should not be described as a reliable long-allele call. DeepRepeat and STRique remain the best-matching ND33392 results.
- Implemented the first algorithm-development milestone: `src/algorithm/evidence_table.py`.
- The evidence-table builder joins available per-read f5index, WarpSTR, STRique, DeepRepeat, truth-label, and REL3 alignment-context evidence without extracting raw signal yet.
- Ran `python3 src/algorithm/evidence_table.py`; it wrote `4265` rows to `ont-str-runner/work/analysis/evidence_table.tsv` for default samples `ND33392`, `ND33392_WARPSTR_SMALL`, and `REL3_WARPSTR_OK`.
- Ran `python3 -m py_compile src/algorithm/evidence_table.py ont-str-runner/scripts/compare_ground_truth.py`; compilation passed.
- Next concrete coding step: extend the algorithm pipeline from metadata to raw-signal windows, using `evidence_table.tsv` as the manifest. For each usable read, locate FAST5 signal, extract a locus-centered window, normalize it, and write compact arrays (`.npz` or HDF5) keyed by sample/read_id.

## 2026-05-11 Progress

- Continued the algorithm-development pipeline from the raw-signal extraction checkpoint.
- Confirmed system `python3` does not have `h5py`, but repo `.venv/bin/python` has `h5py 3.16.0` and `numpy 2.2.6`; use `.venv/bin/python` for FAST5 signal extraction.
- Added `src/algorithm/signal_windows.py`.
- The signal-window extractor reads `ont-str-runner/work/analysis/evidence_table.tsv`, opens FAST5 files via `h5py`, extracts raw-signal windows using `signal_window_start`/`signal_window_end` when available, adds configurable padding, normalizes each window with median/MAD, and writes fixed-width arrays plus an index TSV.
- Default output files:
  - `ont-str-runner/work/analysis/signal_windows.npz`
  - `ont-str-runner/work/analysis/signal_windows.index.tsv`
- Ran a 10-read test extraction for `ND33392_WARPSTR_SMALL`; output shape was `(10, 20000)` with valid masks and normalized signal values.
- Ran the default bounded extraction: `266` windows total, split as `212` for `ND33392_WARPSTR_SMALL` and `54` for `REL3_WARPSTR_OK`.
- Truncation summary with default `--max-signal-len 20000`: `0/212` truncated for `ND33392_WARPSTR_SMALL`, `13/54` truncated for `REL3_WARPSTR_OK`.
- Ran `.venv/bin/python -m py_compile src/algorithm/evidence_table.py src/algorithm/signal_windows.py ont-str-runner/scripts/compare_ground_truth.py`; compilation passed.
- Updated `src/algorithm/README.md` with the signal-window milestone command and outputs.
- Next concrete coding step: build a small training/evaluation dataset loader over `signal_windows.npz` and `signal_windows.index.tsv`, then implement a simple baseline model or non-neural repeat-count regressor before moving to the full RNN.
- User asked to install LazyVim before continuing algorithm work. LazyVim was installed under `~/.config/nvim`; Markdown rendering support was added via `MeanderingProgrammer/render-markdown.nvim` in `~/.config/nvim/lua/plugins/markdown.lua`. Neovim Markdown smoke test confirmed `filetype=markdown`, Markdown Tree-sitter parser availability, and `render-markdown.nvim` presence. Further LazyVim/Mason cleanup was stopped at the user's request because Markdown was working well enough.
- Returned to algorithm work and inspected the extracted signal-window labels. Current supervised signal-window set: `266` rows total; `212` labeled rows from `ND33392_WARPSTR_SMALL`; `54` unlabeled/unknown-truth rows from `REL3_WARPSTR_OK`. Labeled split is highly imbalanced: `201` short-like and `11` long-like.
- Added `src/algorithm/dataset.py`, which loads `ont-str-runner/work/analysis/signal_windows.npz` plus `signal_windows.index.tsv`, maps `short_like`/`long_like` rows to weak targets from sample truth, and computes compact signal-summary features.
- Added `src/algorithm/baseline.py`, a deterministic ridge-regression baseline using simple features: stored window length, mean, standard deviation, mean absolute signal, and signal quantiles. It uses inverse-label weighting by default because long-like reads are rare.
- Ran `.venv/bin/python src/algorithm/baseline.py`; outputs:
  - `ont-str-runner/work/analysis/baseline_predictions.tsv`
  - `ont-str-runner/work/analysis/baseline_summary.tsv`
- Balanced baseline result: `212` labeled rows, `170` train, `42` test, total test MAE `6.937`, short-like test MAE `6.645`, long-like test MAE `12.784`. Plain-English interpretation: this simple feature baseline still struggles, especially with the rare long allele, so it is a reasonable weak baseline for the RNN to beat.
- Ran `.venv/bin/python -m py_compile src/algorithm/dataset.py src/algorithm/baseline.py src/algorithm/evidence_table.py src/algorithm/signal_windows.py`; compilation passed.
- Updated `src/algorithm/README.md` with the baseline milestone command and caveat.
- Next concrete coding step: implement the first neural dataset/training loop over `signal_windows.npz`, likely a very small 1D CNN/BiGRU prototype with class-balanced or soft-label training, while keeping this ridge baseline as the sanity-check comparator.
- Continued from the neural training-loop checkpoint.
- Confirmed the repo venv has no PyTorch, TensorFlow, JAX, Keras, or scikit-learn, so avoided adding large dependencies and implemented a lightweight NumPy-only neural prototype.
- Added `src/algorithm/neural_baseline.py`, a one-hidden-layer MLP over downsampled raw-signal windows with inverse-label weighting, Adam optimization, and an internal validation split for early model selection.
- Ran `.venv/bin/python src/algorithm/neural_baseline.py`; outputs:
  - `ont-str-runner/work/analysis/neural_baseline_predictions.tsv`
  - `ont-str-runner/work/analysis/neural_baseline_summary.tsv`
- Neural baseline result: `266` total rows, `212` labeled rows, `170` train rows, `42` test rows, best epoch `58`, validation MAE `5.507`, total test MAE `5.746`.
- Comparison to previous ridge baseline: total test MAE improved slightly (`5.746` vs `6.937`), but rare long-like reads are still poorly modeled (`long_like` test MAE `32.418`; `short_like` test MAE `4.413`).
- Ran `.venv/bin/python -m py_compile src/algorithm/dataset.py src/algorithm/baseline.py src/algorithm/neural_baseline.py src/algorithm/evidence_table.py src/algorithm/signal_windows.py`; compilation passed.
- Updated `src/algorithm/README.md` with the neural baseline milestone command and caveat.
- Next concrete coding step: improve the neural model/data rather than over-interpreting this prototype. Priority options are: add more labeled long-allele windows, augment/rebalance long-like reads, or replace coarse downsampling with a small sequence model/convolutional boundary detector that preserves local repeat-boundary structure.

## Working Rule

For future multi-step plans, update this file after every major completed step or blocker so a later OpenCode session can resume without reconstructing context.

## 2026-05-14 Truth Benchmark Plan Recovery

- User clarified a missing plan that was not fully reflected in this session state: REL3 was archived so the project can focus on objective-truth fibroblast samples and compare the new RNN algorithm against DeepRepeat, STRique, and WarpSTR.
- Truth source: `https://pmc.ncbi.nlm.nih.gov/articles/instance/5363210/bin/mmc1.pdf`.
- Main truth-labeled HTT CAG samples to use for objective benchmarking: `GM04723 72/17`, `ND30015 41/20`, `ND30016 41/21`, `ND30047 41/18`, `ND30422 40/18`, `ND30626 41/21`, `ND31551 39/18`, `ND33392 57/17`, and `ND33947 40/18`.
- Truth-labeled samples mentioned in the PDF but not currently in the SRA URL list: `GM04767 47/18` and `ND31038 44/19`.
- Additional SRA archives to download as unlabeled/comparison data unless truth is supplied: `ND29970`, `ND40534`, and `NA12878`.
- Download manifest: `ont-str-runner/work/truth_benchmark_20260514/objective_truth_samples.tsv`.
- Download helper: `ont-str-runner/scripts/download_truth_samples.sh` uses `wget -c` and `gzip -t` for resumable verified downloads.
- Current archive check before resuming downloads: `ND33392` archive exists at `ont-str-runner/data/ND33392/ND33392.tar.gz.1`; `GM04723` archive exists but is much smaller than expected and should be treated as partial until `gzip -t` passes; the other listed archives were missing.
- Current disk check before resuming downloads: `/home/jkaranja/workdir` has about `459G` free.
- Working rule update from user: include every multi-step plan discussed in `SESSION_STATE.md` (or a clearly referenced project state file) before moving on, so future sessions do not lose context.

## 2026-08-13 REL3 Expanded Validation

- Recovered the project after a server reboot by mounting the existing 1 TB
  ext4 volume `/dev/vdb` at `/home/jkaranja/workdir`. The volume had about
  `351G` free after mounting.
- Confirmed the scored nine-sample checkpoint remains unchanged: current LOSO
  MLP allele MAE is `0.556`, versus WarpSTR `0.722` and STRique `1.667`.
- Added `src/algorithm/alignment_signal_bounds.py`. It independently maps HTT
  reference coordinates through BAM CIGAR operations and native FAST5
  event/move tables to raw-signal coordinates.
- Added focused unit tests in `src/algorithm/test_alignment_signal_bounds.py`
  and `src/algorithm/test_call_alleles.py`; five tests pass.
- Current REL3 source coverage: 172 matched FAST5/BAM reads, 93 independently
  derived full-flank signal windows, and 33 MAPQ-60 windows.
- Boundary validation on 38 reads shared with WarpSTR has median absolute raw
  coordinate differences of `28.5`, `19.5`, `24.0`, and `12.0` samples for
  window start, repeat start, repeat end, and window end.
- Added `src/algorithm/combine_signal_archives.py` and generated:
  - `ont-str-runner/work/analysis/signal_windows_rel3_expanded.npz`
  - `ont-str-runner/work/analysis/signal_windows_truth_plus_rel3_expanded.npz`
  - matching `.index.tsv` files
- Updated `call_alleles.py` so unlabeled external samples use MAPQ >=20 when
  MAPQ is available. Closely spaced external clusters now produce an unresolved
  consensus instead of two misleading calibrated alleles.
- Current quality-aware REL3 result: unresolved `17/17`, raw prediction median
  `18.812`, 33/93 reads used, confidence `low` because coverage is small, two
  alleles are unresolved, and 60 low-MAPQ reads were filtered.
- All-read sensitivity result: `38/15` on 93 reads. Low-MAPQ extreme
  predictions drive the apparent high cluster, so this is retained only as a
  failure-mode analysis in `algorithm_truth_plus_rel3_expanded_all_reads_*`.
- Independent sequence evidence in the 33 MAPQ-60 reads: median 14 total CAG
  triplets (range 10-18) and median longest uninterrupted CAG run 11 (range
  4-18). This does not support the historical low-confidence `54/18` call.
- REL3 remains unlabeled, so no REL3 MAE is claimed. The next target is more
  independent high-quality REL3 coverage and per-read boundary/sequence quality
  features before final RNN evidence.

## 2026-08-14 Novelty Audit and Weak-Supervision RNN

- Audited current raw-signal tandem-repeat methods. NanoSatellite already uses
  raw-squiggle DTW; STRique uses raw-signal boundary alignment plus an HMM;
  DeepRepeat uses a deep CNN over signal-derived images and evaluated the same
  11 HTT cell lines; WarpSTR uses a raw-signal finite-state/DTW-like model plus
  sample-level GMM calling. A generic “deep RNN for raw nanopore STR counting”
  is therefore not a defensible novelty claim.
- Narrowed the research contribution to the complete combination of unordered
  sample-level diploid supervision, latent per-read assignment, sequence-aware
  raw-signal residual learning, heteroscedastic uncertainty, abstention, and
  nested sample-disjoint evaluation. Details and literature links are in
  `docs/PROPOSED_RNN_ALGORITHM_PLAN.md`.
- Added `src/algorithm/weak_supervised_rnn.py`. It never consults `group_label`
  or per-read `target` during optimization. It uses one sample for outer test,
  a distinct sample for validation/uncertainty scaling, and the rest for train.
- Added a train-only monotonic duration calibration. Two duration centres are
  found without read labels for every training sample and paired in sorted
  order with the unordered genotype. A Conv-BiGRU/LSTM learns only the residual
  count and log variance.
- Added constrained generalized-EM assignment, component-balanced loss,
  beta-NLL weighting, auxiliary Huber mean loss, and a duration ordering prior.
- Added `src/algorithm/uncertainty_alleles.py`, a heteroscedastic one-versus-two
  Gaussian caller with BIC, separation, support gates, and explicit abstention.
  Output now calls this `mixture_confidence`; it measures within-sample
  separation only and must not be interpreted as calibrated genotype accuracy.
- Added `src/algorithm/run_weak_supervised_loso.py`. It performs nested LOSO,
  reports resolved coverage separately from conditional resolved-call MAE, and
  also reports all-fold candidate-mode MAE as a non-clinical diagnostic.
- Added `test_uncertainty_alleles.py` and `test_weak_supervised_rnn.py`. Together
  with existing focused algorithm tests, 15 tests pass. Checks include allele
  order invariance, no dependence on per-read group labels, sample split
  disjointness, duration-prior train-only isolation, uncertainty calibration,
  and abstention behavior.
- Nested-LOSO smoke mechanics passed for three folds at 32 reads/sample and one
  epoch. All three folds abstained, as expected for an undertrained smoke run;
  outputs are under
  `ont-str-runner/work/analysis/weak_supervised_rnn_loso_smoke/`.
- Completed the fixed nine-fold nested LOSO development screen at 64 reads per
  sample and 20 epochs per fold. Output is under
  `ont-str-runner/work/analysis/weak_supervised_rnn_loso_dev/`.
- Aggregate result: 0/9 folds resolved (coverage 0.000) at the safe 0.20 minor-
  component threshold; all-fold candidate-mode MAE was 14.784. Candidate MAE
  is diagnostic only. This architecture fails the development gate, so a full
  30,356-read run is not justified until the boundary/model design changes.
- Bounded 64-read/sample development experiments exposed two failures. Soft
  assignment collapsed to the genotype midpoint. Hard assignment separated
  alleles but compressed expanded counts toward ~40. Adding the train-only
  duration prior improved the already-exposed ND33392 forced call from 42/21 to
  62/24 (truth 57/17; MAE 6.0), but that apparent call relied on only 7/64 reads.
  Raising caller minor support from 0.10 to the safer 0.20 correctly abstains.
- A duration-only nine-fold LOSO diagnostic produced allele MAE 3.597. This is
  much worse than the frozen engineered MLP LOSO MAE 0.556 and is an ablation,
  not a replacement caller.
- The weak RNN has not beaten the MLP and should not be presented as a positive
  benchmark result. ND33392 has influenced design choices and is no longer an
  untouched confirmation sample. Stop fold-specific tuning and judge future
  changes using aggregate nested LOSO.
- Important independence limitation: the nine-sample raw windows still use
  WarpSTR-derived boundaries. The next research gate is a complete capped LOSO
  screen, followed by replacing those windows with the independent BAM/native-
  FAST5 boundary mapper and adding a learned boundary/alignment component.

## 2026-08-14 Independent Truth Boundaries and Repeat-Duration Gate

- Generalized `src/algorithm/alignment_signal_bounds.py` from the REL3 probe to
  arbitrary truth samples. The output now includes sample truth, blank
  `group_label`, an explicit `bam_cigar_native_fast5_events` source, alignment
  diagnostics, raw-per-base consistency features, and independent boundary QC.
- Corrected two Albacore compatibility details. The older truth FAST5 files
  have an inferred event-to-FASTQ k-mer offset of 4 rather than REL3's 5, and
  their event `start` values are already integer raw-sample positions rather
  than seconds. Tests cover both variants.
- Added `src/algorithm/build_independent_truth_manifest.py`. It reads only the
  primary labelled entries in `configs/truth_samples.tsv` and independently
  maps a deterministic maximum of 128 successful MAPQ >=20 reads per sample.
- Bounded manifest output:
  `ont-str-runner/work/analysis/independent_truth_signal_bounds_dev.tsv` and
  `_summary.tsv`. It contains exactly 1,152 rows (128 for each of nine samples),
  all MAPQ 60, with zero FAST5 failures and no nonblank per-read group labels.
- Independent boundary QC retained 1,135/1,152 reads and rejected 17 (1.5%).
  Per-sample pass counts are GM04723 123, ND30015 128, ND30016 126, ND30047
  127, ND30422 126, ND30626 126, ND31551 127, ND33392 125, and ND33947 127.
- WarpSTR is used only for retrospective coordinate comparison, never as a
  boundary input. Median absolute independent-versus-WarpSTR deltas are roughly
  36.5-41 raw samples at full-window start, 19-25 at repeat start, 12-22 at
  repeat end, and 5-12 at full-window end. The largest disagreements are
  enriched for multiple full-flank alignments and are independently QC-flagged.
- Extended `src/algorithm/signal_windows.py` with `--boundary-kind repeat` and
  `--require-boundary-qc`. Created two bounded independent archives:
  `signal_windows_independent_qc_dev.*` for full flank windows and
  `signal_repeat_windows_independent_qc_dev.*` for the exact mapped repeat plus
  250 raw-sample padding. The repeat archive has 1,135 windows and no
  truncation.
- Physics ablations under strict LOSO: full-flank duration MAE 4.776; exact
  mapped repeat-duration MAE 1.638; flank-rate-normalized duration MAE 1.689;
  mapped query-span MAE 2.912. Raw repeat duration is the best independent
  physics feature. Existing tail correction worsened it to 1.705.
- Added `src/algorithm/evaluate_repeat_duration_loso.py` and its tests to freeze
  the 1.638 result reproducibly. Every fold finds robust unlabeled duration
  centres, fits its affine count calibration on the other eight samples only,
  and ignores `group_label` and all tool-derived per-read counts. Outputs are in
  `ont-str-runner/work/analysis/repeat_duration_independent_loso_dev/`.
- The weak RNN still failed on independent full-flank windows: 1/9 folds
  resolved, candidate MAE 10.951, conditional resolved MAE 6.5.
- Repeat-focused windows improved the uncorrected RNN run to 6/9 resolved, but
  inspection showed validation likelihood improving while validation genotype
  MAE worsened. This made the original epoch selection scientifically
  misaligned.
- Updated `weak_supervised_rnn.py` so epoch 0 (the duration prior) is eligible
  and validation defaults to robust genotype allele MAE rather than likelihood.
  The corrected nested run is in
  `weak_supervised_rnn_repeat_valselect_loso_dev/`: seven folds selected epoch
  0, only ND33392 and ND33947 selected trained epochs, 5/9 folds resolved,
  candidate MAE 5.775, and conditional resolved MAE 4.400.
- Interpretation: the independent boundary pipeline succeeds, and exact repeat
  duration is a useful physical baseline, but the current Conv-BiRNN residual
  is harmful. Freeze both results; do not run a larger neural job or tune outer
  folds. The next model must beat epoch 0 on validation genotype MAE and should
  test explicit periodicity/boundary or monotonic-alignment structure before a
  full independent archive is justified.
- Focused algorithm suite now contains 27 passing tests, including boundary
  variants/QC, no group-label dependence, train-only duration calibration,
  validation selection, uncertainty behavior, and LOSO holdout isolation.
- Added `src/algorithm/evaluate_repeat_periodicity_loso.py`. It slices only the
  independently mapped repeat, estimates a local autocorrelation period near
  the flank-implied CAG dwell, and compares raw duration with span/period.
- The fixed autocorrelation-normalized feature has exploratory LOSO MAE 1.414
  versus duration 1.638. This feature and its parameters were developed after
  inspecting the same nine samples, so 1.414 is not an unbiased benchmark.
- A nested selector chooses raw duration versus autocorrelation using inner
  training folds only. It selected autocorrelation in 8/9 folds but produced
  aggregate outer MAE 1.725; the single duration selection was GM04723 and its
  long-allele undercall dominated the difference. The apparent fixed-feature
  gain therefore requires external confirmation, not more tuning on these nine.
- Median selected autocorrelation period is 35 raw samples and median peak
  strength is 0.113. Treat this as a candidate local-period feature, not yet as
  definitive biological CAG periodicity.
- Direct NCBI SRA E-utility searches returned zero records for `GM04767` and
  `ND31038`, the two additional truth genotypes mentioned in the source PDF.
  The current public accession series contains the existing nine labelled and
  three unlabeled samples, so external confirmation cannot simply reuse a
  missing public run. Do not assign surrogate truth to unlabeled samples.
- Added two periodicity tests; the focused algorithm suite now has 29 passing
  tests.

## 2026-08-14 External confirmation acquisition

- External confirmation is now the active gate; do not tune the nine-sample
  development result further before evaluating new labelled samples.
- Primary study: Stevanovski et al. 2022, SRA `SRP349335` / BioProject
  `PRJNA786382`, targeted ONT R9.4.1 ReadUntil/ReadFish sequencing.
- NCBI full SRA XML authoritatively resolves the anonymized aliases:
  - NA13509 `15/70`: preferred alias `GBXM106320`, FASTQ `SRR17138617`,
    FAST5 `SRR17138604`, SLOW5 `SRR17859097`; reserve replicate
    `MBXM118340` (`SRR17138629`, `SRR17138587`, `SRR17859099`).
  - NA13512 `16/44`: alias `GBXM077293`, FASTQ `SRR17138584`, FAST5
    `SRR17138601`, SLOW5 `SRR17859077`.
- Frozen manifest:
  `ont-str-runner/configs/external_confirmation_samples.tsv`.
- Raw archives are 103--293 GB and must not be downloaded indiscriminately.
  Added `src/algorithm/http_tar_members.py`, which indexes uncompressed remote
  tar headers using HTTP Range requests and refuses servers that ignore Range.
- SLOW5 tar indexes show exactly nine members per preferred sample: pass FASTQ,
  fail FASTQ, and one monolithic BLOW5 plus directories. There is no deposited
  BLOW5 index, so the useful selective path is FASTQ alignment plus FAST5 batch
  retrieval.
- FAST5 tar indexing found 753 multi-FAST5 files for GBXM106320. Each contains
  about 4,000 raw reads. Batch suffixes are chronological: `_0` covers the
  beginning of the run and `_752` the end. FASTQ comments include acquisition
  timestamps, allowing direct retrieval of a small candidate set.
- Deposited FAST5 is raw-only (root read groups contain Raw/channel/tracking
  metadata and no Analyses group). A disposable Guppy probe confirmed that the
  available Guppy build is GPU-only, and current Dorado no longer supports
  R9.4.1. The selected CPU path therefore uses the published FASTQ sequence
  with f5c event alignment rather than introducing a new basecaller.
- Reproducible FASTQ-streaming/alignment driver:
  `ont-str-runner/scripts/prepare_external_confirmation.sh`. It preserves
  FASTQ comments with minimap2 `-y`, writes a chr4 BAM, an HTT BAM, and HTT
  read metadata without storing the run-wide FASTQ.
- `src/algorithm/remote_fast5_lookup.py` is a guarded HDF5-over-Range fallback.
  It is correct but scattered HDF5 metadata requests are slower than using the
  discovered chronological batch invariant.
- Installed the official f5c 1.6 CPU binary under
  `/home/jkaranja/workdir/tools/f5c-v1.6/` and the official VBZ HDF5 plugin
  under `/home/jkaranja/workdir/tools/vbz-1.0.1/`. Added
  `ont-str-runner/scripts/run_external_f5c_eventalign.sh` and
  `src/algorithm/f5c_signal_bounds.py`. The workflow indexes the target-only
  multi-FAST5, emits f5c raw indices for HTT-aligned reference positions, and
  derives truth-free left/repeat/right signal spans with consistency QC.
- `src/algorithm/signal_windows.py` now reads both legacy single-FAST5 layout
  and modern multi-FAST5 root groups, so the selected raw groups can feed the
  unchanged repeat-window feature extraction path. Commands that read or copy
  deposited FAST5 signal must expose the installed VBZ directory through
  `HDF5_PLUGIN_PATH`.
- Optimized `src/algorithm/external_fast5_batches.py` so its full-run header
  census uses sorted target thresholds rather than comparing every header to
  every target read. Rank calculation is now `O(run_reads * log HTT_reads)`
  instead of `O(run_reads * HTT_reads)` while retaining deterministic
  timestamp/read-ID ordering.
- External evaluation remains frozen: train calibration on all nine
  development samples, predict NA13509/NA13512 before reading their truth in
  the evaluator, and report per-sample plus pooled allele MAE. Do not select
  duration versus ACF using external truth.
- Completed the NA13509 / GBXM106320 acquisition path. The pass stream aligned
  2.77 million reads; 31 overlapped the broad HTT region and 5 unique MAPQ >=20
  reads spanned both frozen 112-bp flanks. All five exact UUIDs were recovered
  from five central plus adjacent chronological FAST5 batches, then copied to
  a target-only multi-FAST5 with its required root attributes preserved.
- This minimap2 build did not emit the original FASTQ comment into BAM despite
  `-y`. `external_fast5_batches.py` now recovers target timestamps by exact
  UUID from the complete compressed pass/fail header census and computes ranks
  in a second local scan. The five target timestamps mapped to five distinct
  central batches; four UUIDs were central and the fifth was in an immediately
  adjacent batch.
- f5c 1.6 indexed 5/5 selected NA13509 reads and event-aligned all five with
  zero f5c QC/calibration/alignment failures. Corrected external boundary QC to
  divide raw repeat duration by each read's CIGAR-derived query repeat span,
  matching the development mapper. Using the 58-bp reference span had
  incorrectly rejected expanded insertions. After this pre-prediction physics
  correction, all 5/5 boundary rows pass QC.
- NA13509 truth-free repeat archive:
  `external_confirmation/GBXM106320/GBXM106320.repeat_windows.{npz,index.tsv}`.
  It contains five rows, no genotype fields, no truncation, and raw repeat
  spans of 397, 467, 573, 2,076, and 2,362 samples. Do not score or tune this
  sample separately; combine it with NA13512 and write both sealed predictions
  before the score subcommand opens the truth manifest.
- Completed NA13512 / GBXM077293. The pass stream processed 9.92 million reads
  from the fixed 27.49-GB member. Thirteen unique MAPQ >=20 reads spanned both
  112-bp flanks; all 13 exact UUIDs were recovered from central plus radius-1
  FAST5 batches. f5c indexed/calibrated/event-aligned all 13 without internal
  failures. Independent boundary QC retained 12/13 and rejected one
  repeat-versus-flank rate inconsistency.
- Combined truth-free external archive:
  `ont-str-runner/work/analysis/external_confirmation/external.repeat_windows.*`.
  It has 17 rows (NA13509 5, NA13512 12), zero nonblank genotype fields, and
  zero truncated windows. Prediction code, development inputs, and external
  inputs were hashed in `frozen_prediction_inputs.sha256` before prediction.
- Sealed predictions were written and hashed before the score command opened
  the truth manifest. Duration predicted NA13509 11.909/71.449 and NA13512
  12.317/39.810. Fixed ACF predicted NA13509 12.435/61.533 and NA13512
  16.128/44.414. Sealed prediction SHA-256 starts `344f2c036706fbfc`.
- External allele MAE by sample: duration 2.270 (NA13509) and 3.936 (NA13512);
  fixed ACF 5.516 (NA13509) and 0.271 (NA13512). Pooled two-sample MAE is
  3.103 for duration and 2.894 for fixed ACF, a small 0.210 ACF advantage.
  The sample-level direction reverses, so this is weak heterogeneous support
  for ACF, not a decisive generalization win. Freeze these samples now; do not
  tune feature parameters or choose a feature using their revealed truth.
- Focused algorithm suite reached 50 passing tests before external scoring.
  Re-run it after documentation-only changes and preserve the hashed external
  artifacts under `external_confirmation/`.

## 2026-08-20 Independent MASTR-seq HTT confirmation

- Identified a four-sample HTT cohort in MASTR-seq (`SRP504233`,
  `PRJNA1105011`) and raw Zenodo record `17618429` / `FAW16852.pod5`.
- Final sequence-audited sample mapping: MASTR_P/SRR35299134/barcode10,
  MASTR_N/SRR35299133/barcode09, MASTR_E1/SRR35299132/barcode11, and
  MASTR_E2/SRR35299131/barcode12. The initial paper-level barcode09/barcode10
  assignment was reversed; this was detected and corrected by aligning raw
  FAST calls back to the complete public ENA sample archives before SUP
  basecalling or truth access.
- Isolated genotype truth in `mastr_confirmation_truth.tsv`: uninterrupted CAG
  `20/22`, `20/22`, `22/56`, and `22/72`. Do not use the paper's observed
  nanopore distributions for tuning.
- Downloaded and MD5-verified all four ENA FASTQs and the 3,195,792,800-byte
  POD5 (`83407793c4217d6aa65eec0c23b33f30`). Public FASTQ alignment yielded
  128 deterministically capped full-flank reads per sample, but ENA and SRA
  both replace raw UUIDs with archive-local ordinal names. None of those 512
  names join to POD5; they remain a coverage/provenance audit only.
- Installed Dorado `0.7.3+6e6c45c` from the official bundle (bundle SHA-256
  `fae832f639aba397399ea36520fb207dd6c2b4c27204586332a99f9fc6114c4f`) and
  read-only `pod5==0.3.44` in the project venv.
- Definitive POD5 `run_info` reports 4,000 Hz, `FLO-MIN106`, `sqk-lsk109`, and
  acquisition ID `ad967a82ca8a05f4dce1a2ce59d3e13ae6357820`. This invalidated the
  initial R10/v5 assumption before any predictions. Treat the cohort as an
  independent targeted-library R9.4.1 gate, not cross-chemistry.
- Frozen compatible models: `dna_r9.4.1_e8_fast@v3.4` for whole-run barcode
  and locus UUID selection only; `dna_r9.4.1_e8_sup@v3.6` for final move-table
  boundaries and signal features.
- Added `select_barcoded_htt_reads.py`, `dorado_move_signal_bounds.py`,
  `extract_pod5_signal_windows.py`, `evaluate_mastr_confirmation.py`, their
  tests, and acquisition/selection/prediction/scoring scripts. The remote
  suite reached 66 tests after these additions (64 before the barcode tests,
  then 2 focused barcode tests); rerun full discovery after final changes.
- Frozen gate: all four samples, >=6 QC windows each, pooled fixed-ACF allele
  MAE <=3, and expanded long-allele absolute error <=5 for both expansion
  samples. Duration is diagnostic-only and cannot affect pass/fail.
- The whole-run CPU screen was projected to take about 90 minutes. Before
  final UUID selection or prediction, it was replaced with a deterministic
  SHA-256-ranked screen of 15,000/91,869 raw UUIDs using seed
  `mastr-raw-screen-v1`. Two parallel runtime shards exceeded the 49-GiB host
  memory limit, so the unchanged UUID set is being processed serially in one
  Dorado process. This cap used only truth-free barcode/locus hit rate and does
  not change the >=6/sample gate.
- The bounded FAST pass selected 146 full-flank raw UUIDs: MASTR_P 27,
  MASTR_N 20, MASTR_E1 46, and MASTR_E2 53. The archive-identity audit used
  base-level minimap2 PAF (`-c`) and passed with concordance 23/23, 19/19,
  40/41, and 49/49 respectively. Mapping-only PAF columns had initially been
  misread as exact identity; enabling base-level alignment corrected the
  implementation without changing the frozen 85% identity or 90% concordance
  thresholds.
- R9 SUP produced boundaries for all 146 selected reads; 145 passed boundary
  QC (P 27, N 20, E1 46, E2 52), with zero missing POD5 reads, zero truncated
  windows, and no genotype values in the prediction index. Sealed prediction
  SHA-256 is
  `31aaa07a1d6ada76e949e84ada832f73afef165e630d943d06a1c5407b9b4ba9`.
- The isolated scorer opened truth only after the prediction hash verified.
  Primary fixed-ACF predictions were P `12.517/22.410`, N `13.915/20.442`,
  E1 `21.396/55.363`, and E2 `19.071/77.781`. Per-sample allele MAE was
  `3.947`, `3.822`, `0.621`, and `4.355`; pooled MAE was `3.186`.
  The E2 long-allele error was `5.781`. The frozen gate therefore failed both
  primary conditions (pooled MAE <=3 and maximum expanded-long error <=5).
  Duration was diagnostic-only with pooled MAE `4.622`.
- This is a valid confirmatory negative result. ACF transferred better than
  duration but did not meet the predeclared accuracy gate. Freeze the four
  samples now; do not tune ACF, calibration, boundary QC, or thresholds on
  their revealed truth.


## 2026-10-13 Stabilization, supervisor comparisons, and Axis-1 plan

- Recovered full project context by SSH to `target`; confirmed 68 algorithm unit
  tests pass under `.venv/bin/python -m unittest discover -s src/algorithm`.
- STABILIZATION: the entire `src/algorithm/` pipeline, its tests, the research
  docs, the external/MASTR confirmation scripts+configs, and this file were all
  previously UNTRACKED in git (only the paper + runner shell were committed).
  Committed everything; gitignored the 7.1 GB `tools/` toolchains and stray
  `*.fastq`. Reviewed and kept the in-flight fixes (python->python3 and
  rg->bash-regex runner patches; strict `compare_ground_truth.py` rewrite that
  adds a failure table and benchmark report; paper text matching the final
  9-sample benchmark).
- Reproducibility audit (all headline numbers re-derived from code/stored
  outputs): benchmark WarpSTR 0.556/0.889, STRique 1.889/1.444, DeepRepeat 4/9
  missed-short, 0 failures; independent duration LOSO 1.638; periodicity
  1.414/1.725; weak RNN 5/9 resolved, candidate 5.775, resolved 4.400; Coriell
  3.103/2.894; MASTR 3.186/5.781/4.622. All reproduce; no contradictions across
  paper/SESSION_STATE/docs. CONFIRMED with hard provenance that the 0.556 MLP
  draws its windows from the WarpSTR-boundary archive, so it is NOT an
  independent win; the defensible headline is the independent duration 1.638.
- Wrote `docs/DEFENSE_PREP.md` (panel rehearsal: honest summary, results table
  with status column, claim/non-claim boundary, four likely panel attacks,
  limitations, reproducibility story, mock defense over the 10 reviewer
  questions). Updated it with the 2026-10-13 figures.
- SUPERVISOR-REQUESTED COMPARISONS (committed): `src/algorithm/make_comparison_figures.py`
  generates `paper/figures/panel_a_error_vs_length.png` (allele error vs repeat
  length) and `paper/figures/panel_d_single_read_distribution.png`
  (density-normalised per-read distributions; proposed caller DOES separate the
  two alleles per read, addressing the ND33392 bimodality note, but with a
  noisier long-allele mode). `paper/figures/runtime_memory_comparison.md`:
  proposed caller measured at 2.05 s / 222 MB for full 9-fold LOSO vs
  minutes-hours and GB-scale for the signal tools. Panel-A mean abs allele
  error: WarpSTR 0.722, DeepRepeat 1.556, Proposed 1.638, STRique 1.667.
- GitHub: added SSH deploy key on the VM (`~/.ssh/ont_str_deploy`, repo
  `core.sshCommand`), switched origin to SSH, pushed `main` (was benchmark-stage
  only). The supervisor can now see the full algorithm + figures at
  github.com/MingiJ/ont-str-analysis.
- Drafted the supervisor email (reports the novel algorithm + the requested
  comparisons; asks (1) to claim his offered extra datasets now that the
  algorithm exists, and (2) whether a rigorous non-WarpSTR-beating contribution
  is acceptable). Ready to send; attach the two PNGs.
- AGREED NEXT DIRECTION (Axis 1): a length-dependent "ruler". Diagnostic on
  `repeat_duration_independent_loso_dev/folds.tsv` + the repeat-window index
  showed samples-per-CAG varies ~29-38 and is systematically LOWER for the long
  allele in 8/9 samples, so a single affine duration->count calibration
  mis-extrapolates to the expansions (GM04723 72 undercalled to ~64; ND33392 57
  overcalled to ~61). The duration-baseline error concentrates on the expanded
  alleles (Panel A). Plan: model samples-per-CAG as a function of allele length
  / per-read speed, measured against the frozen 1.638 gate under identical
  nested LOSO, carrying the uncertainty/abstention layer. Uncertainty/abstention
  is a reporting feature, not an accuracy win (within-sample separation does not
  track error: GM04723 has the highest cluster separation AND the worst error).
  Keep leakage discipline (no WarpSTR boundaries, no tuning on held-out truth).
- Jeff is upskilling (genetics + nanopore physics + ML evaluation) and wants to
  steer/judge outputs. Covered: diploid/dominant genetics, why long+short,
  nanopore k-mer signal, repeat DURATION as the core feature, boundary
  sensitivity (200 samples ~= 6 CAG), alignment vs move-table coordinate chain,
  train/val/test, read-split leakage vs LOSO, data leakage, negative results.
  Remaining: finish practising the 10-question review checklist on live results.
