"""
Auto-Discovery API Routes for SENTINEL AI.
Automatic sensor detection and threshold tuning.
"""

from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Machine, SensorReading
from services.auto_discovery import auto_discovery_service

router = APIRouter(prefix="/discovery", tags=["discovery"])


@router.post("/analyze-sensors/{machine_id}")
async def analyze_machine_sensors(
    machine_id: str,
    sample_size: int = 100,
    db: Session = Depends(get_db)
):
    """
    Analyze sensors for a machine and generate profiles.
    
    Fetches historical readings and creates sensor profiles
    with detected types, ranges, and stability scores.
    """
    # Get machine
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    # Get recent readings
    readings = db.query(SensorReading).filter(
        SensorReading.machine_id == machine_id
    ).order_by(SensorReading.timestamp.desc()).limit(sample_size).all()
    
    if not readings:
        raise HTTPException(
            status_code=400,
            detail=f"No readings found for machine {machine_id}"
        )
    
    # Convert to data samples
    data_samples = []
    for reading in readings:
        sample = {
            "timestamp": reading.timestamp.isoformat(),
            **reading.sensor_values
        }
        data_samples.append(sample)
    
    # Discover sensors
    profiles = auto_discovery_service.discover_sensors_from_data(data_samples)
    
    return {
        "machine_id": machine_id,
        "sample_size": len(data_samples),
        "sensors_discovered": len(profiles),
        "profiles": [
            {
                "name": p.name,
                "type": p.sensor_type,
                "unit": p.unit,
                "data_range": p.data_range,
                "normal_range": p.normal_range,
                "stability_score": round(p.stability_score, 2),
                "anomaly_rate": round(p.anomaly_rate, 2)
            }
            for p in profiles
        ]
    }


@router.post("/recommend-thresholds/{machine_id}")
async def recommend_thresholds(
    machine_id: str,
    history_days: int = 7,
    db: Session = Depends(get_db)
):
    """
    Get threshold recommendations for all sensors on a machine.
    
    Analyzes historical data to recommend optimized thresholds
    that minimize false positives while maintaining sensitivity.
    """
    # Get machine
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    # Get readings from last N days
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(days=history_days)
    
    readings = db.query(SensorReading).filter(
        SensorReading.machine_id == machine_id,
        SensorReading.timestamp >= cutoff
    ).all()
    
    if not readings:
        raise HTTPException(
            status_code=400,
            detail=f"No readings found in last {history_days} days"
        )
    
    # Organize by sensor
    sensor_history: Dict[str, List[float]] = {}
    for reading in readings:
        for sensor_name, value in reading.sensor_values.items():
            if sensor_name not in sensor_history:
                sensor_history[sensor_name] = []
            if isinstance(value, (int, float)):
                sensor_history[sensor_name].append(float(value))
    
    # Get current thresholds
    current_thresholds = machine.thresholds or {}
    
    # Auto-tune
    result = auto_discovery_service.auto_tune_machine(
        machine_id=machine_id,
        readings_history=sensor_history,
        current_thresholds=current_thresholds
    )
    
    return result


@router.post("/apply-thresholds/{machine_id}")
async def apply_recommended_thresholds(
    machine_id: str,
    sensor_selection: Optional[List[str]] = None,
    db: Session = Depends(get_db)
):
    """
    Apply recommended thresholds to a machine.
    
    Only applies high-confidence recommendations by default.
    """
    # Get machine
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    # Get recommendations first
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(days=7)
    
    readings = db.query(SensorReading).filter(
        SensorReading.machine_id == machine_id,
        SensorReading.timestamp >= cutoff
    ).all()
    
    sensor_history: Dict[str, List[float]] = {}
    for reading in readings:
        for sensor_name, value in reading.sensor_values.items():
            if sensor_name not in sensor_history:
                sensor_history[sensor_name] = []
            if isinstance(value, (int, float)):
                sensor_history[sensor_name].append(float(value))
    
    current_thresholds = machine.thresholds or {}
    
    tuning_result = auto_discovery_service.auto_tune_machine(
        machine_id=machine_id,
        readings_history=sensor_history,
        current_thresholds=current_thresholds
    )
    
    # Apply high-confidence recommendations
    applied = []
    failed = []
    
    new_thresholds = dict(current_thresholds)
    
    for rec in tuning_result["recommendations"]:
        sensor = rec["sensor"]
        
        # Skip if not in selection
        if sensor_selection and sensor not in sensor_selection:
            continue
        
        # Only apply high confidence recommendations
        if rec["confidence"] >= 0.7:
            new_thresholds[sensor] = rec["recommended"]
            applied.append({
                "sensor": sensor,
                "previous": rec["current"],
                "new": rec["recommended"],
                "confidence": rec["confidence"]
            })
        else:
            failed.append({
                "sensor": sensor,
                "reason": f"Low confidence ({rec['confidence']:.2f})",
                "recommendation": rec["recommended"]
            })
    
    # Update machine
    machine.thresholds = new_thresholds
    db.commit()
    
    return {
        "machine_id": machine_id,
        "applied_count": len(applied),
        "skipped_count": len(failed),
        "applied": applied,
        "skipped": failed
    }


@router.get("/sensor-health/{machine_id}")
async def check_sensor_health(
    machine_id: str,
    sample_size: int = 50,
    db: Session = Depends(get_db)
):
    """
    Check health status of all sensors on a machine.
    
    Identifies stuck sensors, excessive noise, missing data, etc.
    """
    # Get machine
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    # Get recent readings
    readings = db.query(SensorReading).filter(
        SensorReading.machine_id == machine_id
    ).order_by(SensorReading.timestamp.desc()).limit(sample_size).all()
    
    if not readings:
        raise HTTPException(
            status_code=400,
            detail=f"No readings found for machine {machine_id}"
        )
    
    # Organize by sensor
    sensor_readings: Dict[str, List[float]] = {}
    for reading in readings:
        for sensor_name, value in reading.sensor_values.items():
            if sensor_name not in sensor_readings:
                sensor_readings[sensor_name] = []
            if isinstance(value, (int, float)):
                sensor_readings[sensor_name].append(float(value))
    
    # Check health for each sensor
    health_reports = []
    for sensor_name, values in sensor_readings.items():
        report = auto_discovery_service.validate_sensor_health(sensor_name, values)
        health_reports.append(report)
    
    healthy_count = sum(1 for r in health_reports if r["healthy"])
    
    return {
        "machine_id": machine_id,
        "total_sensors": len(health_reports),
        "healthy_sensors": healthy_count,
        "unhealthy_sensors": len(health_reports) - healthy_count,
        "sensors": health_reports
    }


@router.post("/detect-new-sensors/{machine_id}")
async def detect_new_sensors(
    machine_id: str,
    current_reading: Dict[str, float],
    db: Session = Depends(get_db)
):
    """
    Detect any new sensors that have appeared.
    
    Compares current reading against known sensors for the machine.
    """
    # Get machine
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    # Get known sensors
    known_sensors = machine.sensors or []
    
    # Detect new sensors
    new_sensors = auto_discovery_service.detect_new_sensors(
        machine_id=machine_id,
        previous_sensors=known_sensors,
        current_reading=current_reading
    )
    
    return {
        "machine_id": machine_id,
        "known_sensors": known_sensors,
        "current_sensors": list(current_reading.keys()),
        "new_sensors_detected": new_sensors,
        "has_new_sensors": len(new_sensors) > 0
    }
