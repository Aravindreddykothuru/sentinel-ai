"""
Gmail SMTP Client for SENTINEL AI.
Sends HTML email alerts for critical machine failures.
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional
from datetime import datetime
from jinja2 import Template

from config import get_settings

settings = get_settings()


# HTML Email Template
EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f4f4; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { background: {{ header_color }}; color: white; padding: 20px; text-align: center; }
        .header.critical { background: #dc3545; }
        .header.warning { background: #ffc107; color: #000; }
        .content { padding: 30px; }
        .alert-badge { display: inline-block; padding: 8px 16px; border-radius: 4px; font-weight: bold; font-size: 14px; margin-bottom: 20px; }
        .alert-badge.critical { background: #dc3545; color: white; }
        .alert-badge.warning { background: #ffc107; color: #000; }
        .machine-info { background: #f8f9fa; padding: 15px; border-radius: 6px; margin-bottom: 20px; }
        .machine-info h3 { margin: 0 0 10px 0; color: #333; }
        .sensor-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 20px 0; }
        .sensor-item { background: #e9ecef; padding: 10px; border-radius: 4px; text-align: center; }
        .sensor-label { font-size: 12px; color: #666; text-transform: uppercase; }
        .sensor-value { font-size: 18px; font-weight: bold; color: #333; }
        .diagnosis { background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }
        .action-required { background: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin: 20px 0; }
        .footer { background: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666; }
        .button { display: inline-block; padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; margin-top: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header {{ severity.lower() }}">
            <h1>🚨 SENTINEL AI ALERT</h1>
            <p>Critical Machine Failure Detected</p>
        </div>
        
        <div class="content">
            <div class="alert-badge {{ severity.lower() }}">
                {{ severity }} - {{ confidence }}% Confidence
            </div>
            
            <div class="machine-info">
                <h3>{{ machine_name }} ({{ machine_id }})</h3>
                <p><strong>Type:</strong> {{ machine_type }}</p>
                <p><strong>Location:</strong> {{ location }}</p>
                <p><strong>Time:</strong> {{ timestamp }}</p>
            </div>
            
            <h3>Current Sensor Readings</h3>
            <div class="sensor-grid">
                {% for sensor, value in sensors.items() %}
                <div class="sensor-item">
                    <div class="sensor-label">{{ sensor }}</div>
                    <div class="sensor-value">{{ value }}</div>
                </div>
                {% endfor %}
            </div>
            
            <div class="diagnosis">
                <h3>🔍 AI Diagnosis</h3>
                <p><strong>Failure Type:</strong> {{ failure_type }}</p>
                <p><strong>Time to Breach:</strong> {{ time_to_breach }}</p>
                <p><strong>Root Cause:</strong> {{ root_cause }}</p>
            </div>
            
            <div class="action-required">
                <h3>⚡ Immediate Action Required</h3>
                <p>{{ action }}</p>
            </div>
            
            <div style="text-align: center;">
                <a href="{{ dashboard_url }}" class="button">View in Dashboard</a>
            </div>
        </div>
        
        <div class="footer">
            <p>SENTINEL AI - Predictive Maintenance System</p>
            <p>This alert was generated automatically based on sensor data analysis.</p>
            <p>Alert ID: {{ alert_id }}</p>
        </div>
    </div>
</body>
</html>
"""


class GmailClient:
    """
    Gmail SMTP client for sending HTML alert emails.
    """
    
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.username = settings.SMTP_USERNAME
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.ALERT_FROM_EMAIL or self.username
        self.template = Template(EMAIL_TEMPLATE)
        
    def is_configured(self) -> bool:
        """Check if Gmail is properly configured."""
        return all([self.username, self.password])
    
    async def send_alert(
        self,
        to_email: str,
        alert_data: Dict,
        machine_info: Dict
    ) -> Dict:
        """
        Send an HTML alert email.
        
        Args:
            to_email: Recipient email address
            alert_data: Alert information (diagnosis, sensors, etc.)
            machine_info: Machine details (name, type, location)
        
        Returns:
            Dict with status and message_id
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "Gmail not configured. Check SMTP_USERNAME and SMTP_PASSWORD"
            }
        
        try:
            # Build email content
            subject = f"🚨 ALERT: {alert_data['failure_type']} - {machine_info['name']}"
            
            html_content = self.template.render(
                severity=alert_data.get('severity', 'WARNING'),
                confidence=alert_data.get('confidence', 0),
                machine_name=machine_info.get('name', 'Unknown'),
                machine_id=machine_info.get('machine_id', 'Unknown'),
                machine_type=machine_info.get('type', 'Unknown'),
                location=machine_info.get('location', 'Unknown'),
                timestamp=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
                sensors=alert_data.get('sensors', {}),
                failure_type=alert_data.get('failure_type', 'Unknown'),
                time_to_breach=alert_data.get('time_to_breach', 'Unknown'),
                root_cause=alert_data.get('root_cause', 'Unknown'),
                action=alert_data.get('action', 'No action specified'),
                alert_id=alert_data.get('alert_id', 'Unknown'),
                dashboard_url=f"http://localhost:5173/machines/{machine_info.get('machine_id', '')}",
                header_color="#dc3545" if alert_data.get('severity') == 'CRITICAL' else "#ffc107"
            )
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email
            
            # Attach HTML
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
                server.sendmail(self.from_email, to_email, msg.as_string())
            
            return {
                "success": True,
                "message_id": f"gmail_{datetime.utcnow().timestamp()}",
                "to": to_email,
                "subject": subject
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_bulk_alert(
        self,
        to_emails: List[str],
        alert_data: Dict,
        machine_info: Dict
    ) -> List[Dict]:
        """Send alert to multiple recipients."""
        results = []
        for email in to_emails:
            result = await self.send_alert(email, alert_data, machine_info)
            results.append(result)
        return results


# Global client instance
gmail_client = GmailClient()
