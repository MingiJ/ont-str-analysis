# Algorithm development

This folder will hold the new STR counting algorithm implementation.

Recommended structure:
```
src/algorithm/
  data_io.py        # FAST5/BAM helpers
  signal.py         # signal preprocessing + event segmentation
  model.py          # core model / alignment / inference
  postprocess.py    # peak calling / confidence scoring
  eval.py           # evaluation hooks
```

Design goals (from paper):
- repeat-boundary detection improvements
- per-read confidence with uncertainty-aware clustering
- robustness to strand / mapping offsets

Start here:
- define inputs/outputs for per-read counting
- implement a minimal pipeline that reads one FAST5 + BAM alignment and returns repeat count + confidence
