#!/usr/bin/env python3
"""Generate supervisor-requested comparison figures and tables.

Reproduces, for the proposed independent-duration caller vs WarpSTR, STRique and
DeepRepeat on the nine labelled HTT CAG samples:

  * Panel A  - allele error vs true repeat length (DeepRepeat Fig. 4A style)
  * Panel D  - per-read single-read estimate distributions (DeepRepeat Fig. 4D style)
  * a per-sample comparison table backing Panel A

Units policy (matches the benchmark report):
  * WarpSTR 'results' field is sequence length in bp -> CAG = round(bp / 3)
  * STRique 'count' is already a CAG repeat count
  * DeepRepeat has no clean per-read count; only allele peaks are used (Panel A)
  * Proposed caller: per-read repeat duration (raw samples) calibrated to CAG with
    the held-out sample's leave-one-sample-out affine fit (no leakage).
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "ont-str-runner" / "work" / "analysis"
WARPSTR = ROOT / "ont-str-runner" / "work" / "warpstr"
STRIQUE = ROOT / "ont-str-runner" / "work" / "strique"
FOLDS = ANALYSIS / "repeat_duration_independent_loso_dev" / "folds.tsv"
INDEX = ANALYSIS / "signal_repeat_windows_independent_qc_dev.index.tsv"
GT = ANALYSIS / "ground_truth_comparison.csv"
OUT_FIG = ROOT / "paper" / "figures"
OUT_FIG.mkdir(parents=True, exist_ok=True)

SAMPLES = ["GM04723", "ND30015", "ND30016", "ND30047",
           "ND30422", "ND30626", "ND31551", "ND33392", "ND33947"]

COLORS = {
    "Proposed": "#1b9e77",
    "WarpSTR": "#7570b3",
    "STRique": "#d95f02",
    "DeepRepeat": "#e7298a",
}


def _num(x):
    try:
        if x in (None, "", "-"):
            return np.nan
        return float(x)
    except (TypeError, ValueError):
        return np.nan


# ---------------------------------------------------------------- load tables
gt = pd.read_csv(GT)
folds = pd.read_csv(FOLDS, sep="\t").set_index("holdout_sample")

# per-sample calibration for the proposed caller (held-out fit)
calib = {s: (folds.loc[s, "calibration_intercept"], folds.loc[s, "calibration_slope"])
         for s in SAMPLES}


# ---------------------------------------------------------------- Panel A data
rows = []
for _, r in gt.iterrows():
    s = r["sample"]
    if s not in SAMPLES:
        continue
    tl, ts = _num(r["truth_long"]), _num(r["truth_short"])
    preds = {
        "WarpSTR": (_num(r["warp_long_rep"]), _num(r["warp_short_rep"])),
        "STRique": (_num(r["strique_long_rep"]), _num(r["strique_short_rep"])),
        "DeepRepeat": (_num(r["deeprepeat_allocr_long_peak"]),
                       _num(r["deeprepeat_allocr_short_peak"])),
        "Proposed": (_num(folds.loc[s, "pred_long"]), _num(folds.loc[s, "pred_short"])),
    }
    for tool, (pl, psh) in preds.items():
        for allele, truth, pred in (("long", tl, pl), ("short", ts, psh)):
            rows.append({"sample": s, "tool": tool, "allele": allele,
                         "truth": truth, "pred": pred,
                         "abs_err": abs(pred - truth) if not np.isnan(pred) else np.nan})
panelA = pd.DataFrame(rows)
panelA.to_csv(ANALYSIS / "tool_comparison_per_sample.tsv", sep="\t", index=False)

# ---------------------------------------------------------------- Panel A plot
fig, ax = plt.subplots(figsize=(7, 5))
for tool in ["Proposed", "WarpSTR", "STRique", "DeepRepeat"]:
    d = panelA[(panelA.tool == tool) & panelA.abs_err.notna()]
    ax.scatter(d.truth, d.abs_err, label=tool, color=COLORS[tool],
               s=55, alpha=0.8, edgecolor="white", linewidth=0.5)
ax.set_xlabel("True CAG repeat length")
ax.set_ylabel("Absolute allele error (repeats)")
ax.set_title("Panel A: Allele error vs. repeat length (9 HTT samples)")
ax.axhline(0, color="grey", lw=0.6)
ax.legend(frameon=False)
ax.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(OUT_FIG / "panel_a_error_vs_length.png", dpi=150)
plt.close(fig)


# ---------------------------------------------------------------- Panel D data
def warpstr_per_read(sample):
    p = WARPSTR / sample / "HTT_CAG" / "overview.csv"
    out = []
    with p.open() as f:
        for r in csv.DictReader(f):
            v = _num(r.get("results"))
            if not np.isnan(v):
                out.append(v / 3.0)
    return np.array(out)


def strique_per_read(sample):
    p = STRIQUE / f"{sample}.txt"
    out = []
    with p.open() as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r.get("target") not in (None, "HTT_CAG"):
                continue
            v = _num(r.get("count"))
            if not np.isnan(v) and v > 0:
                out.append(v)
    return np.array(out)


def proposed_per_read(sample):
    intercept, slope = calib[sample]
    out = []
    with INDEX.open() as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r["sample"] != sample:
                continue
            dur = _num(r.get("source_span_abs"))
            if not np.isnan(dur):
                out.append(intercept + slope * dur)
    return np.array(out)


SHOWCASE = ["ND33392", "GM04723"]
# Density-normalised so distribution SHAPE is comparable across tools, since the
# proposed caller uses the capped independent QC read set (~128/sample) while the
# existing tools use all basecalled reads (~3-4k/sample).
fig, axes = plt.subplots(len(SHOWCASE), 3, figsize=(12, 7))
for i, s in enumerate(SHOWCASE):
    tl, ts = folds.loc[s, "truth_long"], folds.loc[s, "truth_short"]
    series = {
        "Proposed": proposed_per_read(s),
        "WarpSTR": warpstr_per_read(s),
        "STRique": strique_per_read(s),
    }
    for j, (tool, vals) in enumerate(series.items()):
        ax = axes[i, j]
        vals = vals[(vals >= 0) & (vals <= 120)]
        ax.hist(vals, bins=np.arange(0, 121, 3), color=COLORS[tool],
                alpha=0.85, density=True)
        ax.axvline(ts, color="black", ls="--", lw=1.2)
        ax.axvline(tl, color="red", ls="--", lw=1.2)
        ax.text(0.97, 0.95, f"n={vals.size}", transform=ax.transAxes,
                ha="right", va="top", fontsize=8, color="grey")
        if i == 0:
            ax.set_title(tool)
        if j == 0:
            ax.set_ylabel(f"{s}\ntruth {int(ts)}/{int(tl)}\ndensity")
        ax.set_xlabel("per-read CAG estimate")
fig.suptitle("Panel D: single-read estimate distributions, density-normalised "
             "(black=short truth, red=long truth)")
fig.tight_layout(rect=(0, 0, 1, 0.96))
fig.savefig(OUT_FIG / "panel_d_single_read_distribution.png", dpi=150)
plt.close(fig)

print("Wrote:")
print(" ", OUT_FIG / "panel_a_error_vs_length.png")
print(" ", OUT_FIG / "panel_d_single_read_distribution.png")
print(" ", ANALYSIS / "tool_comparison_per_sample.tsv")
print("\nPanel A absolute-error summary (mean abs error, repeats):")
print(panelA.groupby("tool").abs_err.mean().round(3).to_string())
