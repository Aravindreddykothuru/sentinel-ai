"""
Grok (xAI) API Client for SENTINEL AI.
Used to generate physics-based machine degradation data.
"""

import os
import json
from typing import Dict, Optional
import httpx
from config import get_settings

settings = get_settings()


class GrokClient:
    """
    Client for xAI Grok API.
    Generates physics-based sensor degradation data.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.XAI_API_KEY
        self.base_url = "https://api.x.ai/v1"
        self.model = "grok-beta"
        
    async def generate_sensor_data(
        self,
        machine_type: str,
        current_values: Dict[str, float],
        degradation_factor: float,
        reading_number: int
    ) -> Dict:
        """
        Generate realistic sensor data using Grok.
        Falls back to local simulation if API not available.
        """
        if not self.api_key:
            # Fallback to local simulation
            return self._local_simulation(machine_type, current_values, degradation_factor)
        
        try:
            prompt = self._build_prompt(machine_type, current_values, degradation_factor, reading_number)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a physics engine for industrial machinery simulation. Generate realistic sensor readings based on machine type and degradation state. Return only JSON."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.3,
                        "max_tokens": 200
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    # Parse JSON from response
                    return json.loads(content)
                else:
                    # Fallback on API error
                    return self._local_simulation(machine_type, current_values, degradation_factor)
                    
        except Exception as e:
            print(f"Grok API error: {e}")
            return self._local_simulation(machine_type, current_values, degradation_factor)
    
    def _build_prompt(
        self,
        machine_type: str,
        current_values: Dict[str, float],
        degradation_factor: float,
        reading_number: int,
        sensor_config: Optional[Dict] = None
    ) -> str:
        """Build prompt for Grok API with dynamic sensor configuration."""
        
        # Build sensor-specific physics guidance
        sensor_guidance = []
        for sensor in current_values.keys():
            if sensor == "temperature":
                sensor_guidance.append(f"- {sensor}: Increases with friction/wear, normal drift +0.1 to +0.5 per reading")
            elif sensor == "vibration":
                sensor_guidance.append(f"- {sensor}: Increases with bearing degradation, normal drift +0.01 to +0.05 per reading")
            elif sensor == "rpm":
                sensor_guidance.append(f"- {sensor}: Slight decrease with load increase, normal drift -0.5 to -2.0 per reading")
            elif sensor == "pressure":
                sensor_guidance.append(f"- {sensor}: Decreases with seal wear, normal drift -0.05 to -0.2 per reading")
            elif sensor == "flow_rate":
                sensor_guidance.append(f"- {sensor}: Decreases with blockage/pump wear, normal drift -0.5 to -1.0 per reading")
            elif sensor == "current":
                sensor_guidance.append(f"- {sensor}: Increases with motor load/wear, normal drift +0.05 to +0.1 per reading")
            elif sensor == "fuel_flow":
                sensor_guidance.append(f"- {sensor}: Increases with efficiency loss, normal drift +0.02 to +0.05 per reading")
            elif sensor == "voltage":
                sensor_guidance.append(f"- {sensor}: Slight decrease with load, normal drift -0.1 to -0.3 per reading")
            else:
                sensor_guidance.append(f"- {sensor}: Apply realistic physics-based drift")
        
        guidance_text = "\n".join(sensor_guidance)
        
        # Build JSON structure dynamically
        sensor_keys = list(current_values.keys())
        json_structure = ",\n  ".join([f'"{k}": <value>' for k in sensor_keys])
        
        return f"""Generate the next sensor reading for a {machine_type}.

Current sensor values:
{json.dumps(current_values, indent=2)}

Degradation factor: {degradation_factor} (1.0 = new machine, 2.0+ = significantly degraded)
Reading number: {reading_number}

Physics-based degradation rules:
{guidance_text}

Generate realistic sensor values that show gradual degradation over time.
Apply small random noise (±5%) to each sensor.
The degradation factor amplifies the drift - higher factor = faster degradation.

Return ONLY a JSON object with this structure:
{{
  {json_structure}
}}"""
    
    def _local_simulation(
        self,
        machine_type: str,
        current_values: Dict[str, float],
        degradation_factor: float
    ) -> Dict:
        """Local fallback simulation when Grok API is unavailable."""
        import random
        
        # Apply degradation drift based on sensor type
        new_values = {}
        for sensor, value in current_values.items():
            # Base drift based on sensor type
            if sensor == "temperature":
                drift = random.uniform(0.05, 0.3) * degradation_factor
                noise = random.gauss(0, 1.5)
            elif sensor == "vibration":
                drift = random.uniform(0.005, 0.02) * degradation_factor
                noise = random.gauss(0, 0.15)
            elif sensor == "rpm":
                drift = random.uniform(-2.0, -0.5) * degradation_factor
                noise = random.gauss(0, 25.0)
            elif sensor == "pressure":
                drift = random.uniform(-0.15, -0.03) * degradation_factor
                noise = random.gauss(0, 1.5)
            elif sensor == "flow_rate":
                drift = random.uniform(-1.0, -0.3) * degradation_factor
                noise = random.gauss(0, 8.0)
            elif sensor == "current":
                drift = random.uniform(0.03, 0.08) * degradation_factor
                noise = random.gauss(0, 1.0)
            elif sensor == "fuel_flow":
                drift = random.uniform(0.01, 0.04) * degradation_factor
                noise = random.gauss(0, 0.8)
            elif sensor == "voltage":
                drift = random.uniform(-0.2, -0.05) * degradation_factor
                noise = random.gauss(0, 0.5)
            else:
                drift = random.uniform(-0.1, 0.1) * degradation_factor
                noise = random.gauss(0, 1.0)
            
            new_values[sensor] = round(value + drift + noise, 2)
        
        return new_values
    
    async def validate_diagnosis(
        self,
        sensor_data: Dict,
        gemini_diagnosis: Dict
    ) -> Dict:
        """
        Validate Gemini's diagnosis against physics.
        Returns validation result with confidence score.
        """
        if not self.api_key:
            return {"valid": True, "confidence": 80, "notes": "No validation available"}
        
        try:
            prompt = f"""Validate this failure diagnosis based on sensor data:

Sensor Data:
{json.dumps(sensor_data, indent=2)}

Gemini Diagnosis:
{json.dumps(gemini_diagnosis, indent=2)}

Does this diagnosis make physical sense? Consider:
1. Are the sensor values consistent with the failure type?
2. Is the confidence level appropriate?
3. Are there any contradictions?

Return JSON:
{{
  "valid": true/false,
  "confidence": 0-100,
  "notes": "explanation"
}}"""
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a mechanical engineering expert validating AI diagnoses."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.2,
                        "max_tokens": 200
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    return json.loads(content)
                else:
                    return {"valid": True, "confidence": 75, "notes": "Validation service unavailable"}
                    
        except Exception as e:
            print(f"Grok validation error: {e}")
            return {"valid": True, "confidence": 70, "notes": f"Validation error: {str(e)}"}


# Global client instance
grok_client = GrokClient()
