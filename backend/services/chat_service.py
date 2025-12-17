from fastapi import HTTPException
from schemas.chat import ChatResponse
from services.gemini_service import GeminiService
from services.service_base import ServiceBase

FILES_COLLECTION = "files"


class ChatService(ServiceBase):
    """
        Main logic for AI chat operations using Gemini File Search.
    """

    def __init__(self, settings):
        super().__init__(settings)
        self.collection = self.firestore_client.collection(FILES_COLLECTION)
        self.gemini_service = GeminiService(settings)

    async def chat_with_file(self, file_id: str, message: str) -> ChatResponse:
        """
            Chat with AI about a specific file.
        """
        # --- Get the file metadata ---
        doc = self.collection.document(file_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="File not found")

        data = doc.to_dict() or {}
        store_name = data.get("gemini_file_search_store_name")
        if not store_name:
            raise HTTPException(
                status_code=500,
                detail="File is not yet linked to a Gemini File Search store",
            )

        # --- Call Gemini with File Search configured ---
        try:
            response_text = await self.gemini_service.chat_with_store(
                store_name=store_name,
                message=message
            )
            
            if not response_text:
                raise HTTPException(
                    status_code=500, detail="AI generated no response"
                )
            
            return ChatResponse(response=response_text)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Chat failed: {e}") from e
