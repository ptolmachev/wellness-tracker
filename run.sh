#!/usr/bin/env bash
set -e

# Go to this script's directory
cd "$(dirname "$0")"

# Load conda (adjust if your conda lives elsewhere)
source ~/miniconda3/etc/profile.d/conda.sh

# Activate your env
conda activate wellness

# If you move this script elsewhere, change the path below
APP_DIR="."
cd "$APP_DIR"

# Run Streamlit app
streamlit run main.py
