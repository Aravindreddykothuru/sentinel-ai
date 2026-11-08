"""
Twilio WhatsApp/SMS Client for SENTINEL AI.
Sends urgent WhatsApp messages for critical alerts.
"""

from typing import Dict, Optional, List
from datetime import datetime

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from config import get_settings

settings = get_settings()


class TwilioClient:
    """
    Twilio client for WhatsApp and SMS notifications.
    Uses Twilio's WhatsApp Sandbox (free for testing).
    """
    
    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_PHONE_NUMBER
        
        self.client = None
        if self.is_configured():
            self.client = Client(self.account_sid, self.auth_token)
    
    def is_configured(self) -> bool:
        """Check if Twilio is properly configured."""
        return all([self.account_sid, self.auth_token, self.from_number])
    
    def _format_whatsapp_number(self, number: str) -> str:
        """Format number for WhatsApp (add whatsapp: prefix)."""
        if not number.startswith('whatsapp:'):
            # Ensure number has country code
            if not number.startswith('+'):
                number = '+' + number
            return f"whatsapp:{number}"
        return number
    
    def _format_sms_number(self, number: str) -> str:
        """Format number for SMS."""
        if number.startswith('whatsapp:'):
            return number.replace('whatsapp:', '')
        if not number.startswith('+'):
            number = '+' + number
        return number
    
    async def send_whatsapp(
        self,
        to_number: str,
        alert_data: Dict,
        machine_info: Dict
    ) -> Dict:
        """
        Send WhatsApp message alert.
        
        Note: In sandbox mode, recipient must have joined the sandbox first
        by messaging the sandbox number.
        """
        if not self.is_configured() or not self.client:
            return {
                "success": False,
                "error": "Twilio not configured. Check TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER"
            }
        
        try:
            # Format message
            message_body = self._format_whatsapp_message(alert_data, machine_info)
            
            # Send message
            from_whatsapp = self._format_whatsapp_number(self.from_number)
            to_whatsapp = self._format_whatsapp_number(to_number)
            
            message = self.client.messages.create(
                from_=from_whatsapp,
                body=message_body,
                to=to_whatsapp
            )
            
            return {
                "success": True,
                "message_id": message.sid,
                "to": to_number,
                "status": message.status,
                "channel": "whatsapp"
            }
            
        except TwilioRestException as e:
            return {
                "success": False,
                "error": f"Twilio error: {e.msg}",
                "code": e.code
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_sms(
        self,
        to_number: str,
        alert_data: Dict,
        machine_info: Dict
    ) -> Dict:
        """Send SMS message alert."""
        if not self.is_configured() or not self.client:
            return {
                "success": False,
                "error": "Twilio not configured"
            }
        
        try:
            # Format message (shorter for SMS)
            message_body = self._format_sms_message(alert_data, machine_info)
            
            # Send message
            to_sms = self._format_sms_number(to_number)
            from_sms = self._format_sms_number(self.from_number)
            
            message = self.client.messages.create(
                from_=from_sms,
                body=message_body,
                to=to_sms
            )
            
            return {
                "success": True,
                "message_id": message.sid,
                "to": to_number,
                "status": message.status,
                "channel": "sms"
            }
            
        except TwilioRestException as e:
            return {
                "success": False,
                "error": f"Twilio error: {e.msg}",
                "code": e.code
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_whatsapp_message(self, alert_data: Dict, machine_info: Dict) -> str:
        """Format WhatsApp message with emoji and formatting."""
        severity_emoji = "🚨" if alert_data.get('severity') == 'CRITICAL' else "⚠️"
        
        # Get sensor snapshot for actionable data
        sensors = alert_data.get('sensor_snapshot', {})
        temp = sensors.get('temperature', 'N/A')
        vibration = sensors.get('vibration', 'N/A')
        rpm = sensors.get('rpm', 'N/A')
        pressure = sensors.get('pressure', 'N/A')
        
        # Get recommended action
        action = alert_data.get('recommended_action') or alert_data.get('action', 'Investigate sensor anomalies immediately')
        
        return f"""{severity_emoji} *SENTINEL AI ALERT* {severity_emoji}

*Machine:* {machine_info.get('name', 'Unknown')} ({machine_info.get('machine_id', 'Unknown')})
*Location:* {machine_info.get('location', 'Unknown')}

*Failure Type:* {alert_data.get('failure_type', 'Anomaly Detected')}
*Confidence:* {alert_data.get('confidence', 0)}%
*Severity:* {alert_data.get('severity', 'WARNING')}
*Time to Breach:* {alert_data.get('time_to_breach', 'Immediate attention required')}

*Sensor Readings:*
• Temperature: {temp}°C
• Vibration: {vibration} mm/s
• RPM: {rpm}
• Pressure: {pressure} bar

*RECOMMENDED ACTION:*
{action}

⚠️ Please acknowledge and take immediate action.

Alert ID: {alert_data.get('alert_id', 'Unknown')}
Time: {datetime.utcnow().strftime('%H:%M:%S UTC')}
"""
    
    def _format_sms_message(self, alert_data: Dict, machine_info: Dict) -> str:
        """Format SMS message (shorter, no emoji)."""
        return f"""SENTINEL AI ALERT
{machine_info.get('name', 'Unknown')}: {alert_data.get('failure_type', 'Unknown')}
Confidence: {alert_data.get('confidence', 0)}%
Time: {alert_data.get('time_to_breach', 'Unknown')}
Action: {alert_data.get('action', 'Check dashboard')[:50]}...
http://localhost:5173
"""
    
    async def send_alert_multi_channel(
        self,
        to_number: str,
        alert_data: Dict,
        machine_info: Dict,
        channels: List[str] = None
    ) -> Dict:
        """
        Send alert via multiple channels.
        
        Args:
            to_number: Phone number
            alert_data: Alert information
            machine_info: Machine details
            channels: List of channels ['whatsapp', 'sms'] or None for both
        
        Returns:
            Dict with results for each channel
        """
        if channels is None:
            channels = ['whatsapp', 'sms']
        
        results = {}
        
        if 'whatsapp' in channels:
            results['whatsapp'] = await self.send_whatsapp(
                to_number, alert_data, machine_info
            )
        
        if 'sms' in channels:
            results['sms'] = await self.send_sms(
                to_number, alert_data, machine_info
            )
        
        return results
    
    def get_sandbox_instructions(self) -> str:
        """Get instructions for joining WhatsApp sandbox."""
        return """
To receive WhatsApp alerts, you must join the Twilio WhatsApp Sandbox:

1. Save this number in your contacts: +1 415 523 8886
2. Send this exact message to that number:
   join <your-sandbox-code>

Your sandbox code is shown in your Twilio Console under
Messaging → Try it out → Send a WhatsApp message

Once joined, you will receive alert messages from SENTINEL AI.
"""


# Global client instance
twilio_client = TwilioClient()
