"""Base Firestore document model."""
from datetime import datetime
from typing import Any

from google.cloud import firestore as gcf
from pydantic import BaseModel, ConfigDict


class FirestoreDocument(BaseModel):
    """Base model for all Firestore documents.
    
    Provides common fields and methods for Firestore operations.
    Uses server-side timestamps to avoid clock skew issues.
    """
    
    id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    
    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
        validate_assignment=True,
    )
    
    def to_dict(self, exclude_id: bool = True) -> dict[str, Any]:
        """Convert model to Firestore-ready dict.
        
        Args:
            exclude_id: Whether to exclude the id field (default: True)
            
        Returns:
            Dictionary ready for Firestore write operations.
        """
        exclude_set = {"id"} if exclude_id else set()
        return self.model_dump(
            exclude_none=True,
            exclude=exclude_set,
            mode="json"
        )
    
    @classmethod
    def from_doc(cls, doc) -> "FirestoreDocument":
        """Create model instance from Firestore DocumentSnapshot.
        
        Args:
            doc: Firestore DocumentSnapshot object
            
        Returns:
            Instance of the model with data from Firestore
        """
        data = doc.to_dict() or {}
        data["id"] = doc.id
        return cls(**data)
    
    @staticmethod
    def server_timestamp() -> Any:
        """Get Firestore SERVER_TIMESTAMP sentinel.
        
        Use this when setting created_at or updated_at fields:
            data["created_at"] = FirestoreDocument.server_timestamp()
            
        Returns:
            Firestore SERVER_TIMESTAMP sentinel value
        """
        return gcf.SERVER_TIMESTAMP
