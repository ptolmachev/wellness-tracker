#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Load conda robustly
if command -v conda >/dev/null 2>&1; then
  CONDA_BIN="$(command -v conda)"
else
  for c in "$HOME/miniconda3/bin/conda" "$HOME/anaconda3/bin/conda" "$HOME/mambaforge/bin/conda" "$HOME/miniforge3/bin/conda"; do
    [ -x "$c" ] && CONDA_BIN="$c" && break
  done
fi
[ "${CONDA_BIN:-}" ] || { echo "ERROR: conda not found"; exit 1; }

eval "$("$CONDA_BIN" shell.bash hook)" || {
  CONDA_BASE="$("$CONDA_BIN" info --base)"
  # shellcheck disable=SC1090
  source "$CONDA_BASE/etc/profile.d/conda.sh"
}

conda activate wellness
streamlit run main.py
