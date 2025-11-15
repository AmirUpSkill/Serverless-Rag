from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from db.base import FirestoreDocument

# --- Allowed file types ---
ALLOWED_FILE_TYPES = {"pdf", "docx", "doc", "txt", "md", "csv", "xlsx", "xls"}

# --- Max file size: 100 MB (as per Gemini File Search limits) ---
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024


class FileMetadataCreate(BaseModel):
    """
        Schema for creating new file metadata.
    """

    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., min_length=1, max_length=10)
    size_bytes: int = Field(..., gt=0, le=MAX_FILE_SIZE_BYTES)
    storage_path: str = Field(..., min_length=1, description="Firebase Storage path")

    # --- Gemini File Search linkage ---
    gemini_file_search_store_name: str = Field(
        ...,
        description="Full resource name of the Gemini File Search store",
    )
    gemini_document_name: str | None = Field(
        None,
        description="Gemini document resource name (if available)",
    )
    gemini_operation_name: str | None = Field(
        None,
        description="Gemini operation name for async import tracking",
    )

    # --- AI-generated content ---
    summary: str | None = Field(None, max_length=500, description="AI summary (3 lines max)")
    keywords: list[str] = Field(default_factory=list, max_length=6)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "research_paper.pdf",
                "type": "pdf",
                "size_bytes": 2_500_000,
                "storage_path": "files/user123/abc-def-ghi/research_paper.pdf",
                "gemini_file_search_store_name": "fileSearchStores/my-store-123",
                "summary": "Research paper on AI advancements in 2024...",
                "keywords": ["AI", "research", "2024", "machine learning"],
            }
        }
    )

    @field_validator("type")
    @classmethod
    def validate_file_type(cls, v: str) -> str:
        """
            Validate file type is in allowed list.
        """
        v_lower = v.lower().strip()
        if v_lower not in ALLOWED_FILE_TYPES:
            raise ValueError(
                f"File type '{v}' not allowed. Allowed types: {', '.join(ALLOWED_FILE_TYPES)}"
            )
        return v_lower

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, v: list[str]) -> list[str]:
        """
            Validate keywords: max 6 items, each max 50 chars.
        """
        if len(v) > 6:
            raise ValueError("Maximum 6 keywords allowed")

        validated: list[str] = []
        for keyword in v:
            keyword = keyword.strip()
            if len(keyword) > 50:
                raise ValueError(f"Keyword '{keyword}' exceeds 50 characters")
            if keyword:
                validated.append(keyword)

        return validated

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, v: str | None) -> str | None:
        """
            Ensure summary is not just whitespace.
        """
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class FileMetadata(FirestoreDocument, FileMetadataCreate):
    """
        Full file metadata schema including Firestore-managed fields.

        Inherits from both FirestoreDocument (for id, timestamps) and
        FileMetadataCreate (for file-specific fields).
    """

    # --- Override to make these fields explicit ---
    id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class FileMetadataResponse(BaseModel):
    """
        Response schema for file metadata API responses.
    """

    id: str
    name: str
    type: str
    size_bytes: int
    summary: str | None = None
    keywords: list[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Pagination(BaseModel):
    """
        Pagination metadata for list endpoints.
    """

    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Number of items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    total_files: int = Field(..., ge=0, description="Total number of files")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "page": 1,
                "page_size": 12,
                "total_pages": 5,
                "total_files": 58,
            }
        }
    )


class FileListResponse(BaseModel):
    """
        Paginated response for file listing.
    """

    files: list[FileMetadataResponse]
    pagination: Pagination = Field(..., description="Pagination metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "files": [
                    {
                        "id": "file123",
                        "name": "document.pdf",
                        "type": "pdf",
                        "size_bytes": 2_500_000,
                        "summary": "AI summary of document...",
                        "keywords": ["keyword1", "keyword2"],
                        "created_at": "2024-11-13T10:00:00Z",
                        "updated_at": "2024-11-13T10:00:00Z",
                    }
                ],
                "pagination": {
                    "page": 1,
                    "page_size": 12,
                    "total_pages": 5,
                    "total_files": 58,
                },
            }
        }
    )