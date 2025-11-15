"""Unit tests for db.session module."""
import threading
from unittest.mock import MagicMock, patch, Mock

# --- Third-party imports ---
import firebase_admin
import pytest
from google.cloud.firestore_v1 import Client as FirestoreClient
from google.cloud.storage import Bucket

# --- Internal imports ---
from db.session import (
    _get_or_init_app,
    get_db,
    get_firestore_client,
    get_storage_bucket,
    make_signed_url,
)


class TestGetOrInitApp:
    """Tests for _get_or_init_app function."""
    
    @patch("db.session.get_settings")
    @patch("db.session.firebase_admin.get_app")
    def test_returns_existing_app(self, mock_get_app, mock_get_settings):
        """Should return existing app if already initialized."""
        mock_app = MagicMock(spec=firebase_admin.App)
        mock_get_app.return_value = mock_app
        
        result = _get_or_init_app()
        
        assert result == mock_app
        mock_get_app.assert_called_once()
    
    @patch("db.session.get_settings")
    @patch("db.session.firebase_admin.get_app")
    @patch("db.session.firebase_admin.initialize_app")
    @patch("db.session.credentials.Certificate")
    def test_initializes_new_app(
        self, mock_cert, mock_init, mock_get_app, mock_get_settings
    ):
        """Should initialize new app if none exists."""
        # --- Simulate no existing app ---
        mock_get_app.side_effect = ValueError("App not found")
        
        # --- Mock settings ---
        mock_settings = MagicMock()
        mock_settings.firebase_service_account = {
            "project_id": "test-project",
            "type": "service_account"
        }
        mock_get_settings.return_value = mock_settings
        
        # --- Mock return values ---
        mock_cred = MagicMock()
        mock_cert.return_value = mock_cred
        mock_app = MagicMock(spec=firebase_admin.App)
        mock_init.return_value = mock_app
        
        result = _get_or_init_app()
        
        assert result == mock_app
        mock_cert.assert_called_once_with(mock_settings.firebase_service_account)
        mock_init.assert_called_once_with(
            mock_cred,
            {
                "projectId": "test-project",
                "storageBucket": "test-project.appspot.com"
            }
        )
    
    @patch("db.session.get_settings")
    @patch("db.session.firebase_admin.get_app")
    @patch("db.session.firebase_admin.initialize_app")
    @patch("db.session.credentials.Certificate")
    def test_handles_initialization_error(
        self, mock_cert, mock_init, mock_get_app, mock_get_settings
    ):
        """Should raise RuntimeError if initialization fails."""
        mock_get_app.side_effect = ValueError("App not found")
        mock_settings = MagicMock()
        mock_settings.firebase_service_account = {"project_id": "test"}
        mock_get_settings.return_value = mock_settings
        
        mock_init.side_effect = Exception("Init failed")
        
        with pytest.raises(RuntimeError, match="Failed to initialize Firebase"):
            _get_or_init_app()
    
    @patch("db.session.get_settings")
    @patch("db.session.firebase_admin.get_app")
    @patch("db.session.firebase_admin.initialize_app")
    def test_thread_safety(self, mock_init, mock_get_app, mock_get_settings):
        """Should be thread-safe (only initialize once)."""
        mock_get_app.side_effect = ValueError("App not found")
        mock_settings = MagicMock()
        mock_settings.firebase_service_account = {"project_id": "test"}
        mock_get_settings.return_value = mock_settings
        
        mock_app = MagicMock(spec=firebase_admin.App)
        mock_init.return_value = mock_app
        
        results = []
        
        def init_app():
            results.append(_get_or_init_app())
        
        threads = [threading.Thread(target=init_app) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # --- All should get the same app instance ---
        assert all(r == mock_app for r in results)


class TestGetFirestoreClient:
    """Tests for get_firestore_client function."""
    
    @patch("db.session._get_or_init_app")
    @patch("db.session.admin_firestore.client")
    def test_returns_firestore_client(self, mock_client, mock_get_app):
        """Should return Firestore client."""
        mock_app = MagicMock(spec=firebase_admin.App)
        mock_get_app.return_value = mock_app
        
        mock_fs_client = MagicMock(spec=FirestoreClient)
        mock_client.return_value = mock_fs_client
        
        result = get_firestore_client()
        
        assert result == mock_fs_client
        mock_client.assert_called_once_with(app=mock_app)


class TestGetStorageBucket:
    """Tests for get_storage_bucket function."""
    
    @patch("db.session._get_or_init_app")
    @patch("db.session.admin_storage.bucket")
    def test_returns_storage_bucket(self, mock_bucket, mock_get_app):
        """Should return storage bucket."""
        mock_app = MagicMock(spec=firebase_admin.App)
        mock_get_app.return_value = mock_app
        
        mock_bucket_obj = MagicMock(spec=Bucket)
        mock_bucket.return_value = mock_bucket_obj
        
        result = get_storage_bucket()
        
        assert result == mock_bucket_obj
        mock_bucket.assert_called_once_with(app=mock_app)


class TestGetDb:
    """Tests for get_db dependency."""
    
    @patch("db.session.get_firestore_client")
    def test_yields_firestore_client(self, mock_get_client):
        """Should yield Firestore client."""
        mock_client = MagicMock(spec=FirestoreClient)
        mock_get_client.return_value = mock_client
        
        gen = get_db()
        result = next(gen)
        
        assert result == mock_client


class TestMakeSignedUrl:
    """Tests for make_signed_url function."""
    
    @patch("db.session.get_storage_bucket")
    def test_generates_signed_url(self, mock_get_bucket):
        """Should generate signed URL for blob."""
        mock_bucket = MagicMock(spec=Bucket)
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_blob.generate_signed_url.return_value = "https://signed-url.com/file.pdf"
        mock_get_bucket.return_value = mock_bucket
        
        result = make_signed_url("files/test.pdf", expires_in_seconds=7200)
        
        assert result == "https://signed-url.com/file.pdf"
        mock_bucket.blob.assert_called_once_with("files/test.pdf")
        mock_blob.generate_signed_url.assert_called_once_with(
            version="v4",
            expiration=7200,
            method="GET"
        )
    
    @patch("db.session.get_storage_bucket")
    def test_uses_default_expiration(self, mock_get_bucket):
        """Should use default 1 hour expiration."""
        mock_bucket = MagicMock(spec=Bucket)
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_blob.generate_signed_url.return_value = "https://signed-url.com/file.pdf"
        mock_get_bucket.return_value = mock_bucket
        
        make_signed_url("files/test.pdf")
        
        mock_blob.generate_signed_url.assert_called_once_with(
            version="v4",
            expiration=3600,  # Default 1 hour
            method="GET"
        )
