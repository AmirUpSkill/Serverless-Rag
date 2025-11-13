"""Unit tests for db.base module."""
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from google.cloud import firestore as gcf

from db.base import FirestoreDocument


class TestFirestoreDocument:
    """Tests for FirestoreDocument base model."""
    
    def test_instantiation(self):
        """Should create instance with basic fields."""
        doc = FirestoreDocument(
            id="test123",
            created_at=datetime(2024, 1, 1, 10, 0, 0),
            updated_at=datetime(2024, 1, 1, 10, 0, 0)
        )
        
        assert doc.id == "test123"
        assert doc.created_at == datetime(2024, 1, 1, 10, 0, 0)
        assert doc.updated_at == datetime(2024, 1, 1, 10, 0, 0)
    
    def test_optional_fields(self):
        """Should allow None for optional fields."""
        doc = FirestoreDocument()
        
        assert doc.id is None
        assert doc.created_at is None
        assert doc.updated_at is None
    
    def test_to_dict_excludes_id_by_default(self):
        """Should exclude id field by default."""
        doc = FirestoreDocument(
            id="test123",
            created_at=datetime(2024, 1, 1, 10, 0, 0),
            updated_at=datetime(2024, 1, 1, 10, 0, 0)
        )
        
        result = doc.to_dict()
        
        assert "id" not in result
        assert "created_at" in result
        assert "updated_at" in result
    
    def test_to_dict_includes_id_when_specified(self):
        """Should include id when exclude_id=False."""
        doc = FirestoreDocument(
            id="test123",
            created_at=datetime(2024, 1, 1, 10, 0, 0)
        )
        
        result = doc.to_dict(exclude_id=False)
        
        assert result["id"] == "test123"
    
    def test_to_dict_excludes_none_values(self):
        """Should exclude None values from dict."""
        doc = FirestoreDocument(id="test123")
        
        result = doc.to_dict()
        
        assert "created_at" not in result
        assert "updated_at" not in result
    
    def test_from_doc_creates_instance(self):
        """Should create instance from Firestore DocumentSnapshot."""
        mock_doc = MagicMock()
        mock_doc.id = "doc123"
        mock_doc.to_dict.return_value = {
            "created_at": datetime(2024, 1, 1, 10, 0, 0),
            "updated_at": datetime(2024, 1, 1, 10, 0, 0),
        }
        
        result = FirestoreDocument.from_doc(mock_doc)
        
        assert result.id == "doc123"
        assert result.created_at == datetime(2024, 1, 1, 10, 0, 0)
        assert result.updated_at == datetime(2024, 1, 1, 10, 0, 0)
    
    def test_from_doc_handles_empty_dict(self):
        """Should handle DocumentSnapshot with no data."""
        mock_doc = MagicMock()
        mock_doc.id = "doc123"
        mock_doc.to_dict.return_value = None
        
        result = FirestoreDocument.from_doc(mock_doc)
        
        assert result.id == "doc123"
        assert result.created_at is None
        assert result.updated_at is None
    
    def test_server_timestamp_returns_sentinel(self):
        """Should return Firestore SERVER_TIMESTAMP sentinel."""
        result = FirestoreDocument.server_timestamp()
        
        assert result == gcf.SERVER_TIMESTAMP
    
    def test_extra_fields_ignored(self):
        """Should ignore extra fields due to model_config."""
        doc = FirestoreDocument(
            id="test123",
            extra_field="should_be_ignored"  # type: ignore
        )
        
        assert doc.id == "test123"
        assert not hasattr(doc, "extra_field")


class ConcreteDocument(FirestoreDocument):
    """Concrete subclass for testing inheritance."""
    name: str
    value: int = 0


class TestFirestoreDocumentSubclass:
    """Tests for subclassing FirestoreDocument."""
    
    def test_subclass_inherits_base_fields(self):
        """Should inherit id, created_at, updated_at fields."""
        doc = ConcreteDocument(
            id="test123",
            name="Test Document",
            value=42,
            created_at=datetime(2024, 1, 1, 10, 0, 0)
        )
        
        assert doc.id == "test123"
        assert doc.name == "Test Document"
        assert doc.value == 42
        assert doc.created_at == datetime(2024, 1, 1, 10, 0, 0)
    
    def test_subclass_to_dict(self):
        """Should include subclass fields in to_dict."""
        doc = ConcreteDocument(
            id="test123",
            name="Test Document",
            value=42
        )
        
        result = doc.to_dict()
        
        assert "id" not in result
        assert result["name"] == "Test Document"
        assert result["value"] == 42
    
    def test_subclass_from_doc(self):
        """Should create subclass instance from DocumentSnapshot."""
        mock_doc = MagicMock()
        mock_doc.id = "doc123"
        mock_doc.to_dict.return_value = {
            "name": "Test Document",
            "value": 42,
            "created_at": datetime(2024, 1, 1, 10, 0, 0),
        }
        
        result = ConcreteDocument.from_doc(mock_doc)
        
        assert isinstance(result, ConcreteDocument)
        assert result.id == "doc123"
        assert result.name == "Test Document"
        assert result.value == 42
    
    def test_subclass_validation(self):
        """Should validate required fields in subclass."""
        with pytest.raises(ValueError):
            ConcreteDocument(id="test123")  # Missing required 'name' field
