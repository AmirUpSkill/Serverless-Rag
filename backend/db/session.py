import threading
from typing import Generator

import firebase_admin
from firebase_admin import credentials, firestore as admin_firestore, storage as admin_storage
from google.cloud.firestore_v1 import Client as FirestoreClient
from google.cloud.storage import Bucket

from core.config import get_settings

# --- Thread-safe initialization lock ---
_init_lock = threading.Lock()


def _get_or_init_app() -> firebase_admin.App:
    """
        Get existing Firebase app or initialize a new one (idempotent).
    """
    settings = get_settings()
    
    with _init_lock:
        try:
            # --- Try to get the existing default app ---
            return firebase_admin.get_app()
        except ValueError:
            # --- App doesn't exist, initialize it ---
            try:
                service_account = settings.firebase_service_account
                cred = credentials.Certificate(service_account)
                
                return firebase_admin.initialize_app(cred, {
                    "projectId": service_account["project_id"],
                    "storageBucket": f"{service_account['project_id']}.appspot.com",
                })
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Firebase: {e}") from e


def get_firestore_client() -> FirestoreClient:
    """
        Get Firestore client instance.
    
    Returns:
        FirestoreClient: Initialized Firestore client.
        
    Raises:
        RuntimeError: If Firebase initialization fails.
    """
    app = _get_or_init_app()
    return admin_firestore.client(app=app)


def get_storage_bucket() -> Bucket:
    """
        Get Firebase Storage bucket instance.
    
    Returns:
        Bucket: Default storage bucket.
        
    Raises:
        RuntimeError: If Firebase initialization fails.
    """
    app = _get_or_init_app()
    return admin_storage.bucket(app=app)


def get_db() -> Generator[FirestoreClient, None, None]:
    """
        FastAPI dependency to inject Firestore client into endpoints.
    
    Yields:
        FirestoreClient: Firestore client instance.
    """
    yield get_firestore_client()


def make_signed_url(blob_path: str, expires_in_seconds: int = 3600) -> str:
    """
        Generate a signed URL for a storage blob.
    
    Args:
        blob_path: Path to the blob in storage (e.g., 'files/user123/doc.pdf')
        expires_in_seconds: URL expiration time in seconds (default: 1 hour)
        
    Returns:
        str: Signed URL for accessing the blob
        
    Raises:
        RuntimeError: If Firebase initialization fails
    """
    bucket = get_storage_bucket()
    blob = bucket.blob(blob_path)
    return blob.generate_signed_url(
        version="v4",
        expiration=expires_in_seconds,
        method="GET"
    )
