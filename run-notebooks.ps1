# Run JupyterLab with uv (requires optional notebooks dependencies)
Write-Host "Starting JupyterLab..." -ForegroundColor Green
Write-Host "Make sure you've installed optional dependencies: uv sync --extra notebooks" -ForegroundColor Yellow
uv run --extra notebooks jupyter lab notebooks
