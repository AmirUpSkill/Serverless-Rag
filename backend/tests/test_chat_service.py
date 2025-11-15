"""Unit tests for services.chat_service module."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from services.chat_service import ChatService, FILES_COLLECTION
from schemas.chat import ChatResponse


@pytest.fixture
def mock_settings():
    """Create mock settings object."""
    settings = MagicMock()
    settings.gemini_api_key.get_secret_value.return_value = "test-api-key"
    settings.gemini_model = "gemini-2.5-pro"
    return settings


@pytest.fixture
def chat_service(mock_settings):
    """Create ChatService instance with mocked dependencies."""
    with patch("services.service_base.genai.Client") as mock_gemini, \
         patch("services.service_base.get_firestore_client") as mock_get_fs, \
         patch("services.service_base.get_storage_bucket"):

        mock_fs_client = MagicMock()
        mock_get_fs.return_value = mock_fs_client

        service = ChatService(mock_settings)
        service.collection = MagicMock()  # Mock the collection
        service.gemini_client = mock_gemini.return_value

        return service


class TestChatServiceInitialization:
    """Tests for ChatService initialization."""
    
    def test_initializes_with_files_collection(self, chat_service):
        """Should initialize with 'files' collection reference."""
        assert chat_service.collection is not None


class TestChatWithFile:
    """Tests for chat_with_file method."""
    
    @pytest.mark.asyncio
    async def test_successful_chat_interaction(self, chat_service):
        """Should successfully chat about a file using Gemini."""
        # Mock Firestore document
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "name": "test.pdf",
            "gemini_file_search_store_name": "fileSearchStores/store123",
        }
        chat_service.collection.document.return_value.get.return_value = mock_doc
        
        # Mock Gemini response
        mock_response = MagicMock()
        mock_response.text = "This document discusses AI advancements in 2024."
        chat_service.gemini_client.models.generate_content.return_value = mock_response
        
        # Execute
        result = await chat_service.chat_with_file(
            file_id="file123",
            message="What is this document about?"
        )
        
        # Assert
        assert isinstance(result, ChatResponse)
        assert result.response == "This document discusses AI advancements in 2024."
        
        # Verify Firestore call
        chat_service.collection.document.assert_called_once_with("file123")
        
        # Verify Gemini call
        chat_service.gemini_client.models.generate_content.assert_called_once()
        call_args = chat_service.gemini_client.models.generate_content.call_args
        assert call_args[1]["model"] == "gemini-2.5-pro"
        assert call_args[1]["contents"] == "What is this document about?"
    
    @pytest.mark.asyncio
    async def test_chat_with_nonexistent_file(self, chat_service):
        """Should raise 404 if file doesn't exist."""
        mock_doc = MagicMock()
        mock_doc.exists = False
        chat_service.collection.document.return_value.get.return_value = mock_doc
        
        with pytest.raises(HTTPException) as exc_info:
            await chat_service.chat_with_file("nonexistent", "test message")
        
        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()
    
    @pytest.mark.asyncio
    async def test_chat_handles_empty_ai_response(self, chat_service):
        """Should raise 500 if AI returns empty response."""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "gemini_file_search_store_name": "fileSearchStores/store123",
        }
        chat_service.collection.document.return_value.get.return_value = mock_doc
        
        # Mock empty response
        mock_response = MagicMock()
        mock_response.text = None
        chat_service.gemini_client.models.generate_content.return_value = mock_response
        
        with pytest.raises(HTTPException) as exc_info:
            await chat_service.chat_with_file("file123", "test message")
        
        assert exc_info.value.status_code == 500
        assert "no response" in str(exc_info.value.detail).lower()
    
    @pytest.mark.asyncio
    async def test_chat_handles_gemini_api_error(self, chat_service):
        """Should handle Gemini API errors gracefully."""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "gemini_file_search_store_name": "fileSearchStores/store123",
        }
        chat_service.collection.document.return_value.get.return_value = mock_doc
        
        # Mock API error
        chat_service.gemini_client.models.generate_content.side_effect = \
            Exception("API rate limit exceeded")
        
        with pytest.raises(HTTPException) as exc_info:
            await chat_service.chat_with_file("file123", "test message")
        
        assert exc_info.value.status_code == 500
        assert "Chat failed" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_chat_passes_correct_file_search_config(self, chat_service):
        """Should pass correct file search configuration to Gemini."""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "gemini_file_search_store_name": "fileSearchStores/my-store-456",
        }
        chat_service.collection.document.return_value.get.return_value = mock_doc
        
        mock_response = MagicMock()
        mock_response.text = "AI response"
        chat_service.gemini_client.models.generate_content.return_value = mock_response
        
        await chat_service.chat_with_file("file123", "test message")
        
        # Verify the config contains the correct file search store
        call_args = chat_service.gemini_client.models.generate_content.call_args
        config = call_args[1]["config"]

        assert "tools" in config
        assert len(config["tools"]) > 0
        assert "file_search" in config["tools"][0]
        assert config["tools"][0]["file_search"]["file_search_store_names"] == [
            "fileSearchStores/my-store-456"
        ]
    
    @pytest.mark.asyncio
    async def test_chat_with_various_message_types(self, chat_service):
        """Should handle different message types."""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "gemini_file_search_store_name": "fileSearchStores/store123",
        }
        chat_service.collection.document.return_value.get.return_value = mock_doc
        
        mock_response = MagicMock()
        mock_response.text = "Response"
        chat_service.gemini_client.models.generate_content.return_value = mock_response
        
        # Test various message types
        messages = [
            "Simple question?",
            "What are the main findings in this research paper?",
            "Can you summarize chapter 3?",
            "Extract all dates mentioned in the document."
        ]
        
        for message in messages:
            result = await chat_service.chat_with_file("file123", message)
            assert isinstance(result, ChatResponse)
            assert result.response == "Response"


