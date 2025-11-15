from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FileResponse(BaseModel):
    """Public-facing schema for a single file in API responses.

    This is the DTO that maps the backend `FileMetadata` model to the
    API contract's "file" object.
    """

    id: str = Field(..., description="Unique identifier for the file.")
    name: str = Field(..., description="The name of the file.")
    type: str = Field(..., description="The file type (e.g. 'pdf', 'docx').")
    size_bytes: int = Field(..., description="Size of the file in bytes.")
    summary: str | None = Field(None, description="AI-generated summary of the document.")
    keywords: list[str] = Field(
        default_factory=list,
        description="AI-generated keywords describing the document.",
    )
    created_at: datetime = Field(
        ..., description="Timestamp when the file metadata was created."
    )
    updated_at: datetime = Field(
        ..., description="Timestamp when the file metadata was last updated."
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "file_123",
                "name": "document.pdf",
                "type": "pdf",
                "size_bytes": 2_500_000,
                "summary": "AI-generated summary of the document...",
                "keywords": ["keyword1", "keyword2"],
                "created_at": "2024-11-20T10:00:00Z",
                "updated_at": "2024-11-20T10:05:00Z",
            }
        },
    )


class Pagination(BaseModel):
    """Pagination metadata for list endpoints."""

    page: int = Field(..., ge=1, description="Current page number.")
    page_size: int = Field(..., ge=1, description="Number of items per page.")
    total_pages: int = Field(..., ge=0, description="Total number of pages.")
    total_files: int = Field(..., ge=0, description="Total number of files across all pages.")

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
    """Schema for a paginated list of files in API responses."""

    files: list[FileResponse]
    pagination: Pagination = Field(..., description="Pagination metadata.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "files": [
                    {
                        "id": "file_abc",
                        "name": "report_q3.docx",
                        "type": "docx",
                        "size_bytes": 1_250_000,
                        "summary": "Q3 financial report summary...",
                        "keywords": ["finance", "report", "q3"],
                        "created_at": "2024-11-21T14:30:00Z",
                        "updated_at": "2024-11-21T14:45:00Z",
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
