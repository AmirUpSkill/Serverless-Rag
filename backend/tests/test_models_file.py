"""Unit tests for models.file module."""
from datetime import datetime

# --- Third-party imports ---
import pytest
from pydantic import ValidationError

# --- Internal imports ---
from models.file import (
    ALLOWED_FILE_TYPES,
    MAX_FILE_SIZE_BYTES,
    FileListResponse,
    FileMetadata,
    FileMetadataCreate,
    FileMetadataResponse,
    Pagination,
)


class TestFileMetadataCreate:
    """Tests for FileMetadataCreate model."""
    
    def test_valid_file_metadata(self):
        """Should create valid file metadata."""
        data = {
            "name": "test.pdf",
            "type": "pdf",
            "size_bytes": 1000000,
            "storage_path": "files/user123/test.pdf",
            "gemini_file_search_store_name": "fileSearchStores/store123",
            "summary": "Test summary",
            "keywords": ["test", "pdf"]
        }
        
        file_meta = FileMetadataCreate(**data)
        
        assert file_meta.name == "test.pdf"
        assert file_meta.type == "pdf"
        assert file_meta.size_bytes == 1000000
        assert file_meta.keywords == ["test", "pdf"]
    
    def test_file_type_validation_lowercase(self):
        """Should convert file type to lowercase."""
        file_meta = FileMetadataCreate(
            name="test.pdf",
            type="PDF",  # --- Uppercase ---
            size_bytes=1000,
            storage_path="files/test.pdf",
            gemini_file_search_store_name="store123"
        )
        
        assert file_meta.type == "pdf"
    
    def test_file_type_validation_invalid(self):
        """Should reject invalid file types."""
        with pytest.raises(ValidationError) as exc_info:
            FileMetadataCreate(
                name="test.exe",
                type="exe",  # --- Not in ALLOWED_FILE_TYPES ---
                size_bytes=1000,
                storage_path="files/test.exe",
                gemini_file_search_store_name="store123"
            )
        
        assert "File type 'exe' not allowed" in str(exc_info.value)
    
    def test_keywords_max_6(self):
        """Should reject more than 6 keywords."""
        with pytest.raises(ValidationError) as exc_info:
            FileMetadataCreate(
                name="test.pdf",
                type="pdf",
                size_bytes=1000,
                storage_path="files/test.pdf",
                gemini_file_search_store_name="store123",
                keywords=["k1", "k2", "k3", "k4", "k5", "k6", "k7"]  # --- 7 keywords ---
            )
        
        # --- Check error contains keywords field validation ---
        error_str = str(exc_info.value)
        assert "keywords" in error_str.lower() and ("6" in error_str or "maximum" in error_str.lower())
    
    def test_keywords_max_length(self):
        """Should reject keywords longer than 50 chars."""
        long_keyword = "a" * 51
        
        with pytest.raises(ValidationError) as exc_info:
            FileMetadataCreate(
                name="test.pdf",
                type="pdf",
                size_bytes=1000,
                storage_path="files/test.pdf",
                gemini_file_search_store_name="store123",
                keywords=[long_keyword]
            )
        
        assert "exceeds 50 characters" in str(exc_info.value)
    
    def test_keywords_strips_whitespace(self):
        """Should strip whitespace from keywords."""
        file_meta = FileMetadataCreate(
            name="test.pdf",
            type="pdf",
            size_bytes=1000,
            storage_path="files/test.pdf",
            gemini_file_search_store_name="store123",
            keywords=["  keyword1  ", " keyword2 ", "keyword3"]
        )
        
        assert file_meta.keywords == ["keyword1", "keyword2", "keyword3"]
    
    def test_keywords_removes_empty_strings(self):
        """Should remove empty strings from keywords."""
        file_meta = FileMetadataCreate(
            name="test.pdf",
            type="pdf",
            size_bytes=1000,
            storage_path="files/test.pdf",
            gemini_file_search_store_name="store123",
            keywords=["keyword1", "", "  ", "keyword2"]
        )
        
        assert file_meta.keywords == ["keyword1", "keyword2"]
    
    def test_summary_strips_whitespace(self):
        """Should strip whitespace from summary."""
        file_meta = FileMetadataCreate(
            name="test.pdf",
            type="pdf",
            size_bytes=1000,
            storage_path="files/test.pdf",
            gemini_file_search_store_name="store123",
            summary="  Test summary  "
        )
        
        assert file_meta.summary == "Test summary"
    
    def test_summary_empty_becomes_none(self):
        """Should convert empty/whitespace summary to None."""
        file_meta = FileMetadataCreate(
            name="test.pdf",
            type="pdf",
            size_bytes=1000,
            storage_path="files/test.pdf",
            gemini_file_search_store_name="store123",
            summary="   "
        )
        
        assert file_meta.summary is None
    
    def test_size_bytes_validation(self):
        """Should validate file size constraints."""
        # --- Size must be > 0 ---
        with pytest.raises(ValidationError):
            FileMetadataCreate(
                name="test.pdf",
                type="pdf",
                size_bytes=0,
                storage_path="files/test.pdf",
                gemini_file_search_store_name="store123"
            )
        
        # --- Size must be <= MAX_FILE_SIZE_BYTES ---
        with pytest.raises(ValidationError):
            FileMetadataCreate(
                name="test.pdf",
                type="pdf",
                size_bytes=MAX_FILE_SIZE_BYTES + 1,
                storage_path="files/test.pdf",
                gemini_file_search_store_name="store123"
            )
    
    def test_name_length_validation(self):
        """Should validate name length."""
        # --- Name cannot be empty ---
        with pytest.raises(ValidationError):
            FileMetadataCreate(
                name="",
                type="pdf",
                size_bytes=1000,
                storage_path="files/test.pdf",
                gemini_file_search_store_name="store123"
            )
        
        # --- Name cannot exceed 255 chars ---
        with pytest.raises(ValidationError):
            FileMetadataCreate(
                name="a" * 256,
                type="pdf",
                size_bytes=1000,
                storage_path="files/test.pdf",
                gemini_file_search_store_name="store123"
            )
    
    def test_optional_gemini_fields(self):
        """Should allow optional Gemini linkage fields."""
        file_meta = FileMetadataCreate(
            name="test.pdf",
            type="pdf",
            size_bytes=1000,
            storage_path="files/test.pdf",
            gemini_file_search_store_name="store123",
            gemini_document_name="documents/doc123",
            gemini_operation_name="operations/op123"
        )
        
        assert file_meta.gemini_document_name == "documents/doc123"
        assert file_meta.gemini_operation_name == "operations/op123"


