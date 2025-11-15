from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    """
        Schema for the request body when sending a message to the chat.
    """
    message: str = Field(..., min_length=1, description="The user's message.")

class ChatResponse(BaseModel):
    """
        Schema for the response body from the chat AI.
    """
    response: str = Field(..., description="The AI's response to the user's message.")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "response": "This is the AI's response to your question about the document."
            }
        }
    }
