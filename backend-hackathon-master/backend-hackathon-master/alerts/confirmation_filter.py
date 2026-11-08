"""
Two-Confirmation Filter for SENTINEL AI Alerts.
Implements the 60-second confirmation window before triggering alerts.
"""

from typing import Dict, Optional, Callable
from datetime import datetime, timedelta
import asyncio


class ConfirmationFilter:
    """
    Two-confirmation filter:
    - First confirmation: Flags potential alert, starts 60-second timer
    - Second confirmation (within 60s): Confirms alert, triggers notification
    - Expired: Resets, requires new first confirmation
    """
    
    def __init__(self, confirmation_window_seconds: int = 60):
        self.confirmation_window = confirmation_window_seconds
        self.pending_confirmations: Dict[str, Dict] = {}
        self.confirmed_alerts: Dict[str, Dict] = {}
        
        # Callbacks
        self.on_first_confirmation: Optional[Callable] = None
        self.on_second_confirmation: Optional[Callable] = None
        self.on_expiration: Optional[Callable] = None
    
    async def process_confirmation(
        self,
        machine_id: str,
        diagnosis: Dict,
        sensor_data: Dict
    ) -> Dict:
        """
        Process a confirmation attempt.
        Returns status and action taken.
        """
        now = datetime.utcnow()
        
        # Check if already confirmed
        if machine_id in self.confirmed_alerts:
            confirmed_alert = self.confirmed_alerts[machine_id]
            return {
                "status": "already_confirmed",
                "message": "Alert already confirmed for this machine",
                "second_confirmed_at": confirmed_alert.get("second_confirmed_at", "Unknown")
            }
        
        # Check if pending confirmation exists
        if machine_id not in self.pending_confirmations:
            # First confirmation
            self.pending_confirmations[machine_id] = {
                "diagnosis": diagnosis,
                "sensor_data": sensor_data,
                "first_confirmed_at": now,
                "expires_at": now + timedelta(seconds=self.confirmation_window)
            }
            
            # Start expiration timer
            asyncio.create_task(
                self._expiration_timer(machine_id, self.confirmation_window)
            )
            
            if self.on_first_confirmation:
                await self.on_first_confirmation(machine_id, diagnosis)
            
            return {
                "status": "first_confirmation",
                "message": f"First confirmation received. Waiting {self.confirmation_window}s for second confirmation...",
                "expires_at": self.pending_confirmations[machine_id]["expires_at"].isoformat(),
                "seconds_remaining": self.confirmation_window
            }
        
        # Second confirmation
        pending = self.pending_confirmations[machine_id]
        
        # Check if expired
        if now > pending["expires_at"]:
            # Expired - reset and treat as new first confirmation
            self.pending_confirmations[machine_id] = {
                "diagnosis": diagnosis,
                "sensor_data": sensor_data,
                "first_confirmed_at": now,
                "expires_at": now + timedelta(seconds=self.confirmation_window)
            }
            
            asyncio.create_task(
                self._expiration_timer(machine_id, self.confirmation_window)
            )
            
            return {
                "status": "first_confirmation",
                "message": "Previous confirmation expired. New first confirmation received.",
                "expires_at": self.pending_confirmations[machine_id]["expires_at"].isoformat(),
                "seconds_remaining": self.confirmation_window
            }
        
        # Valid second confirmation
        seconds_elapsed = (now - pending["first_confirmed_at"]).total_seconds()
        
        confirmed_alert = {
            "machine_id": machine_id,
            "diagnosis": diagnosis,
            "sensor_data": sensor_data,
            "first_confirmed_at": pending["first_confirmed_at"].isoformat(),
            "second_confirmed_at": now.isoformat(),
            "confirmation_delay_seconds": seconds_elapsed,
            "status": "confirmed"
        }
        
        self.confirmed_alerts[machine_id] = confirmed_alert
        del self.pending_confirmations[machine_id]
        
        if self.on_second_confirmation:
            await self.on_second_confirmation(machine_id, confirmed_alert)
        
        return {
            "status": "confirmed",
            "message": "Two-confirmation complete. Alert triggered!",
            "confirmation_delay_seconds": seconds_elapsed,
            "alert": confirmed_alert
        }
    
    async def _expiration_timer(self, machine_id: str, delay_seconds: int):
        """Background timer to handle confirmation expiration."""
        await asyncio.sleep(delay_seconds)
        
        # Check if still pending (not confirmed)
        if machine_id in self.pending_confirmations:
            expired = self.pending_confirmations.pop(machine_id)
            
            if self.on_expiration:
                await self.on_expiration(machine_id, expired)
    
    def get_pending(self, machine_id: str) -> Optional[Dict]:
        """Get pending confirmation for a machine."""
        return self.pending_confirmations.get(machine_id)
    
    def get_confirmed(self, machine_id: str) -> Optional[Dict]:
        """Get confirmed alert for a machine."""
        return self.confirmed_alerts.get(machine_id)
    
    def get_time_remaining(self, machine_id: str) -> Optional[float]:
        """Get seconds remaining for pending confirmation."""
        if machine_id not in self.pending_confirmations:
            return None
        
        expires_at = self.pending_confirmations[machine_id]["expires_at"]
        remaining = (expires_at - datetime.utcnow()).total_seconds()
        return max(0, remaining)
    
    def cancel_pending(self, machine_id: str) -> bool:
        """Cancel a pending confirmation (e.g., false alarm)."""
        if machine_id in self.pending_confirmations:
            del self.pending_confirmations[machine_id]
            return True
        return False
    
    def resolve_alert(self, machine_id: str, resolution_notes: str = "") -> Optional[Dict]:
        """Mark a confirmed alert as resolved."""
        if machine_id not in self.confirmed_alerts:
            return None
        
        alert = self.confirmed_alerts.pop(machine_id)
        alert["resolved_at"] = datetime.utcnow().isoformat()
        alert["resolution_notes"] = resolution_notes
        alert["status"] = "resolved"
        
        return alert
    
    def get_all_pending(self) -> Dict[str, Dict]:
        """Get all pending confirmations."""
        return self.pending_confirmations.copy()
    
    def get_all_confirmed(self) -> Dict[str, Dict]:
        """Get all confirmed alerts."""
        return self.confirmed_alerts.copy()
    
    def get_stats(self) -> Dict:
        """Get filter statistics."""
        return {
            "pending_count": len(self.pending_confirmations),
            "confirmed_count": len(self.confirmed_alerts),
            "confirmation_window_seconds": self.confirmation_window,
            "pending_machines": list(self.pending_confirmations.keys()),
            "confirmed_machines": list(self.confirmed_alerts.keys())
        }
    
    def reset(self):
        """Reset all confirmations."""
        self.pending_confirmations.clear()
        self.confirmed_alerts.clear()
    
    def set_callbacks(
        self,
        on_first_confirmation: Optional[Callable] = None,
        on_second_confirmation: Optional[Callable] = None,
        on_expiration: Optional[Callable] = None
    ):
        """Set callback functions."""
        self.on_first_confirmation = on_first_confirmation
        self.on_second_confirmation = on_second_confirmation
        self.on_expiration = on_expiration
