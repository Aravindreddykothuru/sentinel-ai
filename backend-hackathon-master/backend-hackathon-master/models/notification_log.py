from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    alert_id = Column(String, ForeignKey("alerts.alert_id"), nullable=True)
    machine_id = Column(String, ForeignKey("machines.machine_id"), nullable=False)
    mechanic_id = Column(Integer, ForeignKey("mechanics.id"), nullable=True)
    
    # Notification type
    channel = Column(String, nullable=False)  # email, whatsapp, sms
    
    # Recipient info
    recipient_address = Column(String, nullable=False)  # email or phone number
    recipient_name = Column(String)
    
    # Message content
    subject = Column(String, nullable=True)  # For email
    message_body = Column(Text)
    message_template = Column(String, nullable=True)
    
    # Status
    status = Column(String, default="pending")  # pending, sent, delivered, failed
    
    # Delivery tracking
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    
    # Retry tracking
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Error info
    error_message = Column(Text, nullable=True)
    error_code = Column(String, nullable=True)
    
    # Provider response (Twilio, SMTP, etc.)
    provider_response = Column(JSON, nullable=True)
    message_id = Column(String, nullable=True)  # Provider's message ID
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
