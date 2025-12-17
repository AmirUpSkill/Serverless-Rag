param(
    [string]$ServerHost = "0.0.0.0",
    [int]$ServerPort = 8000,
    [int]$Workers = 4,
    [string]$LogLevel = "info"
)

Write-Host "Starting Servless RAG backend (PROD) on ${ServerHost}:${ServerPort} with ${Workers} workers ..." -ForegroundColor Green

# Use uv to run uvicorn with production-friendly settings
uv run uvicorn main:app `
    --host $ServerHost `
    --port $ServerPort `
    --workers $Workers `
    --log-level $LogLevel `
    --proxy-headers `
    --forwarded-allow-ips="*"
