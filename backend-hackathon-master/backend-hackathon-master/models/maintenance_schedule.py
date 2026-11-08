"""
Maintenance Schedule Model for SENTINEL AI.
Stores AI-recommended maintenance windows.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class MaintenanceSchedule(Base):
    __tablename__ = "maintenance_schedules"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(String, unique=True, index=True, nullable=False)
    
    # Foreign keys
    machine_id = Column(String, ForeignKey("machines.machine_id"), nullable=False)
    alert_id = Column(String, ForeignKey("alerts.alert_id"), nullable=True)
    
    # Schedule status
    status = Column(String, default="proposed")  # proposed, confirmed, completed, cancelled
    
    # Gemini AI recommendations
    recommended_start = Column(DateTime, nullable=False)
    recommended_end = Column(DateTime, nullable=False)
    duration_hours = Column(Float, nullable=False)
    
    # Reasoning
    reasoning = Column(Text)  # Why this window was chosen
    confidence_score = Column(Float)  # 0-100
    
    # Factors considered
    factors = Column(JSON)  # {
    #   "production_impact": "LOW",
    #   "failure_urgency": "HIGH", 
    #   "parts_availability": "AVAILABLE",
    #   "mechanic_availability": True,
    #   "optimal_conditions": ["low_demand", "weekend", "cooling_period"]
    # }
    
    # Production schedule integration
    production_impact = Column(String)  # LOW, MEDIUM, HIGH
    affected_shifts = Column(JSON)  # ["morning", "evening"]
    estimated_downtime_cost = Column(Float)  # Cost per hour of downtime
    
    # Maintenance details
    maintenance_type = Column(String)  # preventive, corrective, emergency
    required_parts = Column(JSON)  # ["bearing_123", "oil_seal_456"]
    required_tools = Column(JSON)  # ["torque_wrench", "hydraulic_lift"]
    estimated_labor_hours = Column(Float)
    
    # Personnel
    assigned_mechanic_id = Column(Integer, ForeignKey("mechanics.id"), nullable=True)
    backup_mechanic_id = Column(Integer, ForeignKey("mechanics.id"), nullable=True)
    
    # Confirmation
    confirmed_by = Column(String)  # User who confirmed
    confirmed_at = Column(DateTime)
    confirmation_notes = Column(Text)
    
    # Completion tracking
    completed_at = Column(DateTime)
    actual_duration_hours = Column(Float)
    completion_notes = Column(Text)
    issues_encountered = Column(JSON)
    
    # Rescheduling
    rescheduled_from = Column(String, ForeignKey("maintenance_schedules.schedule_id"), nullable=True)
    reschedule_reason = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    machine = relationship("Machine", back_populates="maintenance_schedules")
    alert = relationship("Alert", back_populates="maintenance_schedule")
    assigned_mechanic = relationship("Mechanic", foreign_keys=[assigned_mechanic_id])
    backup_mechanic = relationship("Mechanic", foreign_keys=[backup_mechanic_id])
