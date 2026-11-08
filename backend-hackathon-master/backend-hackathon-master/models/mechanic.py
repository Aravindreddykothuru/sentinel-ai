from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Mechanic(Base):
    __tablename__ = "mechanics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String)  # For SMS
    whatsapp_number = Column(String)  # For WhatsApp
    
    # Role and availability
    role = Column(String, default="mechanic")  # mechanic, supervisor, manager
    is_available = Column(Boolean, default=True)
    
    # Notification preferences
    email_enabled = Column(Boolean, default=True)
    sms_enabled = Column(Boolean, default=False)
    whatsapp_enabled = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    assigned_machines = relationship("Machine", back_populates="assigned_mechanic")
    alerts_responded = relationship("Alert", back_populates="responded_by")
