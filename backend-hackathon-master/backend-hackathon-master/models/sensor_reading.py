from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=False, index=True)
    
    # Flexible sensor storage - supports any sensor configuration
    sensor_values = Column(JSON, nullable=False, default={})
    
    # Data source tracking
    data_source = Column(String, default="local")  # "grok" or "local"
    reading_number = Column(Integer, default=0)
    degradation_factor = Column(Float, default=1.0)
    
    # Tier information at time of reading
    tier_level = Column(Integer, default=1)  # 1=Normal, 2=Trending, 3=Critical
    tier_label = Column(String, default="NORMAL")
    consecutive_rises = Column(Integer, default=0)
    rising_metric = Column(String, nullable=True)
    
    # Calculated values
    health_score = Column(Float, default=100.0)
    failure_probability = Column(Float, default=0.0)
    
    # Gemini diagnosis (if triggered)
    gemini_diagnosis = Column(JSON, nullable=True)
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    machine = relationship("Machine", back_populates="sensor_readings")
    
    # Backward compatibility properties
    @property
    def temperature(self):
        return self.sensor_values.get("temperature")
    
    @property
    def vibration(self):
        return self.sensor_values.get("vibration")
    
    @property
    def rpm(self):
        return self.sensor_values.get("rpm")
    
    @property
    def pressure(self):
        return self.sensor_values.get("pressure")
