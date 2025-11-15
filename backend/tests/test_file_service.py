"""Unit tests for services.file_service module."""
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
from fastapi import HTTPException, UploadFile

from services.file_service import FileService, FILES_COLLECTION
from schemas.file import FileResponse, FileListResponse, Pagination


@pytest.fixture
def mock_settings():
    """Create mock settings object."""
    settings = MagicMock()
    settings.gemini_api_key.get_secret_value.return_value = "test-api-key"
    return settings


@pytest.fixture
def file_service(mock_settings):
    """Create FileService instance with mocked dependencies."""
    with patch("services.service_base.genai.Client"), \
         patch("services.service_base.get_firestore_client") as mock_get_fs, \
         patch("services.service_base.get_storage_bucket"):

        mock_fs_client = MagicMock()
        mock_get_fs.return_value = mock_fs_client

        service = FileService(mock_settings)
        service.collection = MagicMock()  # Mock the collection

        return service


class TestFileServiceInitialization:
    """Tests for FileService initialization."""
    
    def test_initializes_with_files_collection(self, file_service):
        """Should initialize with 'files' collection reference."""
        assert file_service.collection is not None


class TestUploadFile:
    """Tests for upload_file method."""
    
    @pytest.mark.asyncio
    async def test_successful_file_upload(self, file_service):
        """Should successfully upload file and return FileResponse."""
        # Setup
        content = b"Test PDF content"
        upload_file = UploadFile(
            filename="test.pdf",
            file=BytesIO(content)
        )
        
        # Mock validate_file
        file_service.validate_file = AsyncMock(return_value=("pdf", len(content)))
        
        # Mock helper methods
        file_service._generate_storage_path = MagicMock(return_value="files/user123/test.pdf")
        file_service._upload_to_storage = AsyncMock(return_value="https://storage.url/test.pdf")
        
        # Mock Firestore save
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "file123"
        file_service._save_metadata = AsyncMock(return_value=mock_doc_ref)
        
        # Execute
        result = await file_service.upload_file(upload_file, user_id="user123")
        
        # Assert
        assert isinstance(result, FileResponse)
        assert result.id == "file123"
        assert result.name == "test.pdf"
        assert result.type == "pdf"
        assert result.summary is None
        assert result.keywords == []
        
        # Verify calls
        file_service.validate_file.assert_called_once_with(upload_file)
        file_service._generate_storage_path.assert_called_once_with("user123", "test.pdf")
        file_service._upload_to_storage.assert_called_once_with(upload_file, "files/user123/test.pdf")
    
    @pytest.mark.asyncio
    async def test_upload_file_validation_failure(self, file_service):
        """Should propagate validation errors."""
        upload_file = UploadFile(filename="test.exe", file=BytesIO(b"content"))
        
        file_service.validate_file = AsyncMock(
            side_effect=HTTPException(status_code=400, detail="Invalid file type")
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await file_service.upload_file(upload_file, user_id="user123")
        
        assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_upload_file_storage_failure(self, file_service):
        """Should handle storage upload failures."""
        upload_file = UploadFile(filename="test.pdf", file=BytesIO(b"content"))
        
        file_service.validate_file = AsyncMock(return_value=("pdf", 7))
        file_service._generate_storage_path = MagicMock(return_value="path")
        file_service._upload_to_storage = AsyncMock(
            side_effect=HTTPException(status_code=500, detail="Storage failed")
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await file_service.upload_file(upload_file, user_id="user123")
        
        assert exc_info.value.status_code == 500


class TestListFiles:
    """Tests for list_files method."""
    
    @pytest.mark.asyncio
    async def test_list_files_returns_paginated_response(self, file_service):
        """Should return paginated file list."""
        # Mock Firestore query
        mock_doc1 = MagicMock()
        mock_doc1.id = "file1"
        mock_doc1.to_dict.return_value = {
            "name": "doc1.pdf",
            "type": "pdf",
            "summary": "Summary 1",
            "keywords": ["key1"],
            "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc)
        }
        
        mock_doc2 = MagicMock()
        mock_doc2.id = "file2"
        mock_doc2.to_dict.return_value = {
            "name": "doc2.docx",
            "type": "docx",
            "keywords": [],
            "created_at": datetime(2024, 1, 2, tzinfo=timezone.utc)
        }
        
        # Setup query chain
        mock_query = MagicMock()
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = [mock_doc1, mock_doc2]
        
        file_service.collection.order_by.return_value = mock_query
        
        # Mock count
        mock_count_result = MagicMock()
        mock_count_result.value = 25
        file_service.collection.count.return_value.get.return_value = [[mock_count_result]]
        
        # Execute
        result = await file_service.list_files(page=1, page_size=12)
        
        # Assert
        assert isinstance(result, FileListResponse)
        assert len(result.files) == 2
        assert result.files[0].id == "file1"
        assert result.files[1].id == "file2"
        assert result.pagination.page == 1
        assert result.pagination.page_size == 12
        assert result.pagination.total_files == 25
        assert result.pagination.total_pages == 3  # ceil(25/12) = 3
    
    @pytest.mark.asyncio
    async def test_list_files_handles_empty_results(self, file_service):
        """Should handle empty file list."""
        mock_query = MagicMock()
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = []
        
        file_service.collection.order_by.return_value = mock_query
        
        mock_count_result = MagicMock()
        mock_count_result.value = 0
        file_service.collection.count.return_value.get.return_value = [[mock_count_result]]
        
        result = await file_service.list_files(page=1, page_size=12)
        
        assert len(result.files) == 0
        assert result.pagination.total_files == 0
        assert result.pagination.total_pages == 0
    
    @pytest.mark.asyncio
    async def test_list_files_respects_pagination(self, file_service):
        """Should apply correct offset and limit for pagination."""
        mock_query = MagicMock()
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = []
        
        file_service.collection.order_by.return_value = mock_query
        
        mock_count_result = MagicMock()
        mock_count_result.value = 0
        file_service.collection.count.return_value.get.return_value = [[mock_count_result]]
        
        await file_service.list_files(page=3, page_size=10)
        
        # Verify offset calculation: (page - 1) * page_size = (3-1)*10 = 20
        mock_query.offset.assert_called_once_with(20)
        mock_query.limit.assert_called_once_with(10)


class TestGetFile:
    """Tests for get_file method."""
    
    @pytest.mark.asyncio
    async def test_get_existing_file(self, file_service):
        """Should return file metadata for existing file."""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.id = "file123"
        mock_doc.to_dict.return_value = {
            "name": "test.pdf",
            "type": "pdf",
            "summary": "Test summary",
            "keywords": ["test"],
            "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc)
        }
        
        file_service.collection.document.return_value.get.return_value = mock_doc
        
        result = await file_service.get_file("file123")
        
        assert isinstance(result, FileResponse)
        assert result.id == "file123"
        assert result.name == "test.pdf"
        assert result.type == "pdf"
        file_service.collection.document.assert_called_once_with("file123")
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_file(self, file_service):
        """Should raise 404 for nonexistent file."""
        mock_doc = MagicMock()
        mock_doc.exists = False
        
        file_service.collection.document.return_value.get.return_value = mock_doc
        
        with pytest.raises(HTTPException) as exc_info:
            await file_service.get_file("nonexistent")
        
        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()


class TestDeleteFile:
    """Tests for delete_file method."""
    
    @pytest.mark.asyncio
    async def test_delete_existing_file(self, file_service):
        """Should delete file from Firestore and Storage."""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "storage_path": "files/user123/test.pdf"
        }
        
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        file_service.collection.document.return_value = mock_doc_ref
        
        # Mock storage bucket
        mock_blob = MagicMock()
        file_service.storage_bucket.blob.return_value = mock_blob
        
        await file_service.delete_file("file123")
        
        # Verify Firestore deletion
        mock_doc_ref.delete.assert_called_once()
        
        # Verify Storage deletion
        file_service.storage_bucket.blob.assert_called_once_with("files/user123/test.pdf")
        mock_blob.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_file(self, file_service):
        """Should raise 404 for nonexistent file."""
        mock_doc = MagicMock()
        mock_doc.exists = False
        
        file_service.collection.document.return_value.get.return_value = mock_doc
        
        with pytest.raises(HTTPException) as exc_info:
            await file_service.delete_file("nonexistent")
        
        assert exc_info.value.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_handles_storage_failure_gracefully(self, file_service):
        """Should continue even if storage deletion fails."""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"storage_path": "path"}
        
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        file_service.collection.document.return_value = mock_doc_ref
        
        # Mock storage failure
        mock_blob = MagicMock()
        mock_blob.delete.side_effect = Exception("Storage error")
        file_service.storage_bucket.blob.return_value = mock_blob
        
        # Should not raise exception
        await file_service.delete_file("file123")
        
        # Firestore deletion should still happen
        mock_doc_ref.delete.assert_called_once()


