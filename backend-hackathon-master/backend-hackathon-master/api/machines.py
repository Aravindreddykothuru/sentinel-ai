"""
Machine API Routes for SENTINEL AI.
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Machine, SensorReading
from seed import thresholds_from_normal_ranges
from services.scheduled_grok_generator import scheduled_grok_generator

router = APIRouter(prefix="/machines", tags=["machines"])

MACHINE_COLUMNS = {c.name for c in Machine.__table__.columns} - {"id", "created_at", "updated_at"}


def _latest_reading(db: Session, machine: Machine) -> Optional[SensorReading]:
    return db.query(SensorReading).filter(
        SensorReading.machine_id == machine.id
    ).order_by(SensorReading.timestamp.desc()).first()


def _serialize_machine(db: Session, machine: Machine) -> dict:
    data = {c.name: getattr(machine, c.name) for c in Machine.__table__.columns}
    latest = _latest_reading(db, machine)
    data["latest_reading"] = {
        "timestamp": latest.timestamp,
        "sensor_values": latest.sensor_values,
        "tier_label": latest.tier_label,
        "health_score": latest.health_score,
        "failure_probability": latest.failure_probability
    } if latest else None
    return data


@router.get("/")
def list_machines(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all machines with optional filtering."""
    query = db.query(Machine)
    
    if status:
        query = query.filter(Machine.status == status)
    
    machines = query.offset(skip).limit(limit).all()
    return {
        "machines": [_serialize_machine(db, m) for m in machines],
        "count": len(machines),
        "total": db.query(Machine).count()
    }


@router.get("/{machine_id}")
def get_machine(machine_id: str, db: Session = Depends(get_db)):
    """Get a specific machine by ID."""
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    return _serialize_machine(db, machine)


@router.post("/")
def create_machine(machine_data: dict, db: Session = Depends(get_db)):
    """Create a new machine. Unknown fields are ignored; thresholds default from the normal ranges."""
    data = {k: v for k, v in machine_data.items() if k in MACHINE_COLUMNS}
    if not data.get("name") or not data.get("type"):
        raise HTTPException(status_code=422, detail="Fields 'name' and 'type' are required")
    
    data.setdefault("machine_id", f"M-{uuid.uuid4().hex[:8].upper()}")
    if db.query(Machine).filter(Machine.machine_id == data["machine_id"]).first():
        raise HTTPException(status_code=409, detail="Machine ID already exists")
    
    # Store normal ranges as {low, high} whichever form the client sent
    if data.get("normal_ranges"):
        data["normal_ranges"] = {
            sensor: {"low": r.get("low", r.get("min")), "high": r.get("high", r.get("max"))}
            for sensor, r in data["normal_ranges"].items()
        }
        data.setdefault("thresholds", thresholds_from_normal_ranges(data["normal_ranges"]))
    
    machine = Machine(**data)
    db.add(machine)
    db.commit()
    db.refresh(machine)
    return _serialize_machine(db, machine)


@router.get("/{machine_id}/readings")
def get_machine_readings(
    machine_id: str,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get recent sensor readings for a machine."""
    # SensorReading.machine_id references Machine.id (integer), not the public machine_id
    readings = db.query(SensorReading).join(Machine).filter(
        Machine.machine_id == machine_id
    ).order_by(SensorReading.timestamp.desc()).limit(limit).all()
    
    return {
        "machine_id": machine_id,
        "readings": readings,
        "count": len(readings)
    }


@router.get("/{machine_id}/health")
def get_machine_health(machine_id: str, db: Session = Depends(get_db)):
    """Get machine health status."""
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    # Get latest reading
    latest = _latest_reading(db, machine)
    
    return {
        "machine_id": machine_id,
        "status": machine.status,
        "health_score": latest.health_score if latest else None,
        "current_tier": latest.current_tier if latest else 1,
        "last_updated": latest.timestamp.isoformat() if latest else None
    }


@router.post("/{machine_id}/generate")
async def trigger_generation(machine_id: str, db: Session = Depends(get_db)):
    """Trigger immediate Grok data generation for a specific machine."""
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    await scheduled_grok_generator.trigger_immediate(machine_id)
    return {
        "message": f"Data generation triggered for {machine.name}",
        "machine_id": machine_id
    }


@router.get("/scheduler/status")
def get_scheduler_status():
    """Get Grok scheduler status."""
    return scheduled_grok_generator.get_status()


@router.post("/scheduler/toggle")
async def toggle_scheduler():
    """Enable or disable the scheduled Grok generator."""
    if scheduled_grok_generator.running:
        await scheduled_grok_generator.stop()
        return {"status": "stopped", "message": "Scheduler disabled"}
    else:
        await scheduled_grok_generator.start()
        return {"status": "running", "message": "Scheduler enabled"}