class TestFileMetadata:
    """Tests for FileMetadata model (extends FirestoreDocument)."""
    
    def test_inherits_firestore_fields(self):
        """Should have Firestore document fields."""
        file_meta = FileMetadata(
            id="file123",
            name="test.pdf",
            type="pdf",
            size_bytes=1000,
            storage_path="files/test.pdf",
            gemini_file_search_store_name="store123",
            created_at=datetime(2024, 1, 1, 10, 0, 0),
            updated_at=datetime(2024, 1, 1, 10, 0, 0)
        )
        
        assert file_meta.id == "file123"
        assert file_meta.created_at == datetime(2024, 1, 1, 10, 0, 0)
        assert file_meta.updated_at == datetime(2024, 1, 1, 10, 0, 0)
    
    def test_to_dict_method(self):
        """Should convert to dict using FirestoreDocument method."""
        file_meta = FileMetadata(
            id="file123",
            name="test.pdf",
            type="pdf",
            size_bytes=1000,
            storage_path="files/test.pdf",
            gemini_file_search_store_name="store123",
            keywords=["test"]
        )
        
        result = file_meta.to_dict()
        
        assert "id" not in result  # --- Excluded by default ---
        assert result["name"] == "test.pdf"
        assert result["type"] == "pdf"
        assert result["keywords"] == ["test"]


class TestFileMetadataResponse:
    """Tests for FileMetadataResponse model."""
    
    def test_creates_response_model(self):
        """Should create response model for API."""
        response = FileMetadataResponse(
            id="file123",
            name="test.pdf",
            type="pdf",
            size_bytes=1000,
            summary="Test summary",
            keywords=["test"],
            created_at=datetime(2024, 1, 1, 10, 0, 0),
            updated_at=datetime(2024, 1, 1, 10, 0, 0)
        )
        
        assert response.id == "file123"
        assert response.name == "test.pdf"
        assert response.summary == "Test summary"
    
    def test_from_attributes_config(self):
        """Should support from_attributes for ORM-like conversion."""
        # --- Create a mock object with attributes ---
        class MockFile:
            id = "file123"
            name = "test.pdf"
            type = "pdf"
            size_bytes = 1000
            summary = None
            keywords = []
            created_at = datetime(2024, 1, 1, 10, 0, 0)
            updated_at = datetime(2024, 1, 1, 10, 0, 0)
        
        mock_file = MockFile()
        response = FileMetadataResponse.model_validate(mock_file)
        
        assert response.id == "file123"
        assert response.name == "test.pdf"


class TestFileListResponse:
    """Tests for FileListResponse model."""
    
    def test_creates_paginated_response(self):
        """Should create paginated file list response."""
        files = [
            FileMetadataResponse(
                id=f"file{i}",
                name=f"test{i}.pdf",
                type="pdf",
                size_bytes=1000,
                keywords=[],
                created_at=datetime(2024, 1, 1, 10, 0, 0),
                updated_at=datetime(2024, 1, 1, 10, 0, 0)
            )
            for i in range(3)
        ]
        
        pagination = Pagination(
            page=1,
            page_size=12,
            total_pages=1,
            total_files=3
        )
        
        response = FileListResponse(files=files, pagination=pagination)
        
        assert len(response.files) == 3
        assert response.pagination.page == 1
        assert response.pagination.total_files == 3


class TestConstants:
    """Tests for module constants."""
    
    def test_allowed_file_types(self):
        """Should define allowed file types."""
        assert isinstance(ALLOWED_FILE_TYPES, set)
        assert "pdf" in ALLOWED_FILE_TYPES
        assert "docx" in ALLOWED_FILE_TYPES
        assert "txt" in ALLOWED_FILE_TYPES
    
    def test_max_file_size(self):
        """Should define max file size as 100MB."""
        assert MAX_FILE_SIZE_BYTES == 100 * 1024 * 1024
