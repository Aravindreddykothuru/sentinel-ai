"""
Maintenance Scheduling API Routes for SENTINEL AI.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid

from database import get_db
from models import MaintenanceSchedule, Machine, Alert, Mechanic
from ai.gemini_client import gemini_client
from services.window_calculator import window_calculator

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


@router.post("/schedule/{alert_id}")
async def create_maintenance_schedule(
    alert_id: str,
    mechanic_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Create AI-recommended maintenance schedule for an alert."""
    
    # Get alert and machine
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    machine = db.query(Machine).filter(Machine.machine_id == alert.machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    # Check if schedule already exists
    existing = db.query(MaintenanceSchedule).filter(
        MaintenanceSchedule.alert_id == alert_id
    ).first()
    
    if existing:
        return {"success": True, "schedule": existing, "message": "Schedule already exists"}
    
    # Get maintenance recommendation from Gemini
    recommendation = await gemini_client.recommend_maintenance_window(
        machine_id=machine.machine_id,
        machine_type=machine.type,
        time_to_failure=alert.time_to_breach,
        shift_schedule=machine.production_schedule or {}
    )
    
    # Parse recommended times
    recommended_start = datetime.fromisoformat(recommendation["recommended_start"].replace('Z', '+00:00'))
    recommended_end = datetime.fromisoformat(recommendation["recommended_end"].replace('Z', '+00:00'))
    
    # Create schedule
    schedule = MaintenanceSchedule(
        schedule_id=f"SCH-{uuid.uuid4().hex[:8].upper()}",
        machine_id=machine.machine_id,
        alert_id=alert_id,
        status="proposed",
        recommended_start=recommended_start,
        recommended_end=recommended_end,
        duration_hours=recommendation["duration_hours"],
        reasoning=recommendation.get("reasoning", ""),
        confidence_score=recommendation.get("confidence_score", 80),
        factors=recommendation.get("factors", {}),
        production_impact=recommendation.get("production_impact", "MEDIUM"),
        estimated_downtime_cost=recommendation.get("estimated_downtime_cost", 0),
        maintenance_type=recommendation.get("maintenance_type", "corrective"),
        required_parts=recommendation.get("required_parts", []),
        required_tools=recommendation.get("required_tools", []),
        estimated_labor_hours=recommendation.get("estimated_labor_hours", 2.0),
        assigned_mechanic_id=mechanic_id or machine.assigned_mechanic_id
    )
    
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    
    return {
        "success": True,
        "schedule": {
            "schedule_id": schedule.schedule_id,
            "machine_id": schedule.machine_id,
            "alert_id": schedule.alert_id,
            "recommended_start": schedule.recommended_start.isoformat(),
            "recommended_end": schedule.recommended_end.isoformat(),
            "duration_hours": schedule.duration_hours,
            "production_impact": schedule.production_impact,
            "confidence_score": schedule.confidence_score,
            "reasoning": schedule.reasoning
        }
    }


@router.get("/schedules")
def list_schedules(
    machine_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all maintenance schedules with optional filtering."""
    query = db.query(MaintenanceSchedule)
    
    if machine_id:
        query = query.filter(MaintenanceSchedule.machine_id == machine_id)
    if status:
        query = query.filter(MaintenanceSchedule.status == status)
    
    schedules = query.order_by(MaintenanceSchedule.recommended_start).all()
    
    return {
        "schedules": schedules,
        "count": len(schedules)
    }


@router.get("/schedules/{schedule_id}")
def get_schedule(schedule_id: str, db: Session = Depends(get_db)):
    """Get a specific maintenance schedule."""
    schedule = db.query(MaintenanceSchedule).filter(
        MaintenanceSchedule.schedule_id == schedule_id
    ).first()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    return schedule


@router.post("/schedules/{schedule_id}/confirm")
def confirm_schedule(
    schedule_id: str,
    confirmed_by: str,
    notes: str = "",
    db: Session = Depends(get_db)
):
    """Confirm a maintenance schedule."""
    schedule = db.query(MaintenanceSchedule).filter(
        MaintenanceSchedule.schedule_id == schedule_id
    ).first()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    if schedule.status != "proposed":
        raise HTTPException(status_code=400, detail="Schedule already processed")
    
    schedule.status = "confirmed"
    schedule.confirmed_by = confirmed_by
    schedule.confirmed_at = datetime.utcnow()
    schedule.confirmation_notes = notes
    
    db.commit()
    db.refresh(schedule)
    
    return {"success": True, "schedule": schedule}


@router.post("/schedules/{schedule_id}/complete")
def complete_schedule(
    schedule_id: str,
    actual_duration_hours: float,
    notes: str = "",
    issues: Optional[List[str]] = None,
    db: Session = Depends(get_db)
):
    """Mark a maintenance schedule as completed."""
    schedule = db.query(MaintenanceSchedule).filter(
        MaintenanceSchedule.schedule_id == schedule_id
    ).first()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    schedule.status = "completed"
    schedule.completed_at = datetime.utcnow()
    schedule.actual_duration_hours = actual_duration_hours
    schedule.completion_notes = notes
    schedule.issues_encountered = issues or []
    
    db.commit()
    db.refresh(schedule)
    
    return {"success": True, "schedule": schedule}


@router.get("/calendar")
def get_maintenance_calendar(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get maintenance calendar for date range."""
    query = db.query(MaintenanceSchedule)
    
    if start_date:
        start = datetime.fromisoformat(start_date)
        query = query.filter(MaintenanceSchedule.recommended_start >= start)
    
    if end_date:
        end = datetime.fromisoformat(end_date)
        query = query.filter(MaintenanceSchedule.recommended_start <= end)
    
    # Default to next 30 days
    if not start_date and not end_date:
        start = datetime.utcnow()
        end = start + timedelta(days=30)
        query = query.filter(
            MaintenanceSchedule.recommended_start >= start,
            MaintenanceSchedule.recommended_start <= end
        )
    
    schedules = query.order_by(MaintenanceSchedule.recommended_start).all()
    
    # Group by date
    calendar = {}
    for sch in schedules:
        date_key = sch.recommended_start.strftime("%Y-%m-%d")
        if date_key not in calendar:
            calendar[date_key] = []
        
        calendar[date_key].append({
            "schedule_id": sch.schedule_id,
            "machine_id": sch.machine_id,
            "start": sch.recommended_start.isoformat(),
            "end": sch.recommended_end.isoformat(),
            "status": sch.status,
            "maintenance_type": sch.maintenance_type,
            "production_impact": sch.production_impact
        })
    
    return {
        "calendar": calendar,
        "total_schedules": len(schedules)
    }


@router.post("/calculate-optimal-windows/{machine_id}")
async def calculate_optimal_windows(
    machine_id: str,
    predicted_failure_hours: float = 24,
    maintenance_duration_hours: float = 2.5,
    parts_available: bool = True,
    mechanic_available: bool = True,
    db: Session = Depends(get_db)
):
    """
    Calculate optimal maintenance windows using advanced multi-factor analysis.
    
    Considers:
    - Failure urgency (time to predicted failure)
    - Production impact (shift schedules)
    - Resource availability (parts, mechanics)
    - Historical success rates
    """
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    # Calculate predicted failure time
    predicted_failure = datetime.utcnow() + timedelta(hours=predicted_failure_hours)
    
    # Get existing maintenance schedules
    existing = db.query(MaintenanceSchedule).filter(
        MaintenanceSchedule.machine_id == machine_id,
        MaintenanceSchedule.status.in_(['proposed', 'confirmed'])
    ).all()
    
    existing_times = [(s.recommended_start, s.recommended_end) for s in existing]
    
    # Calculate optimal windows
    windows = window_calculator.calculate_optimal_windows(
        machine_id=machine_id,
        predicted_failure_time=predicted_failure,
        shift_schedule=machine.shift_schedule or {},
        parts_available=parts_available,
        mechanic_available=mechanic_available,
        maintenance_duration_hours=maintenance_duration_hours,
        existing_schedules=existing_times
    )
    
    # Get recommendation summary
    summary = window_calculator.get_recommendation_summary(windows)
    
    return {
        "machine_id": machine_id,
        "predicted_failure": predicted_failure.isoformat(),
        "recommendation": summary,
        "optimal_windows": [
            {
                "start": w.start_time.isoformat(),
                "end": w.end_time.isoformat(),
                "overall_score": w.overall_score,
                "urgency_score": w.urgency_score,
                "production_score": w.production_score,
                "availability_score": w.availability_score,
                "confidence": w.confidence,
                "reasoning": w.reasoning
            }
            for w in windows
        ]
    }


@router.get("/stats/optimization")
def get_optimization_stats(db: Session = Depends(get_db)):
    """Get maintenance optimization statistics."""
    
    # Total schedules
    total = db.query(MaintenanceSchedule).count()
    proposed = db.query(MaintenanceSchedule).filter(MaintenanceSchedule.status == "proposed").count()
    confirmed = db.query(MaintenanceSchedule).filter(MaintenanceSchedule.status == "confirmed").count()
    completed = db.query(MaintenanceSchedule).filter(MaintenanceSchedule.status == "completed").count()
    
    # Production impact
    low_impact = db.query(MaintenanceSchedule).filter(
        MaintenanceSchedule.production_impact == "LOW"
    ).count()
    
    # Average confidence score
    from sqlalchemy import func
    avg_confidence = db.query(func.avg(MaintenanceSchedule.confidence_score)).scalar() or 0
    
    # Estimated savings (completed vs emergency)
    completed_schedules = db.query(MaintenanceSchedule).filter(
        MaintenanceSchedule.status == "completed"
    ).all()
    
    total_estimated_cost = sum(s.estimated_downtime_cost or 0 for s in completed_schedules)
    
    return {
        "total_schedules": total,
        "by_status": {
            "proposed": proposed,
            "confirmed": confirmed,
            "completed": completed
        },
        "production_impact": {
            "low_impact": low_impact,
            "low_impact_percentage": round((low_impact / total * 100), 1) if total > 0 else 0
        },
        "average_confidence": round(avg_confidence, 1),
        "estimated_cost_avoidance": total_estimated_cost * 10  # Emergency cost is ~10x planned
    }
