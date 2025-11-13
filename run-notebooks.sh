#!/bin/bash
# Run JupyterLab with uv (requires optional notebooks dependencies)
echo "Starting JupyterLab..."
echo "Make sure you've installed optional dependencies: uv sync --extra notebooks"
uv run --extra notebooks jupyter lab notebooks
