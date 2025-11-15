from core.config import get_settings
from .service_base import ServiceBase
from .file_service import FileService
from .chat_service import ChatService

# --- Lazy initialization to avoid loading settings at import time ---
_file_service = None
_chat_service = None

def get_file_service() -> FileService:
    """
        Get or create file service instance.
    """
    global _file_service
    if _file_service is None:
        settings = get_settings()
        _file_service = FileService(settings)
    return _file_service

def get_chat_service() -> ChatService:
    """
        Get or create chat service instance."""
    global _chat_service
    if _chat_service is None:
        settings = get_settings()
        _chat_service = ChatService(settings)
    return _chat_service

__all__ = ["get_file_service", "get_chat_service", "ServiceBase", "FileService", "ChatService"]
