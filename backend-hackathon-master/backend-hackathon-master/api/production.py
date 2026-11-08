"""
Production Schedule API Routes for SENTINEL AI.
Manages production schedules and calculates maintenance impact.
"""

from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json

from database import get_db
from models import Machine, MaintenanceSchedule

router = APIRouter(prefix="/production", tags=["production"])


def parse_time(time_str: str) -> int:
    """Convert HH:MM to minutes since midnight."""
    hour, minute = map(int, time_str.split(':'))
    return hour * 60 + minute


def get_shift_at_time(shifts: List[Dict], time_minutes: int) -> Optional[Dict]:
    """Determine which shift is active at a given time."""
    for shift in shifts:
        start = parse_time(shift['start'])
        end = parse_time(shift['end'])
        
        # Handle overnight shifts
        if end < start:
            if time_minutes >= start or time_minutes <= end:
                return shift
        else:
            if start <= time_minutes < end:
                return shift
    
    return None


def calculate_production_impact(
    maintenance_start: datetime,
    maintenance_end: datetime,
    shift_schedule: Dict,
    production_value_per_hour: float = 10000
) -> Dict:
    """
    Calculate production impact of a maintenance window.
    
    Returns impact metrics including:
    - affected_shifts: Which shifts are impacted
    - downtime_hours: Total production downtime
    - lost_production_value: Dollar value of lost production
    - impact_level: LOW/MEDIUM/HIGH
    - optimal: Whether this is an optimal window
    """
    shifts = shift_schedule.get('shifts', [])
    maintenance_windows = shift_schedule.get('maintenance_windows', [])
    
    if not shifts:
        return {
            "affected_shifts": [],
            "downtime_hours": 0,
            "lost_production_value": 0,
            "impact_level": "LOW",
            "optimal": True,
            "reason": "No shift schedule defined"
        }
    
    # Calculate duration
    duration = maintenance_end - maintenance_start
    duration_hours = duration.total_seconds() / 3600
    
    # Check which shifts are affected
    affected_shifts = []
    current = maintenance_start
    
    while current < maintenance_end:
        time_minutes = current.hour * 60 + current.minute
        shift = get_shift_at_time(shifts, time_minutes)
        
        if shift and shift['name'] not in [s['name'] for s in affected_shifts]:
            affected_shifts.append(shift)
        
        current += timedelta(minutes=30)
    
    # Calculate lost production value
    # Assume full production value during shifts, partial during transitions
    lost_value = 0
    current = maintenance_start
    
    while current < maintenance_end:
        time_minutes = current.hour * 60 + current.minute
        shift = get_shift_at_time(shifts, time_minutes)
        
        if shift:
            lost_value += production_value_per_hour * 0.5  # 30 min chunks
        else:
            lost_value += production_value_per_hour * 0.1  # Off-shift minimal
        
        current += timedelta(minutes=30)
    
    # Determine impact level
    if len(affected_shifts) == 0:
        impact_level = "LOW"
        optimal = True
        reason = "Off-shift maintenance - minimal production impact"
    elif len(affected_shifts) == 1 and duration_hours <= 2:
        impact_level = "LOW"
        optimal = True
        reason = "Single shift affected, short duration"
    elif len(affected_shifts) == 1:
        impact_level = "MEDIUM"
        optimal = False
        reason = "Single shift affected but longer duration"
    else:
        impact_level = "HIGH"
        optimal = False
        reason = "Multiple shifts affected"
    
    # Check if during designated maintenance window
    start_minutes = maintenance_start.hour * 60 + maintenance_start.minute
    for window in maintenance_windows:
        window_minutes = parse_time(window)
        if abs(start_minutes - window_minutes) <= 30:  # Within 30 min
            impact_level = "LOW"
            optimal = True
            reason = "Scheduled during designated maintenance window"
            break
    
    return {
        "affected_shifts": [s['name'] for s in affected_shifts],
        "downtime_hours": round(duration_hours, 1),
        "lost_production_value": round(lost_value, 2),
        "impact_level": impact_level,
        "optimal": optimal,
        "reason": reason
    }


@router.get("/schedule/{machine_id}")
def get_production_schedule(machine_id: str, db: Session = Depends(get_db)):
    """Get production schedule for a machine."""
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    return {
        "machine_id": machine_id,
        "shift_schedule": machine.shift_schedule,
        "production_value_per_hour": 10000  # Configurable
    }


@router.post("/schedule/{machine_id}")
def update_production_schedule(
    machine_id: str,
    shifts: List[Dict],
    maintenance_windows: List[str],
    weekend_maintenance: bool = True,
    db: Session = Depends(get_db)
):
    """Update production schedule for a machine."""
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    machine.shift_schedule = {
        "shifts": shifts,
        "maintenance_windows": maintenance_windows,
        "weekend_maintenance": weekend_maintenance
    }
    
    db.commit()
    
    return {
        "success": True,
        "machine_id": machine_id,
        "shift_schedule": machine.shift_schedule
    }


