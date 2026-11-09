"""
Gemini (Google) API Client for SENTINEL AI.
Used for failure diagnosis and maintenance scheduling.
"""

import os
import re
import json
from functools import lru_cache
from typing import Dict, Optional
from datetime import datetime
import google.generativeai as genai
from config import get_settings

settings = get_settings()

STABLE_FLASH = re.compile(r"gemini-(\d+(?:\.\d+)*)-flash(-lite)?")
MAX_MODEL_ATTEMPTS = 4


def is_quota_error(error: Exception) -> bool:
    text = str(error)
    return "429" in text or "quota" in text.lower()


@lru_cache()
def model_candidates(preferred: str) -> tuple:
    """
    Models to try in order: the preferred one if the configured key can still call it, then
    stable Flash models newest-first, then Flash-Lite. Google retires model versions (a
    hardcoded name then 404s), and each model has its own free-tier quota, so callers move
    down this list on 429. Call after genai.configure().
    """
    try:
        available = {
            m.name.removeprefix("models/")
            for m in genai.list_models()
            if "generateContent" in m.supported_generation_methods
        }
    except Exception as e:
        print(f"[Gemini] Could not list models ({e}); using {preferred}")
        return (preferred,)

    def rank(name):
        match = STABLE_FLASH.fullmatch(name)
        return (bool(match.group(2)), tuple(-int(p) for p in match.group(1).split(".")))

    stable = sorted((m for m in available if STABLE_FLASH.fullmatch(m)), key=rank)
    candidates = ([preferred] if preferred in available else []) + [m for m in stable if m != preferred]
    if not candidates:
        candidates = [m for m in sorted(available) if "flash" in m] or [preferred]
    return tuple(candidates[:MAX_MODEL_ATTEMPTS])


def resolve_model_name(preferred: str) -> str:
    """The model to use by default (first candidate)."""
    chosen = model_candidates(preferred)[0]
    if chosen != preferred:
        print(f"[Gemini] Model '{preferred}' is not available; using '{chosen}'")
    return chosen


class GeminiClient:
    """
    Client for Google Gemini API.
    Performs failure diagnosis and maintenance scheduling.
    Supports multiple API keys with automatic fallback on quota errors.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        # GOOGLE_API_KEY may hold several comma-separated keys; later ones are quota fallbacks
        keys = api_key or settings.GOOGLE_API_KEY or os.getenv("GOOGLE_API_KEY", "")
        self.api_keys = [k.strip() for k in keys.split(",") if k.strip()]
        self.current_key_index = 0
        self.model_name = settings.GEMINI_MODEL
        self.model = None
        
        # Initialize with first available key
        self._configure_with_next_key()
    
    def _configure_with_next_key(self) -> bool:
        """Configure Gemini with the next available API key. Returns True if successful."""
        while self.current_key_index < len(self.api_keys):
            key = self.api_keys[self.current_key_index]
            try:
                genai.configure(api_key=key)
                self.model_name = resolve_model_name(self.model_name)
                self.model = genai.GenerativeModel(self.model_name)
                self.api_key = key
                print(f"[Gemini] Configured with API key #{self.current_key_index + 1} ({self.model_name})")
                return True
            except Exception as e:
                print(f"[Gemini] Failed to configure key #{self.current_key_index + 1}: {e}")
                self.current_key_index += 1
        
        self.model = None
        self.api_key = None
        return False
    
    def _switch_to_next_key(self) -> bool:
        """Switch to the next API key after quota error. Returns True if switched successfully."""
        self.current_key_index += 1
        return self._configure_with_next_key()
    
    async def diagnose_failure(
        self,
        machine_id: str,
        machine_type: str,
        sensor_data: Dict,
        tier_info: Dict,
        history: Optional[list] = None
    ) -> Dict:
        """
        Diagnose potential failure based on sensor data.
        Returns structured diagnosis with confidence score.
        Automatically switches to fallback API key on quota errors.
        """
        if not self.model:
            return self._mock_diagnosis(machine_id, machine_type, sensor_data, tier_info)
        
        prompt = self._build_diagnosis_prompt(
            machine_id, machine_type, sensor_data, tier_info, history
        )
        
        # Try current key, then fallback keys on quota errors
        while self.current_key_index < len(self.api_keys):
            # Each model has its own quota, so try the other available models before the next key
            for model_name in model_candidates(self.model_name):
                try:
                    model = self.model if model_name == self.model_name else genai.GenerativeModel(model_name)
                    response = await model.generate_content_async(prompt)
                    text = response.text
                except Exception as e:
                    if is_quota_error(e):
                        print(f"[Gemini] Quota exceeded for {model_name} (key #{self.current_key_index + 1}), trying fallback...")
                        continue
                    print(f"Gemini API error: {e}")
                    return self._mock_diagnosis(machine_id, machine_type, sensor_data, tier_info)

                # Parse JSON from response
                try:
                    # Find JSON block
                    if "```json" in text:
                        json_str = text.split("```json")[1].split("```")[0]
                    elif "```" in text:
                        json_str = text.split("```")[1].split("```")[0]
                    else:
                        json_str = text

                    diagnosis = json.loads(json_str.strip())
                    return diagnosis

                except json.JSONDecodeError:
                    # Fallback if JSON parsing fails
                    return self._parse_text_response(text, machine_id, sensor_data)

            # Every model is out of quota on this key
            if not self._switch_to_next_key():
                # Out of quota everywhere for now; quotas reset, so start from the first key next time
                self.current_key_index = 0
                self._configure_with_next_key()
                break

        # All keys exhausted, use mock
        return self._mock_diagnosis(machine_id, machine_type, sensor_data, tier_info)
    
    def _build_diagnosis_prompt(
        self,
        machine_id: str,
        machine_type: str,
        sensor_data: Dict,
        tier_info: Dict,
        history: Optional[list]
    ) -> str:
        """Build prompt for failure diagnosis."""
        history_str = ""
        if history:
            history_str = f"\nRecent sensor history (last 5 readings):\n{json.dumps(history[-5:], indent=2)}"
        
        return f"""You are an expert industrial maintenance AI. Analyze the following machine data and provide a failure diagnosis.

