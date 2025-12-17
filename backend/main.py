import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1 import api_router
from core.config import get_settings

# --- Configure logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# --- Get settings ---
settings = get_settings()

# Create FastAPI application
app = FastAPI(
    title="Servless RAG API",
    description="Retrieval-Augmented Generation API powered by Gemini File Search",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# --- Configure CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include API routes with /api/v1 prefix ----
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["health"])
async def root():
    """
    Root endpoint - health check.
    """
    return {
        "message": "Servless RAG API is running",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint.
    """
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        reload=True, 
    )