#!/usr/bin/env bash
set -e

# Name of the conda environment
ENV_NAME="wellness"

# Go to the directory where this script lives
cd "$(dirname "$0")"

# Make conda available in this script
eval "$(conda shell.bash hook)"

echo "Creating conda environment: ${ENV_NAME} (if it doesn't exist)..."
if ! conda env list | grep -q "^${ENV_NAME}\s"; then
    conda create -y -n "${ENV_NAME}" python=3.11
else
    echo "Environment ${ENV_NAME} already exists, skipping creation."
fi

echo "Activating environment: ${ENV_NAME}"
conda activate "${ENV_NAME}"

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing Python packages..."
pip install streamlit pandas pyyaml

echo
echo "Done."
echo "To run the app next time:"
echo "  conda activate ${ENV_NAME}"
echo "  streamlit run main.py"