Machine ID: {machine_id}
Machine Type: {machine_type}
Current Tier: {tier_info.get('label', 'UNKNOWN')}
Alert Reason: {tier_info.get('reason', 'N/A')}

Current Sensor Data:
{json.dumps(sensor_data, indent=2)}{history_str}

Provide a diagnosis in this exact JSON format:
{{
  "failure_type": "Specific failure type (e.g., Bearing Failure, Overheating, Hydraulic Leak)",
  "confidence": <number 0-100>,
  "severity": "WARNING|CRITICAL|EMERGENCY",
  "time_to_breach": "Estimated time until failure (e.g., '8 minutes', '2 hours', '1 day')",
  "action": "Specific immediate action to take",
  "root_cause": "Likely root cause of the issue",
  "recommended_parts": ["Part 1", "Part 2"],
  "safety_concerns": "Any safety warnings"
}}

Be specific and actionable. Confidence should reflect certainty based on sensor patterns."""
    
    def _mock_diagnosis(
        self,
        machine_id: str,
        machine_type: str,
        sensor_data: Dict,
        tier_info: Dict
    ) -> Dict:
        """Mock diagnosis when API is unavailable."""
        sensors = sensor_data.get('sensors', sensor_data)
        
        # Simple rule-based mock diagnosis
        failure_type = "Normal Operation"
        confidence = 50
        severity = "WARNING"
        time_to_breach = "Unknown"
        action = "Continue monitoring"
        
        temp = sensors.get('temperature', 0)
        vib = sensors.get('vibration', 0)
        pressure = sensors.get('pressure', 0)
        
        if temp > 95:
            failure_type = "Overheating"
            confidence = 85
            severity = "CRITICAL"
            time_to_breach = "15 minutes"
            action = "Reduce load immediately, check cooling system"
        elif vib > 3.5:
            failure_type = "Bearing Failure"
            confidence = 78
            severity = "CRITICAL"
            time_to_breach = "30 minutes"
            action = "Schedule immediate inspection, prepare bearing replacement"
        elif pressure < 75:
            failure_type = "Pressure Loss"
            confidence = 72
            severity = "WARNING"
            time_to_breach = "2 hours"
            action = "Check for leaks, verify pump operation"
        elif tier_info.get('label') == 'TRENDING':
            failure_type = "Gradual Degradation"
            confidence = 65
            severity = "WARNING"
            time_to_breach = "4 hours"
            action = "Schedule maintenance during next window"
        
        return {
            "failure_type": failure_type,
            "confidence": confidence,
            "severity": severity,
            "time_to_breach": time_to_breach,
            "action": action,
            "root_cause": "Wear and tear based on sensor trends",
            "recommended_parts": ["Inspect before ordering"],
            "safety_concerns": "None" if severity == "WARNING" else "Potential equipment damage"
        }
    
    def _parse_text_response(self, text: str, machine_id: str, sensor_data: Dict) -> Dict:
        """Parse non-JSON response text."""
        return {
            "failure_type": "Unknown (Parse Error)",
            "confidence": 50,
            "severity": "WARNING",
            "time_to_breach": "Unknown",
            "action": "Manual inspection required",
            "root_cause": text[:200] if text else "Could not parse response",
            "recommended_parts": [],
            "safety_concerns": "None"
        }
    
    async def recommend_maintenance_window(
        self,
        machine_id: str,
        machine_type: str,
        time_to_failure: str,
        shift_schedule: Dict,
        current_sensors: Dict
    ) -> Dict:
        """
        Recommend optimal maintenance window based on schedule and failure prediction.
        """
        if not self.api_key or not self.model:
            return self._mock_maintenance_recommendation(
                machine_id, time_to_failure, shift_schedule
            )
        
        try:
            prompt = f"""Recommend the optimal maintenance window for this machine.

