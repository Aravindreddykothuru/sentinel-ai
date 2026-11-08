"""
Copilot API Routes for SENTINEL AI.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from copilot import conversation_manager

router = APIRouter(prefix="/copilot", tags=["copilot"])


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: str = "anonymous"
    context: dict = {}


class ChatResponse(BaseModel):
    response: str
    session_id: str
    success: bool
    error: Optional[str] = None


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message to the Copilot."""
    try:
        # Create session if not provided
        session_id = request.session_id
        if not session_id:
            session_id = conversation_manager.create_session(
                user_id=request.user_id,
                context=request.context
            )
        
        # Send message
        result = await conversation_manager.send_message(
            session_id=session_id,
            message=request.message
        )
        
        return ChatResponse(
            response=result.get("response", ""),
            session_id=session_id,
            success=result.get("success", False),
            error=result.get("error")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}")
def get_session_info(session_id: str):
    """Get information about a chat session."""
    info = conversation_manager.get_session_info(session_id)
    if not info:
        raise HTTPException(status_code=404, detail="Session not found")
    return info


@router.delete("/session/{session_id}")
def end_session(session_id: str):
    """End a chat session."""
    success = conversation_manager.end_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "message": "Session ended"}


@router.get("/stats")
def get_copilot_stats():
    """Get Copilot statistics."""
    return conversation_manager.get_stats()
