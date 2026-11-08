"""
Alert Manager for SENTINEL AI.
Manages alert lifecycle from creation to resolution.
"""

import uuid
from typing import Dict, Optional, List, Callable
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from database import get_db
from models import Alert as AlertModel, Machine, Mechanic
from alerts.confirmation_filter import ConfirmationFilter


class AlertManager:
    """
    Manages the complete alert lifecycle:
    1. Create alert from confirmed diagnosis
    2. Assign to mechanic
    3. Track escalation
    4. Handle resolution
    """
    
    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self.confirmation_filter = ConfirmationFilter(confirmation_window_seconds=180)  # 3 minutes to match Grok interval
        self.active_alerts: Dict[str, Dict] = {}
        
        # Set up confirmation callbacks
        self.confirmation_filter.on_second_confirmation = self._on_alert_confirmed
        
        # Callbacks
        self.on_alert_created: Optional[Callable] = None
        self.on_alert_escalated: Optional[Callable] = None
        self.on_alert_resolved: Optional[Callable] = None
    
    async def process_diagnosis(
        self,
        machine_id: str,
        diagnosis: Dict,
        sensor_data: Dict
    ) -> Dict:
        """
        Process a diagnosis through the two-confirmation filter.
        """
        return await self.confirmation_filter.process_confirmation(
            machine_id=machine_id,
            diagnosis=diagnosis,
            sensor_data=sensor_data
        )
    
    async def _on_alert_confirmed(self, machine_id: str, confirmed_alert: Dict):
        """
        Callback when two-confirmation is complete.
        Creates the actual alert and notifies assigned mechanic.
        """
        # Create alert in database
        alert = self._create_alert_in_db(machine_id, confirmed_alert)
        
        # Store in active alerts
        self.active_alerts[alert.alert_id] = {
            "alert_id": alert.alert_id,
            "machine_id": machine_id,
            "created_at": datetime.utcnow(),
            "escalation_level": 0,
            "escalation_timer": None,
            "assigned_mechanic": None,
            "status": "open"
        }
        
        # Find and assign mechanic
        mechanic = self._find_assigned_mechanic(machine_id)
        if mechanic:
            self.active_alerts[alert.alert_id]["assigned_mechanic"] = mechanic.id
            alert.assigned_mechanic_id = mechanic.id
            if self.db:
                self.db.commit()
        
        # Start escalation timer
        self._start_escalation_timer(alert.alert_id)
        
        # Trigger callback
        if self.on_alert_created:
            await self.on_alert_created(alert, mechanic)
    
    def _create_alert_in_db(self, machine_id: str, confirmed_alert: Dict) -> AlertModel:
        """Create alert record in database."""
        alert_id = f"ALT-{uuid.uuid4().hex[:8].upper()}"
        diagnosis = confirmed_alert["diagnosis"]
        
        # Parse ISO format strings back to datetime
        from datetime import datetime
        first_confirmed = confirmed_alert.get("first_confirmed_at")
        second_confirmed = confirmed_alert.get("second_confirmed_at")
        
        if isinstance(first_confirmed, str):
            first_confirmed = datetime.fromisoformat(first_confirmed.replace('Z', '+00:00').replace('+00:00', ''))
        if isinstance(second_confirmed, str):
            second_confirmed = datetime.fromisoformat(second_confirmed.replace('Z', '+00:00').replace('+00:00', ''))
        
        alert = AlertModel(
            alert_id=alert_id,
            machine_id=machine_id,
            status="open",
            severity=diagnosis.get("severity", "WARNING"),
            failure_type=diagnosis.get("failure_type", "Unknown"),
            confidence=diagnosis.get("confidence", 0),
            time_to_breach=diagnosis.get("time_to_breach", "Unknown"),
            recommended_action=diagnosis.get("action", ""),
            sensor_snapshot=confirmed_alert.get("sensor_data", {}),
            first_confirmation_at=first_confirmed,
            second_confirmation_at=second_confirmed,
            confirmed=True,
            maintenance_window=diagnosis.get("time_to_breach"),
            production_impact="PENDING"
        )
        
        if self.db:
            self.db.add(alert)
            self.db.commit()
            self.db.refresh(alert)
        
        return alert
    
    def _find_assigned_mechanic(self, machine_id: str) -> Optional[Mechanic]:
        """Find mechanic assigned to this machine."""
        if not self.db:
            return None
        
        machine = self.db.query(Machine).filter(Machine.machine_id == machine_id).first()
        if machine and machine.assigned_mechanic:
            return machine.assigned_mechanic
        
        # Fallback: find any available mechanic
        return self.db.query(Mechanic).filter(Mechanic.is_available == True).first()
    
    def _start_escalation_timer(self, alert_id: str):
        """Start the escalation timer for this alert."""
        import asyncio
        
        async def escalate():
            await asyncio.sleep(900)  # 15 minutes
            await self._escalate_alert(alert_id, level=1)
        
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id]["escalation_timer"] = asyncio.create_task(escalate())
    
    async def _escalate_alert(self, alert_id: str, level: int):
        """Escalate alert to next level."""
        if alert_id not in self.active_alerts:
            return
        
        alert_data = self.active_alerts[alert_id]
        alert_data["escalation_level"] = level
        
        # Update database
        if self.db:
            alert = self.db.query(AlertModel).filter(AlertModel.alert_id == alert_id).first()
            if alert:
                alert.escalation_level = level
                alert.escalated_at = datetime.utcnow()
                self.db.commit()
        
        # Trigger callback
        if self.on_alert_escalated:
            await self.on_alert_escalated(alert_id, level)
        
        # Schedule next escalation
        if level < 3:
            import asyncio
            async def next_escalation():
                await asyncio.sleep(900)  # Another 15 minutes
                await self._escalate_alert(alert_id, level + 1)
            
            alert_data["escalation_timer"] = asyncio.create_task(next_escalation())
    
    async def acknowledge_alert(self, alert_id: str, mechanic_id: int) -> bool:
        """Mechanic acknowledges the alert."""
        if alert_id not in self.active_alerts:
            return False
        
        alert_data = self.active_alerts[alert_id]
        alert_data["status"] = "acknowledged"
        
        # Cancel escalation timer
        if alert_data.get("escalation_timer"):
            alert_data["escalation_timer"].cancel()
        
        # Update database
        if self.db:
            alert = self.db.query(AlertModel).filter(AlertModel.alert_id == alert_id).first()
            if alert:
                alert.status = "acknowledged"
                alert.responded_by_id = mechanic_id
                alert.responded_at = datetime.utcnow()
                alert.response = "acknowledged"
                self.db.commit()
        
        return True
    
    async def resolve_alert(
        self,
        alert_id: str,
        mechanic_id: int,
        resolution: str,
        notes: str = "",
        gemini_was_correct: Optional[bool] = None
    ) -> bool:
        """Resolve an alert."""
        if alert_id not in self.active_alerts:
            return False
        
        alert_data = self.active_alerts.pop(alert_id)
        
        # Cancel escalation timer
        if alert_data.get("escalation_timer"):
            alert_data["escalation_timer"].cancel()
        
        # Update database
        if self.db:
            alert = self.db.query(AlertModel).filter(AlertModel.alert_id == alert_id).first()
            if alert:
                alert.status = "resolved"
                alert.resolved_at = datetime.utcnow()
                alert.resolved_by_id = mechanic_id
                alert.resolution = resolution
                alert.resolution_notes = notes
                alert.gemini_was_correct = gemini_was_correct
                self.db.commit()
        
        # Clear from confirmation filter
        self.confirmation_filter.resolve_alert(alert_data["machine_id"], notes)
        
        # Trigger callback
        if self.on_alert_resolved:
            await self.on_alert_resolved(alert_id, resolution)
        
        return True
    
    def get_active_alert_for_machine(self, machine_id: str) -> Optional[Dict]:
        """Get active alert for a specific machine."""
        for alert_id, alert_data in self.active_alerts.items():
            if alert_data["machine_id"] == machine_id:
                return alert_data
        return None
    
    def get_alert_by_id(self, alert_id: str) -> Optional[Dict]:
        """Get alert by ID."""
        return self.active_alerts.get(alert_id)
    
    def get_all_active_alerts(self) -> List[Dict]:
        """Get all active alerts."""
        return list(self.active_alerts.values())
    
    def get_stats(self) -> Dict:
        """Get alert manager statistics."""
        return {
            "active_alerts": len(self.active_alerts),
            "pending_confirmations": self.confirmation_filter.get_stats()["pending_count"],
            "confirmed_alerts": self.confirmation_filter.get_stats()["confirmed_count"]
        }


# Global alert manager instance
alert_manager = AlertManager()
