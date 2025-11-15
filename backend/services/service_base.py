import mimetypes
from abc import ABC
from datetime import datetime, timezone
from typing import Tuple

from fastapi import UploadFile, HTTPException, status
from google import genai

from core.config import Settings
from db.session import get_firestore_client, get_storage_bucket

# --- Constants ---
ALLOWED_FILE_TYPES = {
    "pdf",
    "docx",
    "doc",
    "txt",
    "md",
    "csv",
    "xlsx",
    "xls",
    "pptx",
    "ppt",
}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB per Gemini limits


class ServiceBase(ABC):
    """
        Base class for all services providing common clients and utilities.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.gemini_client = genai.Client(
            api_key=settings.gemini_api_key.get_secret_value()
        )
        self.firestore_client = get_firestore_client()
        self.storage_bucket = get_storage_bucket()

    async def validate_file(self, file: UploadFile) -> Tuple[str, int]:
        """
            Validate file type and size.

        Returns:
            Tuple[str, int]: (file_type, file_size_bytes).
        """
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must have a filename",
            )

        content = await file.read()
        file_size = len(content)
        # ---  Reset position so callers can re-read the file ---
        await file.seek(0)

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"File size ({file_size} bytes) exceeds maximum "
                    f"({MAX_FILE_SIZE} bytes)"
                ),
            )

        # --- Extract file extension from filename ---
        file_extension = file.filename.split(".")[-1].lower()

        # --- Prefer the file extension if it's already in allowed types ---
        if file_extension in ALLOWED_FILE_TYPES:
            file_type = file_extension
        else:
            # --- Try to map MIME type to common extension if needed ---
            mime_type = mimetypes.guess_type(file.filename)[0]
            if mime_type:
                mime_to_ext = {
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
                    "application/vnd.ms-excel": "xls",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
                    "application/vnd.ms-powerpoint": "ppt",
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
                    "text/markdown": "md",
                    "text/plain": "txt",
                    "text/csv": "csv",
                }
                file_type = mime_to_ext.get(mime_type, file_extension)
            else:
                file_type = file_extension

        if file_type not in ALLOWED_FILE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type '{file_type}' not allowed",
            )

        return file_type, file_size

    def get_current_timestamp(self) -> datetime:
        """
            Get timezone-aware UTC timestamp.
        """
        return datetime.now(timezone.utc)
