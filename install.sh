#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="wellness"
PY_VER="3.11"
REQ_PKGS=(streamlit pandas pyyaml plotly)

cd "$(dirname "$0")"

die(){ echo "ERROR: $*" >&2; exit 1; }

have(){ command -v "$1" >/dev/null 2>&1; }

# --- locate conda robustly ---
if have conda; then
  CONDA_BIN="$(command -v conda)"
else
  # common install locations
  for c in \
    "$HOME/miniconda3/bin/conda" \
    "$HOME/anaconda3/bin/conda" \
    "$HOME/mambaforge/bin/conda" \
    "$HOME/miniforge3/bin/conda" \
    "/opt/homebrew/Caskroom/miniconda/base/bin/conda" \
    "/opt/homebrew/Caskroom/anaconda/base/bin/conda" \
    "/usr/local/Caskroom/miniconda/base/bin/conda" \
    "/usr/local/Caskroom/anaconda/base/bin/conda"
  do
    [ -x "$c" ] && CONDA_BIN="$c" && break
  done
fi

[ "${CONDA_BIN:-}" ] || die "conda not found. Install Miniconda/Anaconda/Miniforge, then re-run."

# --- load conda into this shell ---
eval "$("$CONDA_BIN" shell.bash hook)" || {
  # fallback to conda.sh if hook fails
  CONDA_BASE="$("$CONDA_BIN" info --base)"
  [ -f "$CONDA_BASE/etc/profile.d/conda.sh" ] || die "Cannot load conda hook or conda.sh at: $CONDA_BASE/etc/profile.d/conda.sh"
  # shellcheck disable=SC1090
  source "$CONDA_BASE/etc/profile.d/conda.sh"
}

echo "Using conda: $CONDA_BIN"
echo "Conda base: $(conda info --base)"

# --- create env if missing ---
if conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
  echo "Environment '$ENV_NAME' already exists."
else
  echo "Creating environment '$ENV_NAME' (python=$PY_VER)..."
  conda create -y -n "$ENV_NAME" "python=$PY_VER"
fi

echo "Activating '$ENV_NAME'..."
conda activate "$ENV_NAME"

echo "Upgrading pip..."
python -m pip install -U pip

echo "Installing packages: ${REQ_PKGS[*]}"
python -m pip install -U "${REQ_PKGS[@]}"

echo
echo "Done."
echo "Run:"
echo "  conda activate $ENV_NAME"
echo "  streamlit run main.py"

cat > Tracker.command <<'EOF'
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
EOF

chmod +x Tracker.command
echo "Created launcher: $(pwd)/Tracker.command"