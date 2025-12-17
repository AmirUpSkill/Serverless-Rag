import os
import tempfile
import uuid
from io import BytesIO
from typing import List

from fastapi import HTTPException, UploadFile
from google.cloud import firestore
from minio import Minio

from core.config import Settings
from schemas.file import FileResponse, FileListResponse, Pagination
from services.gemini_service import GeminiService
from services.service_base import ServiceBase

# --- Firestore collection reference ---
FILES_COLLECTION = "files"


class FileService(ServiceBase):
    """
        Handles all file-related operations: upload, list, get, delete.
    """

    def __init__(self, settings: Settings):
        super().__init__(settings)
        self.collection = self.firestore_client.collection(FILES_COLLECTION)
        
        # --- Initialize Gemini File Search service ---
        self.gemini_service = GeminiService(settings)

        # --- Initialise MinIO client for object storage ---
        self._init_storage()

    async def upload_file(self, file: UploadFile, user_id: str) -> FileResponse:
        """
            Complete file upload pipeline with Gemini File Search integration.
        """
        # --- Validation ---
        file_type, file_size = await self.validate_file(file)

        # --- Generate path and upload to MinIO storage ---
        storage_path = self._generate_storage_path(user_id, file.filename)
        public_url = await self._upload_to_storage(file, storage_path)
        
        # --- Reset file position for re-reading ---
        await file.seek(0)
        
        # --- Save file temporarily for Gemini upload ---
        temp_file_path = None
        try:
            # Create temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type}") as temp_file:
                content = await file.read()
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            # --- Upload to Gemini File Search ---
            store_name, document_name = await self.gemini_service.upload_and_index_file(
                file_path=temp_file_path,
                display_name=file.filename or "unknown"
            )
            
            # --- Generate AI summary and keywords ---
            try:
                # Try to extract text for summary generation
                text_content = content.decode('utf-8', errors='ignore')[:5000]
                summary, keywords = await self.gemini_service.generate_summary_and_keywords(
                    file_content=text_content,
                    filename=file.filename or "unknown"
                )
            except Exception as e:
                print(f"Summary generation failed: {e}")
                summary = None
                keywords = []
            
        finally:
            # Clean up temp file
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

        now = self.get_current_timestamp()
        
        # --- Save metadata to Firestore with Gemini info ---
        metadata = {
            "name": file.filename,
            "type": file_type,
            "size_bytes": file_size,
            "storage_path": storage_path,
            "public_url": public_url,
            "gemini_file_search_store_name": store_name,
            "gemini_document_name": document_name,
            "summary": summary,
            "keywords": keywords,
            "created_at": now,
            "updated_at": now,
        }
        doc_ref = await self._save_metadata(metadata)

        return FileResponse(
            id=doc_ref.id,
            name=file.filename,
            type=file_type,
            size_bytes=file_size,
            summary=summary,
            keywords=keywords,
            created_at=metadata["created_at"],
            updated_at=metadata["updated_at"],
        )

    async def list_files(self, page: int = 1, page_size: int = 12) -> FileListResponse:
        """
            Retrieve paginated file list.
        """
        offset = (page - 1) * page_size

        query = self.collection.order_by(
            "created_at", direction=firestore.Query.DESCENDING
        )
        docs = query.offset(offset).limit(page_size).stream()

        files: List[FileResponse] = []
        for doc in docs:
            data = doc.to_dict() or {}
            if not data:
                continue
            files.append(
                FileResponse(
                    id=doc.id,
                    name=data["name"],
                    type=data["type"],
                    size_bytes=data.get("size_bytes", 0),
                    summary=data.get("summary"),
                    keywords=data.get("keywords", []),
                    created_at=data["created_at"],
                    updated_at=data.get("updated_at", data["created_at"]),
                )
            )

        # --- Get total count ---
        total_files = self.collection.count().get()[0][0].value
        total_pages = (total_files + page_size - 1) // page_size

        return FileListResponse(
            files=files,
            pagination=Pagination(
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                total_files=total_files,
            ),
        )

    async def get_file(self, file_id: str) -> FileResponse:
        """
            Get single file metadata.
        """
        doc = self.collection.document(file_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="File not found")

        data = doc.to_dict() or {}
        return FileResponse(
            id=doc.id,
            name=data["name"],
            type=data["type"],
            size_bytes=data.get("size_bytes", 0),
            summary=data.get("summary"),
            keywords=data.get("keywords", []),
            created_at=data["created_at"],
            updated_at=data.get("updated_at", data["created_at"]),
        )

    async def delete_file(self, file_id: str) -> None:
        """Delete file from Firestore and object storage."""
        doc_ref = self.collection.document(file_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="File not found")

        data = doc.to_dict() or {}

        # --- Delete from Firestore ---
        doc_ref.delete()

        # --- Delete from MinIO bucket (best-effort) ---
        storage_path = data.get("storage_path")
        if not storage_path:
            return
        try:
            self.storage_client.remove_object(self.bucket_name, storage_path)
        except Exception as e:
            # Log and continue; Firestore deletion has already succeeded
            print(f"Warning: Storage deletion failed: {e}")

    # --- Private helpers ---
    def _generate_storage_path(self, user_id: str, filename: str) -> str:
        """
            Generate unique Firebase Storage path.
        """
        timestamp = self.get_current_timestamp().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        return f"files/{user_id}/{timestamp}_{unique_id}_{safe_filename}"

    async def _upload_to_storage(self, file: UploadFile, storage_path: str) -> str:
        """Upload file to MinIO and return its public URL."""
        try:
            content = await file.read()
            data_stream = BytesIO(content)

            content_type = file.content_type or "application/octet-stream"
            self.storage_client.put_object(
                bucket_name=self.bucket_name,
                object_name=storage_path,
                data=data_stream,
                length=len(content),
                content_type=content_type,
            )

            # Construct a simple HTTP URL; suitable for local/dev usage.
            public_base = self.public_base_url or f"http://{self.settings.minio_endpoint}"
            return f"{public_base}/{self.bucket_name}/{storage_path}"
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Storage upload failed: {e}"
            ) from e

    def _init_storage(self) -> None:
        """Initialise MinIO client and ensure bucket exists."""
        self.storage_client = Minio(
            endpoint=self.settings.minio_endpoint,
            access_key=self.settings.minio_access_key,
            secret_key=self.settings.minio_secret_key.get_secret_value(),
            secure=self.settings.minio_use_ssl,
        )

        self.bucket_name = self.settings.minio_bucket
        self.public_base_url = self.settings.minio_public_url

        # Ensure bucket exists (idempotent)
        found = self.storage_client.bucket_exists(self.bucket_name)
        if not found:
            self.storage_client.make_bucket(self.bucket_name)

    async def _save_metadata(self, metadata: dict) -> firestore.DocumentReference:
        """
            Save metadata to Firestore and return the new document reference.
        """
        doc_ref = self.collection.document()
        doc_ref.set(metadata)
        return doc_ref
