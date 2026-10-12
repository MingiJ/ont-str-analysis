# Runtime and memory comparison (supplementary)

Hardware: project VM (CPU-only for the proposed caller). Proposed caller figures
are **measured** with `/usr/bin/time -v`; the three existing tools are
**indicative** from their prior runs on this project (a controlled same-hardware
benchmark over identical read sets is the remaining supplementary step).

| Tool | Stage timed | Wall time | Peak RAM | Notes |
|---|---|---|---|---|
| **Proposed (independent duration)** | full 9-fold LOSO calling | **2.05 s** (measured) | **222 MB** (measured) | CPU-only, NumPy; no basecaller, no GPU |
| WarpSTR | raw-signal DTW + Guppy annotation | minutes–hours / sample (indicative) | GB-scale | Docker image `wkusmirek/warpstr`; needs Guppy; ~8 min for 54 reads, ~15 min for 240 reads in prior runs, so thousands of reads is hours |
| STRique | raw-signal HMM | tens of minutes–hours / sample (indicative) | GB-scale | Docker; did not finish a full ND33392 sample within a 30-min window in prior runs |
| DeepRepeat | signal-to-image CNN | minutes / sample (indicative) | GB-scale | Requires loading the 32 GB trained model directory |

**Takeaway:** the proposed caller is orders of magnitude lighter in both time and
memory because it operates on a per-read repeat-duration feature rather than a
full raw-signal DTW/HMM search or an image CNN. A controlled, identical-read-set
runtime/RAM benchmark of the three existing tools is listed as supplementary work.
EOF
echo "runtime table written"; ssh target 'cd ~/workdir/ont-str-analysis && ls -la paper/figures/'