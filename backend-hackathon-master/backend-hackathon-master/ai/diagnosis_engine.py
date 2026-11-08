"""
Diagnosis Engine - Orchestrates failure diagnosis using Gemini.
Integrates with the 3-tier monitoring system.
"""

from typing import Dict, Optional, Callable
from datetime import datetime
import asyncio

from ai.gemini_client import GeminiClient, gemini_client
from engine import TierResult


class DiagnosisEngine:
    """
    Manages failure diagnosis workflow:
    1. Receives trigger from Tier 3 (Critical)
    2. Calls Gemini for diagnosis
    3. Implements two-confirmation filter
    4. Triggers alerts if confirmed
    """
    
    def __init__(self):
        self.gemini = gemini_client
        self.pending_confirmations: Dict[str, Dict] = {}  # machine_id -> pending diagnosis
        self.confirmed_diagnoses: Dict[str, Dict] = {}    # machine_id -> confirmed diagnosis
        self.diagnosis_history: list = []
        
        # Callbacks
        self.on_first_confirmation: Optional[Callable] = None
        self.on_second_confirmation: Optional[Callable] = None
        self.on_alert_triggered: Optional[Callable] = None
    
    async def process_critical_tier(
        self,
        machine_id: str,
        machine_type: str,
        sensor_data: Dict,
        tier_result: TierResult,
        history: Optional[list] = None
    ) -> Dict:
        """
        Process Tier 3 (Critical) - triggers diagnosis workflow.
        Implements two-confirmation filter.
        """
        # Get diagnosis from Gemini
        diagnosis = await self.gemini.diagnose_failure(
            machine_id=machine_id,
            machine_type=machine_type,
            sensor_data=sensor_data,
            tier_info={
                "label": tier_result.label,
                "reason": tier_result.reason,
                "level": tier_result.level.value
            },
            history=history
        )
        
        # Check confidence threshold (80%)
        if diagnosis.get("confidence", 0) < 80:
            return {
                "status": "below_threshold",
                "diagnosis": diagnosis,
                "message": f"Confidence {diagnosis.get('confidence')}% below 80% threshold"
            }
        
        # Two-confirmation logic
        if machine_id not in self.pending_confirmations:
            # First confirmation
            self.pending_confirmations[machine_id] = {
                "diagnosis": diagnosis,
                "first_confirmed_at": datetime.utcnow(),
                "sensor_data": sensor_data
            }
            
            if self.on_first_confirmation:
                await self.on_first_confirmation(machine_id, diagnosis)
            
            return {
                "status": "first_confirmation",
                "diagnosis": diagnosis,
                "message": "First confirmation received. Waiting 60 seconds for second confirmation..."
            }
        
        else:
            # Second confirmation
            pending = self.pending_confirmations[machine_id]
            time_diff = (datetime.utcnow() - pending["first_confirmed_at"]).total_seconds()
            
            # Check if within confirmation window (60 seconds)
            if time_diff > 60:
                # Reset and start over
                self.pending_confirmations[machine_id] = {
                    "diagnosis": diagnosis,
                    "first_confirmed_at": datetime.utcnow(),
                    "sensor_data": sensor_data
                }
                return {
                    "status": "first_confirmation",
                    "diagnosis": diagnosis,
                    "message": "Previous confirmation expired. New first confirmation received."
                }
            
            # Second confirmation successful
            confirmed_diagnosis = {
                **diagnosis,
                "confirmed_at": datetime.utcnow().isoformat(),
                "confirmation_delay_seconds": time_diff
            }
            
            self.confirmed_diagnoses[machine_id] = confirmed_diagnosis
            self.diagnosis_history.append({
                "machine_id": machine_id,
                "diagnosis": confirmed_diagnosis,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Clear pending
            del self.pending_confirmations[machine_id]
            
            # Trigger callbacks
            if self.on_second_confirmation:
                await self.on_second_confirmation(machine_id, confirmed_diagnosis)
            
            if self.on_alert_triggered:
                await self.on_alert_triggered(machine_id, confirmed_diagnosis)
            
            return {
                "status": "confirmed",
                "diagnosis": confirmed_diagnosis,
                "message": "Two-confirmation complete. Alert triggered!"
            }
    
    async def get_maintenance_recommendation(
        self,
        machine_id: str,
        machine_type: str,
        time_to_failure: str,
        shift_schedule: Dict,
        current_sensors: Dict
    ) -> Dict:
        """Get maintenance window recommendation from Gemini."""
        return await self.gemini.recommend_maintenance_window(
            machine_id=machine_id,
            machine_type=machine_type,
            time_to_failure=time_to_failure,
            shift_schedule=shift_schedule,
            current_sensors=current_sensors
        )
    
    def get_pending_confirmation(self, machine_id: str) -> Optional[Dict]:
        """Get pending confirmation for a machine."""
        return self.pending_confirmations.get(machine_id)
    
    def get_confirmed_diagnosis(self, machine_id: str) -> Optional[Dict]:
        """Get confirmed diagnosis for a machine."""
        return self.confirmed_diagnoses.get(machine_id)
    
    def clear_diagnosis(self, machine_id: str):
        """Clear diagnosis for a machine (e.g., after resolution)."""
        self.pending_confirmations.pop(machine_id, None)
        self.confirmed_diagnoses.pop(machine_id, None)
    
    def get_diagnosis_stats(self) -> Dict:
        """Get diagnosis engine statistics."""
        return {
            "pending_confirmations": len(self.pending_confirmations),
            "confirmed_diagnoses": len(self.confirmed_diagnoses),
            "total_diagnoses": len(self.diagnosis_history),
            "pending_machines": list(self.pending_confirmations.keys()),
            "confirmed_machines": list(self.confirmed_diagnoses.keys())
        }
    
    def set_callbacks(
        self,
        on_first_confirmation: Optional[Callable] = None,
        on_second_confirmation: Optional[Callable] = None,
        on_alert_triggered: Optional[Callable] = None
    ):
        """Set callback functions for diagnosis events."""
        self.on_first_confirmation = on_first_confirmation
        self.on_second_confirmation = on_second_confirmation
        self.on_alert_triggered = on_alert_triggered


# Global diagnosis engine instance
diagnosis_engine = DiagnosisEngine()
