#!/usr/bin/env bash
set -euo pipefail

SAMPLE=${1:-}
MODE=${2:-ontfast5}

if [[ -z "$SAMPLE" ]]; then
  echo "Usage: $0 <SAMPLE> [ontfast5|h5py]" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_ROOT_DEFAULT="$ROOT/data"
DATA_ROOT="${DATA_ROOT:-$DATA_ROOT_DEFAULT}"
DATA_ROOT_REAL="$(realpath "$DATA_ROOT")"
SAMPLE_DIR="$DATA_ROOT_REAL/$SAMPLE"
FAST5_DIR="$SAMPLE_DIR/workspace/pass/0"

if [[ ! -d "$FAST5_DIR" ]]; then
  echo "Missing FAST5 dir: $FAST5_DIR" >&2
  exit 1
fi

OUT="$SAMPLE_DIR/htt.f5index.$MODE"

EXTRA_VOLUMES=()
if [[ -d "/Volumes/Legion" ]]; then
  EXTRA_VOLUMES+=(-v "/Volumes/Legion:/Volumes/Legion")
fi

export SAMPLE_DIR FAST5_DIR OUT MODE

# Build index inside ont-fast5-api container to ensure h5py/ont_fast5_api availability.
PYCODE=$(cat <<'PY'
import os
from pathlib import Path

mode = os.environ.get("MODE", "ontfast5")
sample_dir = Path(os.environ["SAMPLE_DIR"])
fast5_dir = Path(os.environ["FAST5_DIR"])
out_path = Path(os.environ["OUT"])

if mode not in {"ontfast5", "h5py"}:
    raise SystemExit(f"Unknown mode: {mode}")

if mode == "ontfast5":
    from ont_fast5_api.fast5_interface import get_fast5_file
else:
    import h5py

rows = []
for fp in fast5_dir.rglob("*.fast5"):
    try:
        rel = fp.relative_to(sample_dir).as_posix()
    except Exception:
        continue
    read_ids = []
    if mode == "ontfast5":
        try:
            with get_fast5_file(str(fp), mode="r") as f5:
                read_ids = list(f5.get_read_ids())
        except Exception:
            continue
    else:
        try:
            with h5py.File(fp, "r") as f:
                # Fast5 can be single or multi; read_ids live under /Raw/Reads/*/read_id
                if "Raw" in f and "Reads" in f["Raw"]:
                    reads_group = f["Raw/Reads"]
                    for read_key in reads_group:
                        g = reads_group[read_key]
                        rid = g.attrs.get("read_id")
                        if isinstance(rid, bytes):
                            rid = rid.decode()
                        if rid:
                            read_ids.append(str(rid))
        except Exception:
            continue
    for rid in read_ids:
        rows.append(f"{rid}\t{rel}")

rows.sort()
out_path.write_text("\n".join(rows) + ("\n" if rows else ""))
print(f"Wrote {out_path} with {len(rows)} entries using mode={mode}")
PY
)

docker run --rm \
  -v "$DATA_ROOT_REAL:$DATA_ROOT_REAL" \
  "${EXTRA_VOLUMES[@]}" \
  -e SAMPLE_DIR="$SAMPLE_DIR" \
  -e FAST5_DIR="$FAST5_DIR" \
  -e OUT="$OUT" \
  -e MODE="$MODE" \
  -w "$SAMPLE_DIR" \
  --entrypoint python \
  ttubb/ont-fast5-api:latest \
  -c "$PYCODE"