class TestChatServiceIntegration:
    """Integration-style tests for ChatService."""
    
    @pytest.mark.asyncio
    async def test_complete_chat_flow(self, chat_service):
        """Should complete full chat flow from file lookup to response."""
        # Setup complete mock chain
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "name": "research_paper.pdf",
            "type": "pdf",
            "gemini_file_search_store_name": "fileSearchStores/research-store",
        }
        chat_service.collection.document.return_value.get.return_value = mock_doc
        
        mock_response = MagicMock()
        mock_response.text = "The paper presents novel findings on AI interpretability."
        chat_service.gemini_client.models.generate_content.return_value = mock_response
        
        # Execute complete flow
        result = await chat_service.chat_with_file(
            file_id="research_file_id",
            message="What are the main contributions?"
        )
        
        # Verify result
        assert result.response == "The paper presents novel findings on AI interpretability."
        
        # Verify full call chain
        chat_service.collection.document.assert_called_once_with("research_file_id")
        chat_service.gemini_client.models.generate_content.assert_called_once()


class TestErrorHandling:
    """Tests for error handling in ChatService."""
    
    @pytest.mark.asyncio
    async def test_handles_firestore_connection_error(self, chat_service):
        """Should handle Firestore connection errors."""
        chat_service.collection.document.side_effect = Exception("Connection timeout")
        
        with pytest.raises(Exception):
            await chat_service.chat_with_file("file123", "message")
    
    @pytest.mark.asyncio
    async def test_handles_malformed_document_data(self, chat_service):
        """Should handle documents missing required fields."""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "name": "test.pdf"
            # Missing gemini_file_search_store_name
        }
        chat_service.collection.document.return_value.get.return_value = mock_doc

        with pytest.raises(HTTPException) as exc_info:
            await chat_service.chat_with_file("file123", "message")

        assert exc_info.value.status_code == 500
        assert "not yet linked" in str(exc_info.value.detail)
