param(
    [string]$ServerHost = "0.0.0.0",
    [int]$ServerPort = 8000
)

Write-Host "Starting Servless RAG backend (DEV) on ${ServerHost}:${ServerPort} ..." -ForegroundColor Cyan

# Use uv to run uvicorn using the project environment
uv run uvicorn main:app `
    --host $ServerHost `
    --port $ServerPort `
    --reload `
    --log-level debug
