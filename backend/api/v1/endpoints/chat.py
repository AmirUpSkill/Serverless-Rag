import logging
import traceback

from fastapi import APIRouter, Depends, HTTPException, status

from core.config import Settings, get_settings
from schemas.chat import ChatRequest, ChatResponse
from services.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


# --- Get the Chat Service ---
def get_chat_service(settings: Settings = Depends(get_settings)) -> ChatService:
    """
        Dependency to inject ChatService into endpoints . 
    """
    return ChatService(settings)

@router.post(
    "/{file_id}",
    response_model=ChatResponse,
    summary="Chat with AI about a File ",
    description="Send a message to the AI and get a response based on the file's content. "
    "Uses Gemini File Search for retrieval-augmented generation (RAG).",
)
async def chat_with_file(
    file_id: str,
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    """
        Send a message to the AI About a specific file 
    """
    try:
        return await chat_service.chat_with_file(file_id, request.message)
    except HTTPException:
        raise 
    except Exception as e:
        logger.error(f"Chat request failed: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat Request failed :{str(e)}"
        ) from e