class TestGenerateStoragePath:
    """Tests for _generate_storage_path helper."""
    
    def test_generates_unique_path(self, file_service):
        """Should generate unique storage path."""
        path1 = file_service._generate_storage_path("user123", "test.pdf")
        path2 = file_service._generate_storage_path("user123", "test.pdf")
        
        assert path1 != path2
        assert path1.startswith("files/user123/")
        assert path1.endswith("_test.pdf")
    
    def test_sanitizes_filename(self, file_service):
        """Should remove unsafe characters from filename."""
        path = file_service._generate_storage_path("user123", "test file!@#$.pdf")
        
        # Should only keep alphanumeric and ._-
        assert "!" not in path
        assert "@" not in path
        assert "#" not in path


class TestUploadToStorage:
    """Tests for _upload_to_storage helper."""
    
    @pytest.mark.asyncio
    async def test_uploads_file_to_storage(self, file_service):
        """Should upload file and return public URL."""
        content = b"test content"
        upload_file = UploadFile(
            filename="test.pdf",
            file=BytesIO(content),
            headers={"content-type": "application/pdf"}
        )
        
        mock_blob = MagicMock()
        mock_blob.public_url = "https://storage.url/test.pdf"
        file_service.storage_bucket.blob.return_value = mock_blob
        
        result = await file_service._upload_to_storage(upload_file, "path/to/file")
        
        assert result == "https://storage.url/test.pdf"
        file_service.storage_bucket.blob.assert_called_once_with("path/to/file")
        mock_blob.upload_from_string.assert_called_once_with(
            content,
            content_type="application/pdf"
        )
        mock_blob.make_public.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_uses_default_content_type(self, file_service):
        """Should use default content type if not specified."""
        # Create UploadFile without content_type (it defaults to None)
        upload_file = UploadFile(filename="test.pdf", file=BytesIO(b"content"))
        
        mock_blob = MagicMock()
        mock_blob.public_url = "url"
        file_service.storage_bucket.blob.return_value = mock_blob
        
        await file_service._upload_to_storage(upload_file, "path")
        
        # Should use default content type
        call_args = mock_blob.upload_from_string.call_args
        assert call_args[1]["content_type"] == "application/octet-stream"
    
    @pytest.mark.asyncio
    async def test_handles_upload_failure(self, file_service):
        """Should raise HTTPException on upload failure."""
        upload_file = UploadFile(filename="test.pdf", file=BytesIO(b"content"))
        
        mock_blob = MagicMock()
        mock_blob.upload_from_string.side_effect = Exception("Upload failed")
        file_service.storage_bucket.blob.return_value = mock_blob
        
        with pytest.raises(HTTPException) as exc_info:
            await file_service._upload_to_storage(upload_file, "path")
        
        assert exc_info.value.status_code == 500
        assert "Storage upload failed" in str(exc_info.value.detail)


class TestSaveMetadata:
    """Tests for _save_metadata helper."""
    
    @pytest.mark.asyncio
    async def test_saves_metadata_to_firestore(self, file_service):
        """Should save metadata and return document reference."""
        metadata = {
            "name": "test.pdf",
            "type": "pdf",
            "size_bytes": 1000
        }
        
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "new_file_id"
        file_service.collection.document.return_value = mock_doc_ref
        
        result = await file_service._save_metadata(metadata)
        
        assert result == mock_doc_ref
        file_service.collection.document.assert_called_once()
        mock_doc_ref.set.assert_called_once_with(metadata)
