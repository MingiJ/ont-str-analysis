#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MANIFEST="${MANIFEST:-${ROOT_DIR}/ont-str-runner/configs/truth_samples.tsv}"
DATA_ROOT="${DATA_ROOT:-${ROOT_DIR}/ont-str-runner/data}"
INCLUDE_UNLABELED="${INCLUDE_UNLABELED:-0}"
WGET_PROGRESS="${WGET_PROGRESS:-dot:giga}"
SAMPLE_FILTER=("$@")

mkdir -p "${DATA_ROOT}"

if [[ ! -f "${MANIFEST}" ]]; then
  echo "Missing manifest: ${MANIFEST}" >&2
  echo "Expected columns: sample, sra_accession, archive_url, truth_long, truth_short, status, include_primary" >&2
  exit 1
fi

want_sample() {
  local sample="$1"
  if [[ "${#SAMPLE_FILTER[@]}" -eq 0 ]]; then
    return 0
  fi
  local requested
  for requested in "${SAMPLE_FILTER[@]}"; do
    if [[ "${requested}" == "${sample}" ]]; then
      return 0
    fi
  done
  return 1
}

echo "Using manifest: ${MANIFEST}"
echo "Writing archives under: ${DATA_ROOT}"

while IFS=$'\t' read -r sample sra_accession archive_url truth_long truth_short status include_primary; do
  if [[ "${sample}" == "sample" ]]; then
    continue
  fi
  if [[ "${include_primary}" != "1" && "${INCLUDE_UNLABELED}" != "1" ]]; then
    continue
  fi
  if ! want_sample "${sample}"; then
    continue
  fi

  sample_dir="${DATA_ROOT}/${sample}"
  archive_path="${sample_dir}/${sample}.tar.gz.1"
  mkdir -p "${sample_dir}"

  echo "[download] ${sample} (${sra_accession})"
  wget -c --progress="${WGET_PROGRESS}" -O "${archive_path}" "${archive_url}"

  echo "[verify] ${archive_path}"
  gzip -t "${archive_path}"
done < "${MANIFEST}"
