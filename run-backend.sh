#!/bin/bash
# Run FastAPI backend with uv
echo "Starting Serverless RAG Backend..."
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
