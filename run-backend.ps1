# Run FastAPI backend with uv
Write-Host "Starting Serverless RAG Backend..." -ForegroundColor Green
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