@router.post("/impact/{schedule_id}")
def calculate_schedule_impact(
    schedule_id: str,
    db: Session = Depends(get_db)
):
    """Calculate production impact for a maintenance schedule."""
    schedule = db.query(MaintenanceSchedule).filter(
        MaintenanceSchedule.schedule_id == schedule_id
    ).first()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    machine = db.query(Machine).filter(
        Machine.machine_id == schedule.machine_id
    ).first()
    
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    impact = calculate_production_impact(
        maintenance_start=schedule.recommended_start,
        maintenance_end=schedule.recommended_end,
        shift_schedule=machine.shift_schedule or {},
        production_value_per_hour=10000
    )
    
    # Update schedule with calculated impact
    schedule.production_impact = impact["impact_level"]
    schedule.affected_shifts = impact["affected_shifts"]
    schedule.estimated_downtime_cost = impact["lost_production_value"]
    
    db.commit()
    
    return {
        "schedule_id": schedule_id,
        "impact": impact
    }


@router.get("/optimal-windows/{machine_id}")
def get_optimal_maintenance_windows(
    machine_id: str,
    days_ahead: int = 7,
    db: Session = Depends(get_db)
):
    """
    Get optimal maintenance windows for the next N days.
    Considers shift schedules, weekends, and existing maintenance.
    """
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    shift_schedule = machine.shift_schedule or {}
    shifts = shift_schedule.get('shifts', [])
    maintenance_windows = shift_schedule.get('maintenance_windows', ['13:45', '21:45'])
    weekend_allowed = shift_schedule.get('weekend_maintenance', True)
    
    # Get existing maintenance schedules
    existing_schedules = db.query(MaintenanceSchedule).filter(
        MaintenanceSchedule.machine_id == machine_id,
        MaintenanceSchedule.status.in_(['confirmed', 'proposed'])
    ).all()
    
    existing_times = [(s.recommended_start, s.recommended_end) for s in existing_schedules]
    
    optimal_windows = []
    now = datetime.utcnow()
    
    for day_offset in range(days_ahead):
        date = now + timedelta(days=day_offset)
        
        # Skip weekends if not allowed
        if date.weekday() >= 5 and not weekend_allowed:
            continue
        
        for window_time in maintenance_windows:
            hour, minute = map(int, window_time.split(':'))
            
            proposed_start = date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            proposed_end = proposed_start + timedelta(hours=2.5)
            
            # Check if overlaps with existing schedule
            overlaps = False
            for existing_start, existing_end in existing_times:
                if (proposed_start < existing_end and proposed_end > existing_start):
                    overlaps = True
                    break
            
            if overlaps:
                continue
            
            # Calculate impact
            impact = calculate_production_impact(
                proposed_start,
                proposed_end,
                shift_schedule,
                10000
            )
            
            if impact["optimal"] or impact["impact_level"] == "LOW":
                optimal_windows.append({
                    "start": proposed_start.isoformat(),
                    "end": proposed_end.isoformat(),
                    "impact": impact["impact_level"],
                    "lost_value": impact["lost_production_value"],
                    "reason": impact["reason"]
                })
    
    # Sort by lost value (lowest first)
    optimal_windows.sort(key=lambda x: x["lost_value"])
    
    return {
        "machine_id": machine_id,
        "optimal_windows": optimal_windows[:10],  # Top 10
        "total_options": len(optimal_windows)
    }


@router.get("/dashboard")
def get_production_dashboard(db: Session = Depends(get_db)):
    """Get production impact dashboard."""
    
    # Get all upcoming maintenance
    upcoming = db.query(MaintenanceSchedule).filter(
        MaintenanceSchedule.status.in_(['proposed', 'confirmed']),
        MaintenanceSchedule.recommended_start >= datetime.utcnow()
    ).all()
    
    total_lost_value = sum(s.estimated_downtime_cost or 0 for s in upcoming)
    
    impact_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    for s in upcoming:
        impact = s.production_impact or "MEDIUM"
        impact_counts[impact] = impact_counts.get(impact, 0) + 1
    
    # Calculate potential savings vs emergency
    emergency_cost = len(upcoming) * 50000  # $50k per emergency repair
    planned_cost = total_lost_value
    savings = emergency_cost - planned_cost
    
    return {
        "upcoming_maintenance": len(upcoming),
        "total_estimated_impact": round(total_lost_value, 2),
        "impact_distribution": impact_counts,
        "potential_savings_vs_emergency": round(savings, 2),
        "optimization_score": round(
            (impact_counts["LOW"] / len(upcoming) * 100) if upcoming else 100, 1
        )
    }
