"""
Notification Manager for SENTINEL AI.
Orchestrates email, WhatsApp, and SMS notifications.
"""

from typing import Dict, List, Optional, Callable
from datetime import datetime
import asyncio

from notifications.gmail_client import GmailClient, gmail_client
from notifications.twilio_client import TwilioClient, twilio_client
from database import get_db
from models import NotificationLog, Mechanic, Machine


class NotificationManager:
    """
    Manages all notification channels:
    - Email (Gmail SMTP)
    - WhatsApp (Twilio)
    - SMS (Twilio)
    
    Logs all notifications to database for tracking.
    """
    
    def __init__(self):
        self.gmail = gmail_client
        self.twilio = twilio_client
        
        # Callbacks
        self.on_notification_sent: Optional[Callable] = None
        self.on_notification_failed: Optional[Callable] = None
    
    async def send_alert_notification(
        self,
        alert_data: Dict,
        machine_info: Dict,
        mechanic_info: Dict,
        channels: List[str] = None
    ) -> Dict:
        """
        Send alert notification through specified channels.
        
        Args:
            alert_data: Alert/diagnosis information
            machine_info: Machine details
            mechanic_info: Mechanic contact details
            channels: List of channels ['email', 'whatsapp', 'sms'] or None for all
        
        Returns:
            Dict with results for each channel
        """
        if channels is None:
            channels = ['email', 'whatsapp']
        
        results = {}
        
        # Email notification
        if 'email' in channels and mechanic_info.get('email'):
            results['email'] = await self._send_email(
                alert_data, machine_info, mechanic_info
            )
        
        # WhatsApp notification
        if 'whatsapp' in channels and mechanic_info.get('whatsapp_number'):
            results['whatsapp'] = await self._send_whatsapp(
                alert_data, machine_info, mechanic_info
            )
        
        # SMS notification
        if 'sms' in channels and mechanic_info.get('phone'):
            results['sms'] = await self._send_sms(
                alert_data, machine_info, mechanic_info
            )
        
        return results
    
    async def _send_email(
        self,
        alert_data: Dict,
        machine_info: Dict,
        mechanic_info: Dict
    ) -> Dict:
        """Send email notification."""
        result = await self.gmail.send_alert(
            to_email=mechanic_info['email'],
            alert_data=alert_data,
            machine_info=machine_info
        )
        
        # Log to database
        await self._log_notification(
            alert_id=alert_data.get('alert_id'),
            machine_id=machine_info.get('machine_id'),
            mechanic_id=mechanic_info.get('id'),
            channel='email',
            recipient=mechanic_info['email'],
            subject=f"ALERT: {alert_data.get('failure_type', 'Unknown')}",
            status='sent' if result['success'] else 'failed',
            error=result.get('error'),
            message_id=result.get('message_id')
        )
        
        # Trigger callback
        if result['success'] and self.on_notification_sent:
            await self.on_notification_sent('email', result)
        elif not result['success'] and self.on_notification_failed:
            await self.on_notification_failed('email', result)
        
        return result
    
    async def _send_whatsapp(
        self,
        alert_data: Dict,
        machine_info: Dict,
        mechanic_info: Dict
    ) -> Dict:
        """Send WhatsApp notification."""
        result = await self.twilio.send_whatsapp(
            to_number=mechanic_info['whatsapp_number'],
            alert_data=alert_data,
            machine_info=machine_info
        )
        
        # Log to database
        await self._log_notification(
            alert_id=alert_data.get('alert_id'),
            machine_id=machine_info.get('machine_id'),
            mechanic_id=mechanic_info.get('id'),
            channel='whatsapp',
            recipient=mechanic_info['whatsapp_number'],
            subject=f"ALERT: {alert_data.get('failure_type', 'Unknown')}",
            status='sent' if result['success'] else 'failed',
            error=result.get('error'),
            message_id=result.get('message_id')
        )
        
        # Trigger callback
        if result['success'] and self.on_notification_sent:
            await self.on_notification_sent('whatsapp', result)
        elif not result['success'] and self.on_notification_failed:
            await self.on_notification_failed('whatsapp', result)
        
        return result
    
    async def _send_sms(
        self,
        alert_data: Dict,
        machine_info: Dict,
        mechanic_info: Dict
    ) -> Dict:
        """Send SMS notification."""
        result = await self.twilio.send_sms(
            to_number=mechanic_info['phone'],
            alert_data=alert_data,
            machine_info=machine_info
        )
        
        # Log to database
        await self._log_notification(
            alert_id=alert_data.get('alert_id'),
            machine_id=machine_info.get('machine_id'),
            mechanic_id=mechanic_info.get('id'),
            channel='sms',
            recipient=mechanic_info['phone'],
            subject=f"ALERT: {alert_data.get('failure_type', 'Unknown')}",
            status='sent' if result['success'] else 'failed',
            error=result.get('error'),
            message_id=result.get('message_id')
        )
        
        return result
    
    async def _log_notification(
        self,
        alert_id: str,
        machine_id: str,
        mechanic_id: Optional[int],
        channel: str,
        recipient: str,
        subject: str,
        status: str,
        error: Optional[str] = None,
        message_id: Optional[str] = None
    ):
        """Log notification to database."""
        try:
            db = next(get_db())
            log = NotificationLog(
                alert_id=alert_id,
                machine_id=machine_id,
                mechanic_id=mechanic_id,
                channel=channel,
                recipient_address=recipient,
                subject=subject,
                message_body=subject,  # Simplified
                status=status,
                sent_at=datetime.utcnow() if status == 'sent' else None,
                error_message=error,
                message_id=message_id
            )
            db.add(log)
            db.commit()
        except Exception as e:
            print(f"Failed to log notification: {e}")
    
    def get_channel_status(self) -> Dict:
        """Get status of all notification channels."""
        return {
            "email": {
                "configured": self.gmail.is_configured(),
                "from": self.gmail.from_email if self.gmail.is_configured() else None
            },
            "whatsapp": {
                "configured": self.twilio.is_configured(),
                "from": self.twilio.from_number if self.twilio.is_configured() else None,
                "sandbox_mode": True  # Always true for free tier
            },
            "sms": {
                "configured": self.twilio.is_configured(),
                "from": self.twilio.from_number if self.twilio.is_configured() else None
            }
        }
    
    def set_callbacks(
        self,
        on_notification_sent: Optional[Callable] = None,
        on_notification_failed: Optional[Callable] = None
    ):
        """Set callback functions."""
        self.on_notification_sent = on_notification_sent
        self.on_notification_failed = on_notification_failed


# Global notification manager instance
notification_manager = NotificationManager()
