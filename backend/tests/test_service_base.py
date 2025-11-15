"""Unit tests for services.service_base module."""
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, UploadFile

from services.service_base import ServiceBase, ALLOWED_FILE_TYPES, MAX_FILE_SIZE


class ConcreteService(ServiceBase):
    """Concrete implementation for testing abstract ServiceBase."""
    pass


class TestServiceBaseInitialization:
    """Tests for ServiceBase initialization."""

    @patch("services.service_base.genai.Client")
    @patch("services.service_base.get_storage_bucket")
    @patch("services.service_base.get_firestore_client")
    def test_initializes_clients(
        self,
        mock_get_firestore_client,
        mock_get_storage_bucket,
        mock_gemini,
    ):
        """Should initialize Gemini, Firestore, and Storage clients via db.session."""
        mock_settings = MagicMock()
        mock_settings.gemini_api_key.get_secret_value.return_value = "test-api-key"

        mock_fs_client = MagicMock()
        mock_bucket = MagicMock()
        mock_get_firestore_client.return_value = mock_fs_client
        mock_get_storage_bucket.return_value = mock_bucket

        service = ConcreteService(mock_settings)

        assert service.settings == mock_settings
        mock_gemini.assert_called_once_with(api_key="test-api-key")
        mock_get_firestore_client.assert_called_once()
        mock_get_storage_bucket.assert_called_once()


class TestValidateFile:
    """Tests for validate_file method."""
    
    @pytest.fixture
    def service(self):
        """Create service instance with mocked dependencies."""
        with patch("services.service_base.genai.Client"), \
             patch("services.service_base.get_firestore_client") as mock_get_fs, \
             patch("services.service_base.get_storage_bucket") as mock_get_bucket:
            mock_settings = MagicMock()
            mock_settings.gemini_api_key.get_secret_value.return_value = "key"
            mock_get_fs.return_value = MagicMock()
            mock_get_bucket.return_value = MagicMock()
            return ConcreteService(mock_settings)
    
    @pytest.mark.asyncio
    async def test_validates_valid_pdf_file(self, service):
        """Should accept valid PDF file."""
        content = b"PDF file content" * 100
        file = UploadFile(
            filename="document.pdf",
            file=BytesIO(content)
        )
        
        file_type, file_size = await service.validate_file(file)
        
        assert file_type == "pdf"
        assert file_size == len(content)
    
    @pytest.mark.asyncio
    async def test_validates_valid_docx_file(self, service):
        """Should accept valid DOCX file."""
        content = b"DOCX content"
        file = UploadFile(
            filename="document.docx",
            file=BytesIO(content)
        )
        
        file_type, file_size = await service.validate_file(file)
        
        assert file_type == "docx"
        assert file_size == len(content)
    
    @pytest.mark.asyncio
    async def test_rejects_file_without_filename(self, service):
        """Should reject file without filename."""
        file = UploadFile(filename="", file=BytesIO(b"content"))
        
        with pytest.raises(HTTPException) as exc_info:
            await service.validate_file(file)
        
        assert exc_info.value.status_code == 400
        assert "filename" in str(exc_info.value.detail).lower()
    
    @pytest.mark.asyncio
    async def test_rejects_file_exceeding_max_size(self, service):
        """Should reject file larger than MAX_FILE_SIZE."""
        large_content = b"x" * (MAX_FILE_SIZE + 1000)
        file = UploadFile(
            filename="large.pdf",
            file=BytesIO(large_content)
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await service.validate_file(file)
        
        assert exc_info.value.status_code == 413
        assert "exceeds maximum" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_rejects_disallowed_file_type(self, service):
        """Should reject file with disallowed extension."""
        file = UploadFile(
            filename="script.exe",
            file=BytesIO(b"content")
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await service.validate_file(file)
        
        assert exc_info.value.status_code == 400
        assert "not allowed" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_accepts_all_allowed_file_types(self, service):
        """Should accept all file types in ALLOWED_FILE_TYPES."""
        for file_type in sorted(ALLOWED_FILE_TYPES):  # Sort for deterministic order
            content = b"test content"
            # Create a fresh BytesIO for each iteration
            file = UploadFile(
                filename=f"test.{file_type}",
                file=BytesIO(content)
            )
            
            result_type, result_size = await service.validate_file(file)
            
            assert result_type == file_type, f"Expected {file_type}, got {result_type} for file test.{file_type}"
            assert result_size == len(content)
    
    @pytest.mark.asyncio
    async def test_file_position_reset_after_validation(self, service):
        """Should reset file position to beginning after reading."""
        content = b"test content"
        file = UploadFile(
            filename="test.pdf",
            file=BytesIO(content)
        )
        
        await service.validate_file(file)
        
        # File should be at position 0 after validation
        new_read = await file.read()
        assert new_read == content


class TestGetCurrentTimestamp:
    """Tests for get_current_timestamp method."""
    
    @pytest.fixture
    def service(self):
        """Create service instance."""
        with patch("services.service_base.genai.Client"), \
             patch("services.service_base.get_firestore_client") as mock_get_fs, \
             patch("services.service_base.get_storage_bucket") as mock_get_bucket:
            mock_settings = MagicMock()
            mock_settings.gemini_api_key.get_secret_value.return_value = "key"
            mock_get_fs.return_value = MagicMock()
            mock_get_bucket.return_value = MagicMock()
            return ConcreteService(mock_settings)
    
    def test_returns_utc_datetime(self, service):
        """Should return timezone-aware UTC datetime."""
        timestamp = service.get_current_timestamp()
        
        assert isinstance(timestamp, datetime)
        assert timestamp.tzinfo == timezone.utc
    
    def test_returns_current_time(self, service):
        """Should return current time (within 1 second)."""
        before = datetime.now(timezone.utc)
        timestamp = service.get_current_timestamp()
        after = datetime.now(timezone.utc)
        
        assert before <= timestamp <= after


class TestConstants:
    """Tests for module-level constants."""
    
    def test_allowed_file_types_contains_common_formats(self):
        """Should include common document formats."""
        expected_types = {"pdf", "docx", "txt", "md", "csv"}
        assert expected_types.issubset(ALLOWED_FILE_TYPES)
    
    def test_max_file_size_matches_gemini_limit(self):
        """Should be 100 MB as per Gemini File Search limits."""
        assert MAX_FILE_SIZE == 100 * 1024 * 1024
