"""
Gemini API Client for SENTINEL AI Copilot.
Handles conversational interface with maintenance staff.
"""

import os
import re
from typing import Dict, List, Optional, AsyncGenerator
from datetime import datetime

import google.generativeai as genai

from config import get_settings
from ai.gemini_client import is_quota_error, model_candidates, resolve_model_name

settings = get_settings()


class CopilotClient:
    """
    Gemini API client for the SENTINEL AI Copilot.
    Provides conversational AI for maintenance queries.
    """
    
    def __init__(self):
        keys = settings.GOOGLE_API_KEY or os.getenv("GOOGLE_API_KEY", "")
        self.api_key = keys.split(",")[0].strip()
        self.model_name = settings.GEMINI_MODEL
        self.model = None

        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model_name = resolve_model_name(self.model_name)
            self.model = genai.GenerativeModel(self.model_name)
    
    def is_configured(self) -> bool:
        """Check if Gemini API is configured."""
        return self.model is not None
    
    def _create_system_prompt(self, context: Dict) -> str:
        """Create system prompt with context."""
        machine = f"\nSelected Machine:\n{context['machine']}\n" if context.get('machine') else ""
        return f"""You are SENTINEL AI Copilot, an expert industrial maintenance assistant.

Your role:
- Help maintenance staff understand machine diagnostics
- Explain sensor readings and failure predictions
- Suggest maintenance procedures and troubleshooting steps
- Answer questions about machine health and maintenance schedules
- Provide clear, actionable advice in simple language

Current Context:
- User Role: {context.get('user_role', 'Maintenance Staff')}
- Active Alerts: {context.get('active_alerts', 0)}
- Machines Monitored: {context.get('machine_count', 0)}
{machine}

Guidelines:
1. Be concise but thorough
2. Use technical terms but explain them
3. Prioritize safety in all recommendations
4. Reference specific sensor data when available
5. Suggest next steps clearly
6. If unsure, recommend consulting a senior technician
7. Keep it under 150 words and do not use emoji

Current time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
    
    async def chat(
        self,
        message: str,
        conversation_history: List[Dict] = None,
        context: Dict = None
    ) -> Dict:
        """
        Send a message to Gemini and get response.
        
        Args:
            message: User's message
            conversation_history: Previous messages [{role, content}]
            context: Additional context (user_role, active_alerts, etc.)
        
        Returns:
            Dict with response text and metadata
        """
        if not self.is_configured():
            return self._mock_response(message, context)
        
        try:
            import asyncio
            
            # Run synchronous Gemini calls in thread pool
            loop = asyncio.get_event_loop()
            
            def _chat_sync(model):
                # Build conversation history for Gemini
                history = []
                
                # Add conversation history if available
                if conversation_history:
                    for msg in conversation_history:
                        role = "user" if msg["role"] == "user" else "model"
                        history.append({"role": role, "parts": [msg["content"]]})
                
                # Start chat with history
                chat = model.start_chat(history=history)
                
                # Send current message with system context prepended
                system_prompt = self._create_system_prompt(context or {})
                full_message = f"{system_prompt}\n\nUser: {message}\n\nAssistant:"
                
                response = chat.send_message(full_message)
                return response.text
            
            # Each model has its own free-tier quota; on 429 move on to the next available model
            for model_name in model_candidates(self.model_name):
                model = self.model if model_name == self.model_name else genai.GenerativeModel(model_name)
                try:
                    response_text = await loop.run_in_executor(None, _chat_sync, model)
                    break
                except Exception as e:
                    if not is_quota_error(e):
                        raise
                    print(f"[Copilot] Quota exceeded for {model_name}, trying next model")
                    quota_error = e
            else:
                raise quota_error

            return {
                "success": True,
                "response": response_text,
                "model": model_name,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            import traceback
            print(f"Gemini API Error: {e}")
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "response": self._get_fallback_response(message)
            }
    
    async def chat_stream(
        self,
        message: str,
        conversation_history: List[Dict] = None,
        context: Dict = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream response from Gemini (for real-time typing effect).
        """
        if not self.is_configured():
            # Return mock response as single chunk
            response = self._mock_response(message, context)
            yield response["response"]
            return
        
        try:
            # Build conversation
            chat = self.model.start_chat(history=[])
            
            # Add system context
            system_prompt = self._create_system_prompt(context or {})
            chat.send_message(system_prompt)
            
            # Add conversation history
            if conversation_history:
                for msg in conversation_history:
                    if msg["role"] == "user":
                        chat.send_message(msg["content"])
            
            # Stream response
            response = chat.send_message(message, stream=True)
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            yield f"Error: {str(e)}. Using fallback response.\n\n"
            yield self._get_fallback_response(message)
    
    def _mock_response(self, message: str, context: Dict) -> Dict:
        """Generate mock response when API not available."""
        response = self._get_fallback_response(message)
        
        return {
            "success": True,
            "response": response + "\n\n[MOCK MODE - Gemini API not configured]",
            "model": "mock",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _get_fallback_response(self, message: str) -> str:
        """Generate rule-based fallback response."""
        message_lower = message.lower()
        
        # Greeting
        if re.search(r"\b(hello|hi|hey)\b", message_lower):
            return """Hello! I'm SENTINEL AI Copilot. I can help you with:

• Understanding machine diagnostics and alerts
• Explaining sensor readings
• Maintenance procedures and troubleshooting
• Interpreting AI predictions

What would you like to know?"""
        
        # Bearing issues
        if "bearing" in message_lower:
            return """Bearing issues are common causes of machine failure. Here's what to check:

**Symptoms:**
- Increased vibration (normal < 2.0 mm/s)
- Rising temperature (normal < 80°C)
- Unusual noise

**Immediate Actions:**
1. Check lubrication levels
2. Inspect for visible damage
3. Monitor vibration trends
4. Schedule replacement if vibration > 4.0 mm/s

**Safety:** Always lock out/tag out before inspection."""
        
        # Temperature
        if "temperature" in message_lower or "overheat" in message_lower:
            return """High temperature indicates potential overheating:

**Common Causes:**
- Insufficient cooling
- Blocked ventilation
- Bearing failure
- Excessive load

**Actions:**
1. Reduce load if possible
2. Check cooling systems
3. Inspect for blockages
4. If temp > 90°C, shut down immediately

Normal operating range is typically 40-70°C."""
        
        # Vibration
        if "vibration" in message_lower:
            return """Vibration analysis is key to predictive maintenance:

**Vibration Levels:**
- Normal: < 2.0 mm/s
- Warning: 2.0-4.0 mm/s
- Critical: > 4.0 mm/s

**Possible Causes:**
- Unbalance
- Misalignment
- Bearing wear
- Loose components

**Recommendation:** If vibration exceeds 4.0 mm/s, schedule immediate inspection."""
        
        # Maintenance schedule
        if "schedule" in message_lower or "maintenance" in message_lower:
            return """Maintenance scheduling depends on several factors:

**Time-Based:**
- Daily: Visual inspection, check oil levels
- Weekly: Vibration check, temperature log
- Monthly: Detailed inspection, filter changes
- Quarterly: Bearing check, alignment verification

**Condition-Based:**
- Triggered by AI predictions
- Based on sensor thresholds
- Historical failure patterns

Would you like specific maintenance procedures for a particular machine?"""
        
        # Alert explanation
        if "alert" in message_lower or "warning" in message_lower:
            return """Alerts are generated by our 3-tier monitoring system:

**Tier 1 - Normal:**
- All sensors within normal range
- No action needed

**Tier 2 - Trending:**
- 5+ consecutive sensor increases
- Monitor closely, plan maintenance

**Tier 3 - Critical:**
- Approaching failure threshold
- AI diagnosis triggered
- Immediate action required

Alerts require two confirmations within 60 seconds before triggering notifications."""
        
        # Default response
        return """I can help you with machine maintenance questions. Try asking about:

• Specific machine issues (bearing, temperature, vibration)
• Maintenance schedules and procedures
• Understanding alerts and diagnostics
• Sensor readings and what they mean

What specific topic would you like to explore?"""


# Global client instance
copilot_client = CopilotClient()
