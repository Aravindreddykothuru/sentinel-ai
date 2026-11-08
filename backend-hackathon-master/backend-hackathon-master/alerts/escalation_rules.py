"""
Escalation Rules for SENTINEL AI.
Defines who gets notified at each escalation level.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class EscalationLevel(Enum):
    NONE = 0
    MECHANIC = 1
    SUPERVISOR = 2
    MANAGER = 3
    FULL = 4


@dataclass
class EscalationRule:
    """Defines notification targets for an escalation level."""
    level: EscalationLevel
    name: str
    description: str
    notify_channels: List[str]
    include_mechanic: bool
    include_supervisor: bool
    include_manager: bool
    sms_override: bool  # Use SMS if other channels fail


class EscalationRules:
    """
    Default escalation rules:
    - Level 0: Assigned mechanic only
    - Level 1: Mechanic + Supervisor
    - Level 2: Mechanic + Supervisor + Manager
    - Level 3: All stakeholders + SMS override
    """
    
    DEFAULT_RULES = {
        EscalationLevel.MECHANIC: EscalationRule(
            level=EscalationLevel.MECHANIC,
            name="Initial Alert",
            description="Notify assigned mechanic only",
            notify_channels=["email", "whatsapp"],
            include_mechanic=True,
            include_supervisor=False,
            include_manager=False,
            sms_override=False
        ),
        
        EscalationLevel.SUPERVISOR: EscalationRule(
            level=EscalationLevel.SUPERVISOR,
            name="Supervisor Escalation",
            description="Escalate to supervisor after 15 minutes",
            notify_channels=["email", "whatsapp"],
            include_mechanic=True,
            include_supervisor=True,
            include_manager=False,
            sms_override=False
        ),
        
        EscalationLevel.MANAGER: EscalationRule(
            level=EscalationLevel.MANAGER,
            name="Manager Escalation",
            description="Escalate to plant manager after 30 minutes",
            notify_channels=["email", "whatsapp"],
            include_mechanic=True,
            include_supervisor=True,
            include_manager=True,
            sms_override=False
        ),
        
        EscalationLevel.FULL: EscalationRule(
            level=EscalationLevel.FULL,
            name="Full Escalation",
            description="All stakeholders + SMS override after 45 minutes",
            notify_channels=["email", "whatsapp", "sms"],
            include_mechanic=True,
            include_supervisor=True,
            include_manager=True,
            sms_override=True
        )
    }
    
    def __init__(self, rules: Dict[EscalationLevel, EscalationRule] = None):
        self.rules = rules or self.DEFAULT_RULES.copy()
    
    def get_rule(self, level: EscalationLevel) -> Optional[EscalationRule]:
        """Get rule for a specific escalation level."""
        return self.rules.get(level)
    
    def get_recipients(
        self,
        level: EscalationLevel,
        assigned_mechanic: Dict = None,
        supervisor: Dict = None,
        manager: Dict = None
    ) -> List[Dict]:
        """
        Get list of recipients for an escalation level.
        
        Returns list of dicts with:
        - id
        - name
        - email
        - phone
        - whatsapp_number
        - channels
        """
        rule = self.get_rule(level)
        if not rule:
            return []
        
        recipients = []
        
        if rule.include_mechanic and assigned_mechanic:
            recipients.append({
                **assigned_mechanic,
                "role": "mechanic",
                "channels": rule.notify_channels,
                "priority": 1
            })
        
        if rule.include_supervisor and supervisor:
            recipients.append({
                **supervisor,
                "role": "supervisor",
                "channels": rule.notify_channels,
                "priority": 2
            })
        
        if rule.include_manager and manager:
            recipients.append({
                **manager,
                "role": "manager",
                "channels": rule.notify_channels,
                "priority": 3
            })
        
        # Add SMS if override enabled
        if rule.sms_override:
            for recipient in recipients:
                if "sms" not in recipient["channels"]:
                    recipient["channels"].append("sms")
        
        return recipients
    
    def get_notification_message(
        self,
        level: EscalationLevel,
        alert_data: Dict,
        is_escalation: bool = False
    ) -> str:
        """Get appropriate message for escalation level."""
        
        if level == EscalationLevel.MECHANIC:
            return f"New alert: {alert_data.get('failure_type', 'Unknown failure')}"
        
        if is_escalation:
            prefixes = {
                EscalationLevel.SUPERVISOR: "⚠️ ESCALATED (15min): ",
                EscalationLevel.MANAGER: "🔥 ESCALATED (30min): ",
                EscalationLevel.FULL: "🚨 FULL ESCALATION (45min): "
            }
            prefix = prefixes.get(level, "ESCALATED: ")
            return prefix + alert_data.get('failure_type', 'Unknown failure')
        
        return alert_data.get('failure_type', 'Unknown failure')
    
    def customize_rule(
        self,
        level: EscalationLevel,
        notify_channels: List[str] = None,
        include_mechanic: bool = None,
        include_supervisor: bool = None,
        include_manager: bool = None,
        sms_override: bool = None
    ):
        """Customize a rule for specific deployment needs."""
        if level not in self.rules:
            return
        
        rule = self.rules[level]
        
        if notify_channels is not None:
            rule.notify_channels = notify_channels
        if include_mechanic is not None:
            rule.include_mechanic = include_mechanic
        if include_supervisor is not None:
            rule.include_supervisor = include_supervisor
        if include_manager is not None:
            rule.include_manager = include_manager
        if sms_override is not None:
            rule.sms_override = sms_override


# Global rules instance
escalation_rules = EscalationRules()
