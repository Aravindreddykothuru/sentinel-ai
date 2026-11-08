"""
Conversation Manager for SENTINEL AI Copilot.
Manages chat sessions and context.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import uuid

from copilot.claude_client import CopilotClient

# Global reference set after import to avoid circular dependency
_copilot_client_instance = None


def _get_copilot_client():
    global _copilot_client_instance
    if _copilot_client_instance is None:
        from copilot.claude_client import copilot_client
        _copilot_client_instance = copilot_client
    return _copilot_client_instance


class ConversationSession:
    """Represents a single conversation session."""
    
    def __init__(self, session_id: str, user_id: str, context: Dict = None):
        self.session_id = session_id
        self.user_id = user_id
        self.context = context or {}
        self.messages: List[Dict] = []
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.is_active = True
    
    def add_message(self, role: str, content: str):
        """Add a message to the conversation."""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        self.last_activity = datetime.utcnow()
    
    def get_recent_messages(self, limit: int = 10) -> List[Dict]:
        """Get recent messages for context."""
        return self.messages[-limit:] if self.messages else []
    
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Check if session has expired due to inactivity."""
        expiry = self.last_activity + timedelta(minutes=timeout_minutes)
        return datetime.utcnow() > expiry


class ConversationManager:
    """
    Manages multiple conversation sessions for the Copilot.
    """
    
    def __init__(self, copilot_client_instance: CopilotClient = None):
        self.copilot = copilot_client_instance or _get_copilot_client()
        self.sessions: Dict[str, ConversationSession] = {}
        self.session_timeout = 30  # minutes
    
    def create_session(
        self,
        user_id: str,
        context: Dict = None
    ) -> str:
        """Create a new conversation session."""
        session_id = str(uuid.uuid4())
        
        session = ConversationSession(
            session_id=session_id,
            user_id=user_id,
            context=context
        )
        
        self.sessions[session_id] = session
        return session_id
    
    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Get an existing session."""
        session = self.sessions.get(session_id)
        
        if session and session.is_expired(self.session_timeout):
            # Clean up expired session
            del self.sessions[session_id]
            return None
        
        return session
    
    async def send_message(
        self,
        session_id: str,
        message: str
    ) -> Dict:
        """
        Send a message in a conversation session.
        
        Returns:
            Dict with response and session info
        """
        session = self.get_session(session_id)
        
        if not session:
            return {
                "success": False,
                "error": "Session not found or expired",
                "response": "Your session has expired. Please start a new conversation."
            }
        
        # Add user message
        session.add_message("user", message)
        
        # Get conversation history for context
        history = session.get_recent_messages(limit=10)
        
        # Call Claude
        result = await self.copilot.chat(
            message=message,
            conversation_history=history[:-1],  # Exclude the message we just added
            context=session.context
        )
        
        # Add assistant response
        if result["success"]:
            session.add_message("assistant", result["response"])
        
        return {
            **result,
            "session_id": session_id,
            "message_count": len(session.messages)
        }
    
    async def send_message_stream(
        self,
        session_id: str,
        message: str
    ):
        """
        Stream response for real-time chat.
        Yields response chunks.
        """
        session = self.get_session(session_id)
        
        if not session:
            yield "Session not found or expired. Please start a new conversation."
            return
        
        # Add user message
        session.add_message("user", message)
        
        # Get history
        history = session.get_recent_messages(limit=10)
        
        # Collect full response
        full_response = []
        
        # Stream from Claude
        async for chunk in self.copilot.chat_stream(
            message=message,
            conversation_history=history[:-1],
            context=session.context
        ):
            full_response.append(chunk)
            yield chunk
        
        # Store complete response
        complete_response = "".join(full_response)
        session.add_message("assistant", complete_response)
    
    def end_session(self, session_id: str) -> bool:
        """End a conversation session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get information about a session."""
        session = self.get_session(session_id)
        
        if not session:
            return None
        
        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "message_count": len(session.messages),
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "is_active": session.is_active,
            "context": session.context
        }
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions."""
        expired = [
            sid for sid, session in self.sessions.items()
            if session.is_expired(self.session_timeout)
        ]
        
        for sid in expired:
            del self.sessions[sid]
        
        return len(expired)
    
    def get_active_sessions(self) -> List[Dict]:
        """Get all active sessions."""
        return [
            self.get_session_info(sid)
            for sid in self.sessions
        ]
    
    def get_stats(self) -> Dict:
        """Get conversation statistics."""
        return {
            "total_sessions": len(self.sessions),
            "copilot_configured": self.copilot.is_configured(),
            "session_timeout_minutes": self.session_timeout
        }


# Global conversation manager
conversation_manager = ConversationManager()
