from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(String, unique=True, index=True, nullable=False)
    
    # Foreign keys
    machine_id = Column(String, ForeignKey("machines.machine_id"), nullable=False)
    responded_by_id = Column(Integer, ForeignKey("mechanics.id"), nullable=True)
    
    # Alert status
    status = Column(String, default="open")  # open, acknowledged, resolved, false_alarm
    severity = Column(String, default="warning")  # warning, critical, emergency
    
    # Gemini diagnosis
    failure_type = Column(String)
    confidence = Column(Float)  # 0-100
    time_to_breach = Column(String)  # e.g., "8 minutes"
    recommended_action = Column(Text)
    
    # Sensor data at time of alert
    sensor_snapshot = Column(JSON)  # {temperature: 91.4, vibration: 4.8, ...}
    
    # Two-confirmation system
    first_confirmation_at = Column(DateTime, nullable=True)
    second_confirmation_at = Column(DateTime, nullable=True)
    confirmed = Column(Boolean, default=False)
    
    # Escalation tracking
    escalation_level = Column(Integer, default=0)  # 0=none, 1=supervisor, 2=manager, 3=full
    escalation_timer_started_at = Column(DateTime, nullable=True)
    escalated_at = Column(DateTime, nullable=True)
    
    # Mechanic response
    response = Column(String, nullable=True)  # on_my_way, false_alarm, already_fixed, need_help
    response_notes = Column(Text, nullable=True)
    responded_at = Column(DateTime, nullable=True)
    eta_minutes = Column(Integer, nullable=True)
    
    # Resolution
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    actual_failure = Column(String, nullable=True)  # For accuracy tracking
    gemini_was_correct = Column(Boolean, nullable=True)
    
    # Maintenance recommendation
    maintenance_window = Column(String, nullable=True)
    production_impact = Column(String, nullable=True)  # LOW, MEDIUM, HIGH
    estimated_savings = Column(Float, nullable=True)
    
    # Notifications sent
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime, nullable=True)
    whatsapp_sent = Column(Boolean, default=False)
    whatsapp_sent_at = Column(DateTime, nullable=True)
    sms_sent = Column(Boolean, default=False)
    sms_sent_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    machine = relationship("Machine", back_populates="alerts")
    responded_by = relationship("Mechanic", back_populates="alerts_responded")
    maintenance_schedule = relationship("MaintenanceSchedule", back_populates="alert", uselist=False)
