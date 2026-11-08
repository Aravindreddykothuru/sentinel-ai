"""
Escalation Chain System for SENTINEL AI.
Manages auto-escalation when alerts are not acknowledged.
"""

import asyncio
from typing import Dict, Optional, List, Callable
from datetime import datetime, timedelta
from enum import Enum


class EscalationLevel(Enum):
    NONE = 0
    SUPERVISOR = 1  # 15 minutes
    MANAGER = 2     # 30 minutes
    FULL = 3        # 45 minutes


class EscalationEngine:
    """
    Auto-escalation system:
    - 0-15 min: Assigned mechanic
    - 15-30 min: Escalate to supervisor
    - 30-45 min: Escalate to plant manager
    - 45+ min: Full escalation (all stakeholders)
    """
    
    def __init__(
        self,
        escalation_intervals: Dict[int, int] = None
    ):
        # Default: 15min, 30min, 45min
        self.intervals = escalation_intervals or {
            1: 15,  # Supervisor after 15 minutes
            2: 30,  # Manager after 30 minutes
            3: 45   # Full escalation after 45 minutes
        }
        
        self.active_timers: Dict[str, asyncio.Task] = {}
        self.escalation_state: Dict[str, Dict] = {}
        
        # Callbacks
        self.on_escalation: Optional[Callable] = None
        self.on_full_escalation: Optional[Callable] = None
    
    def start_escalation_timer(self, alert_id: str, machine_id: str):
        """Start the escalation timer for an alert."""
        # Cancel existing timer if any
        self.cancel_timer(alert_id)
        
        # Initialize state
        self.escalation_state[alert_id] = {
            "alert_id": alert_id,
            "machine_id": machine_id,
            "started_at": datetime.utcnow(),
            "current_level": EscalationLevel.NONE,
            "acknowledged": False
        }
        
        # Start timer
        task = asyncio.create_task(
            self._escalation_loop(alert_id)
        )
        self.active_timers[alert_id] = task
    
    async def _escalation_loop(self, alert_id: str):
        """Background loop that handles escalation timing."""
        try:
            while alert_id in self.escalation_state:
                state = self.escalation_state[alert_id]
                
                if state["acknowledged"]:
                    break
                
                elapsed = (datetime.utcnow() - state["started_at"]).total_seconds() / 60
                current_level = state["current_level"]
                
                # Check for escalation triggers
                for level, minutes in sorted(self.intervals.items()):
                    if elapsed >= minutes and current_level.value < level:
                        await self._escalate(alert_id, EscalationLevel(level))
                        break
                
                # Check if fully escalated
                if current_level == EscalationLevel.FULL:
                    break
                
                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Escalation loop error for {alert_id}: {e}")
    
    async def _escalate(self, alert_id: str, new_level: EscalationLevel):
        """Escalate alert to new level."""
        if alert_id not in self.escalation_state:
            return
        
        state = self.escalation_state[alert_id]
        old_level = state["current_level"]
        state["current_level"] = new_level
        
        escalation_info = {
            "alert_id": alert_id,
            "machine_id": state["machine_id"],
            "old_level": old_level.name,
            "new_level": new_level.name,
            "elapsed_minutes": (datetime.utcnow() - state["started_at"]).total_seconds() / 60,
            "escalated_at": datetime.utcnow().isoformat()
        }
        
        # Trigger callback
        if self.on_escalation:
            await self.on_escalation(escalation_info)
        
        # Check for full escalation
        if new_level == EscalationLevel.FULL and self.on_full_escalation:
            await self.on_full_escalation(escalation_info)
    
    def acknowledge(self, alert_id: str) -> bool:
        """Acknowledge alert - stops escalation."""
        if alert_id not in self.escalation_state:
            return False
        
        self.escalation_state[alert_id]["acknowledged"] = True
        self.cancel_timer(alert_id)
        return True
    
    def cancel_timer(self, alert_id: str):
        """Cancel escalation timer for an alert."""
        if alert_id in self.active_timers:
            self.active_timers[alert_id].cancel()
            del self.active_timers[alert_id]
    
    def resolve(self, alert_id: str):
        """Resolve alert - stops escalation and removes state."""
        self.cancel_timer(alert_id)
        if alert_id in self.escalation_state:
            del self.escalation_state[alert_id]
    
    def get_state(self, alert_id: str) -> Optional[Dict]:
        """Get current escalation state for an alert."""
        if alert_id not in self.escalation_state:
            return None
        
        state = self.escalation_state[alert_id].copy()
        state["current_level"] = state["current_level"].name
        state["elapsed_minutes"] = (datetime.utcnow() - state["started_at"]).total_seconds() / 60
        state["next_escalation"] = self._get_next_escalation(alert_id)
        return state
    
    def _get_next_escalation(self, alert_id: str) -> Optional[Dict]:
        """Get information about next escalation."""
        if alert_id not in self.escalation_state:
            return None
        
        state = self.escalation_state[alert_id]
        current_level = state["current_level"]
        elapsed = (datetime.utcnow() - state["started_at"]).total_seconds() / 60
        
        # Find next level
        next_level_num = current_level.value + 1
        if next_level_num > 3:
            return None
        
        next_minutes = self.intervals.get(next_level_num)
        if not next_minutes:
            return None
        
        remaining = next_minutes - elapsed
        
        return {
            "level": EscalationLevel(next_level_num).name,
            "in_minutes": max(0, remaining),
            "at_time": (state["started_at"] + timedelta(minutes=next_minutes)).isoformat()
        }
    
    def get_active_escalations(self) -> List[Dict]:
        """Get all active escalations."""
        return [
            self.get_state(alert_id)
            for alert_id in self.escalation_state
        ]
    
    def get_stats(self) -> Dict:
        """Get escalation statistics."""
        levels = {level: 0 for level in EscalationLevel}
        
        for state in self.escalation_state.values():
            levels[state["current_level"]] += 1
        
        return {
            "active_escalations": len(self.escalation_state),
            "by_level": {level.name: count for level, count in levels.items()},
            "intervals": self.intervals
        }
    
    def set_callbacks(
        self,
        on_escalation: Optional[Callable] = None,
        on_full_escalation: Optional[Callable] = None
    ):
        """Set callback functions."""
        self.on_escalation = on_escalation
        self.on_full_escalation = on_full_escalation


# Global escalation engine instance
escalation_engine = EscalationEngine()
