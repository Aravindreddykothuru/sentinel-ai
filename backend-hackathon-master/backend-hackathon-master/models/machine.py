from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Machine(Base):
    __tablename__ = "machines"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # gas_turbine, air_compressor, hydraulic_pump, drive_motor
    location = Column(String)
    industry_preset = Column(String)  # steel, automotive, food, oil_gas, power_plant, custom
    
    # Sensor thresholds (JSON for flexibility)
    thresholds = Column(JSON, default={
        "temperature": {"min": 0, "max": 100, "critical": 105},
        "vibration": {"min": 0, "max": 3.0, "critical": 4.5},
        "rpm": {"min": 1000, "max": 3500, "critical": 4000},
        "pressure": {"min": 70, "max": 120, "critical": 60}
    })
    
    # Normal operating ranges
    normal_ranges = Column(JSON, default={
        "temperature": {"low": 60, "high": 90},
        "vibration": {"low": 0.5, "high": 2.5},
        "rpm": {"low": 2800, "high": 3200},
        "pressure": {"low": 80, "high": 110}
    })
    
    # Shift schedule
    shift_schedule = Column(JSON, default={
        "shifts": [
            {"name": "Shift 1", "start": "06:00", "end": "14:00"},
            {"name": "Shift 2", "start": "14:00", "end": "22:00"}
        ],
        "maintenance_windows": ["13:45", "21:45"],
        "weekend_maintenance": True
    })
    
    # Current status
    health_score = Column(Float, default=100.0)
    failure_probability = Column(Float, default=0.0)
    current_tier = Column(Integer, default=1)  # 1=Normal, 2=Trending, 3=Critical
    status = Column(String, default="normal")  # normal, trending, critical, maintenance
    
    # Assigned mechanic
    assigned_mechanic_id = Column(Integer, ForeignKey("mechanics.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_reading_at = Column(DateTime, nullable=True)
    
    # Relationships
    alerts = relationship("Alert", back_populates="machine", cascade="all, delete-orphan")
    sensor_readings = relationship("SensorReading", back_populates="machine", cascade="all, delete-orphan")
    assigned_mechanic = relationship("Mechanic", back_populates="assigned_machines")
    maintenance_schedules = relationship("MaintenanceSchedule", back_populates="machine")
