from fastapi import APIRouter

from api.v1.endpoints import chat, files

# --- Create the main v1 API router ---
api_router = APIRouter()

# --- Include all endpoint routers ----
api_router.include_router(files.router)
api_router.include_router(chat.router)