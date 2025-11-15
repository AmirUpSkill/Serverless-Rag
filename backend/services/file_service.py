import uuid
from typing import List

from fastapi import HTTPException, UploadFile
from google.cloud import firestore

from schemas.file import FileResponse, FileListResponse, Pagination
from services.service_base import ServiceBase

# --- Firestore collection reference ---
FILES_COLLECTION = "files"


class FileService(ServiceBase):
    """
        Handles all file-related operations: upload, list, get, delete.
    """

    def __init__(self, settings):
        super().__init__(settings)
        self.collection = self.firestore_client.collection(FILES_COLLECTION)

    async def upload_file(self, file: UploadFile, user_id: str) -> FileResponse:
        """
            Complete file upload pipeline.
        """
        # --- Validation ---
        file_type, file_size = await self.validate_file(file)

        # --- Generate path and upload to storage ---
        storage_path = self._generate_storage_path(user_id, file.filename)
        public_url = await self._upload_to_storage(file, storage_path)

        now = self.get_current_timestamp()
        # --- Save metadata to Firestore ---
        metadata = {
            "name": file.filename,
            "type": file_type,
            "size_bytes": file_size,
            "storage_path": storage_path,
            "public_url": public_url,
            "created_at": now,
            "updated_at": now,
        }
        doc_ref = await self._save_metadata(metadata)

        return FileResponse(
            id=doc_ref.id,
            name=file.filename,
            type=file_type,
            size_bytes=file_size,
            summary=None,
            keywords=[],
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
        """
            Delete file from Firestore and Storage.
        """
        doc_ref = self.collection.document(file_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="File not found")

        data = doc.to_dict() or {}

        # --- Delete from Firestore ---
        doc_ref.delete()
        # --- Delete it from the Bucket ---
        storage_path = data.get("storage_path")
        if not storage_path:
            return
        try:
            blob = self.storage_bucket.blob(storage_path)
            blob.delete()
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
        """
            Upload file to Firebase Storage and return its public URL.
        """
        try:
            blob = self.storage_bucket.blob(storage_path)
            content = await file.read()

            content_type = file.content_type or "application/octet-stream"
            blob.upload_from_string(content, content_type=content_type)
            blob.make_public()

            return blob.public_url
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Storage upload failed: {e}"
            ) from e

    async def _save_metadata(self, metadata: dict) -> firestore.DocumentReference:
        """
            Save metadata to Firestore and return the new document reference.
        """
        doc_ref = self.collection.document()
        doc_ref.set(metadata)
        return doc_ref
