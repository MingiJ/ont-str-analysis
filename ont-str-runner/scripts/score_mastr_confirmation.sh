#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}
WORK_ROOT=${MASTR_WORK_ROOT:-$REPO_ROOT/ont-str-runner/work/mastr}
PYTHON=${PYTHON:-$REPO_ROOT/.venv/bin/python}
TRUTH=${MASTR_TRUTH_MANIFEST:-$REPO_ROOT/ont-str-runner/configs/mastr_confirmation_truth.tsv}
PREDICTIONS=${MASTR_PREDICTIONS:-$WORK_ROOT/mastr_sealed_predictions.tsv}
PREDICTION_HASH=${MASTR_PREDICTION_HASH:-$PREDICTIONS.sha256}
FORCE_SCORE=${FORCE_SCORE:-0}

if [[ ! -s "$PREDICTIONS" || ! -s "$PREDICTION_HASH" ]]; then
  echo "Missing sealed predictions or hash" >&2
  exit 1
fi
sha256sum -c "$PREDICTION_HASH"
if [[ -e "$WORK_ROOT/mastr_frozen_decision.tsv" && "$FORCE_SCORE" != 1 ]]; then
  echo "Refusing to overwrite an existing MASTR decision without FORCE_SCORE=1" >&2
  exit 1
fi

sha256sum "$PREDICTIONS" "$TRUTH" > "$WORK_ROOT/mastr_scoring_inputs.sha256.tmp"
mv "$WORK_ROOT/mastr_scoring_inputs.sha256.tmp" "$WORK_ROOT/mastr_scoring_inputs.sha256"

"$PYTHON" "$REPO_ROOT/src/algorithm/evaluate_mastr_confirmation.py" score \
  --predictions "$PREDICTIONS" \
  --truth-manifest "$TRUTH" \
  --output "$WORK_ROOT/mastr_scores.tsv" \
  --summary "$WORK_ROOT/mastr_score_summary.tsv" \
  --decision "$WORK_ROOT/mastr_frozen_decision.tsv"
sha256sum \
  "$WORK_ROOT/mastr_scores.tsv" \
  "$WORK_ROOT/mastr_score_summary.tsv" \
  "$WORK_ROOT/mastr_frozen_decision.tsv" \
  > "$WORK_ROOT/mastr_scored_outputs.sha256"
