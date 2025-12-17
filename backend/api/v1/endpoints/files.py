import logging
import traceback

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from core.config import Settings, get_settings
from schemas.file import FileListResponse, FileResponse
from services.file_service import FileService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["files"])

# --- Get the File Service Instance --- 
def get_file_service(settings: Settings = Depends(get_settings)) -> FileService:
    """
        Depedency to Inject FileService into endpoints .
    """
    return FileService(settings)

# ---- 1. Upload File Endpoint --- 
@router.post(
    "",
    response_model=FileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new file",
    description="Upload a file to Firebase Storage and create metadata in Firestore. "
    "Supports PDF, DOCX, TXT, MD, CSV, XLSX, and other document formats. "
    "Maximum file size: 100 MB.",
)
async def upload_file(
    file: UploadFile = File(..., description="The File To Upload"),
    file_service: FileService = Depends(get_file_service),
) -> FileResponse:
    """ 
        Upload a new file and create its metdata . 
    """
    # --- Later we gonna add Auth --- 
    user_id = "anonymous"
    try:
        return await file_service.upload_file(file , user_id)
    except HTTPException:
        raise 
    except Exception as e:
        logger.error(f"File upload failed: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File Upload failed : {str(e)}"
        ) from e
@router.get(
    "",
    response_model=FileListResponse,
    summary="Get Paginated list of files",
    description="Retrieve a paginated list of all uploaded files. "
    "Default pagination: 12 files per page (3×4 grid).",
)
async def list_files(
    page: int = Query(1, ge=1 , description="Page Number (1-indexed)"),
    page_size: int = Query(12 , ge=1 , le=100 , description="Number of files per page"),
    file_service: FileService = Depends(get_file_service),
) -> FileListResponse:
    """
        Get A Paginated List of Files . 
        - page : Page Number (default : 1)
        - page_size : Items per page (default : 12 , max: 100)
    Returns List of Files with pagination metadata 
    """
    try:
        return await file_service.list_files(page , page_size)
    except HTTPException:
        raise 
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrive files: {str(e)}"
        ) from e 
@router.get(
    "/{file_id}",
    response_model=FileResponse,
    summary="Get a specific file",
    description="Retrieve metadata for a single file by its ID.",
)
async def get_file(
    file_id: str,
    file_service: FileService = Depends(get_file_service),
) -> FileResponse:
    """
    Get metadata for a specific file.

    - **file_id**: The unique identifier of the file

    Returns the file metadata if found.
    """
    return await file_service.get_file(file_id)


@router.delete(
    "/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a file",
    description="Delete a file from both Firestore and Firebase Storage.",
)
async def delete_file(
    file_id: str,
    file_service: FileService = Depends(get_file_service),
) -> None:
    """
    Delete a file and its metadata.

    - **file_id**: The unique identifier of the file to delete

    Returns 204 No Content on success.
    """
    await file_service.delete_file(file_id)