Machine ID: {machine_id}
Machine Type: {machine_type}
Predicted Time to Failure: {time_to_failure}
Current Sensor Values: {json.dumps(current_sensors, indent=2)}

Shift Schedule:
{json.dumps(shift_schedule, indent=2)}

Provide recommendation in this JSON format:
{{
  "recommended_window": "Specific date/time (e.g., 'Today 13:45', 'Tomorrow 06:00')",
  "production_impact": "LOW|MEDIUM|HIGH",
  "impact_reason": "Why this impact level",
  "time_available": "How much time before failure",
  "savings_vs_emergency": <estimated dollar savings>,
  "alternative_windows": ["Option 1", "Option 2"],
  "preparation_needed": ["Task 1", "Task 2"]
}}

Consider:
- Must schedule BEFORE predicted failure time
- Minimize production impact
- Account for repair time needed
- Use shift changeover windows when possible"""
            
            response = await self.model.generate_content_async(prompt)
            
            try:
                text = response.text
                if "```json" in text:
                    json_str = text.split("```json")[1].split("```")[0]
                elif "```" in text:
                    json_str = text.split("```")[1].split("```")[0]
                else:
                    json_str = text
                
                return json.loads(json_str.strip())
                
            except json.JSONDecodeError:
                return self._mock_maintenance_recommendation(
                    machine_id, time_to_failure, shift_schedule
                )
                
        except Exception as e:
            print(f"Gemini maintenance recommendation error: {e}")
            return self._mock_maintenance_recommendation(
                machine_id, time_to_failure, shift_schedule
            )
    
    def _mock_maintenance_recommendation(
        self,
        machine_id: str,
        time_to_failure: str,
        shift_schedule: Dict
    ) -> Dict:
        """Mock maintenance recommendation with full scheduling details."""
        maintenance_windows = shift_schedule.get('maintenance_windows', ['13:45', '21:45'])
        
        from datetime import datetime, timedelta
        
        # Calculate recommended times
        now = datetime.now()
        window_time = maintenance_windows[0]
        hour, minute = map(int, window_time.split(':'))
        
        recommended_start = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if recommended_start < now:
            recommended_start += timedelta(days=1)
        
        duration_hours = 2.5
        recommended_end = recommended_start + timedelta(hours=duration_hours)
        
        return {
            "recommended_start": recommended_start.isoformat(),
            "recommended_end": recommended_end.isoformat(),
            "duration_hours": duration_hours,
            "production_impact": "LOW",
            "impact_reason": "Shift changeover window - zero production loss",
            "confidence_score": 85,
            "reasoning": "Selected during shift changeover when production is minimal. Provides adequate time before predicted failure.",
            "factors": {
                "production_impact": "LOW",
                "failure_urgency": "HIGH",
                "parts_availability": "AVAILABLE",
                "mechanic_availability": True,
                "optimal_conditions": ["shift_changeover", "cooling_period", "minimal_demand"]
            },
            "time_available": time_to_failure,
            "estimated_downtime_cost": 5000,
            "maintenance_type": "corrective",
            "required_parts": ["bearing_assembly", "lubricant_seal"],
            "required_tools": ["torque_wrench", "hydraulic_lift", "bearing_puller"],
            "estimated_labor_hours": 3.0,
            "alternative_windows": [
                {
                    "start": (recommended_start + timedelta(hours=8)).isoformat(),
                    "end": (recommended_start + timedelta(hours=10.5)).isoformat(),
                    "impact": "MEDIUM"
                }
            ]
        }


# Global client instance
gemini_client = GeminiClient()
