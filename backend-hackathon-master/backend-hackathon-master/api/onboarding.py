"""
Machine Onboarding API Routes for SENTINEL AI.
Zero-config machine setup in <5 minutes.
"""

from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Machine
from services.onboarding_service import onboarding_service

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("/discover")
async def discover_machine(
    machine_name: str,
    location: str,
    sensor_data: Dict[str, float],
    machine_type_hint: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Auto-discover and configure a new machine.
    
    This endpoint performs zero-config onboarding:
    1. Detects sensors from initial data
    2. Identifies machine type from sensor signature
    3. Auto-configures thresholds
    4. Returns complete configuration
    
    Expected to complete in <5 minutes.
    """
    # Perform onboarding
    user_hints = {"machine_type": machine_type_hint} if machine_type_hint else None
    
    result = await onboarding_service.onboard_machine(
        machine_name=machine_name,
        location=location,
        initial_sensor_data=sensor_data,
        user_hints=user_hints
    )
    
    if not result.success:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Machine onboarding failed",
                "errors": result.errors,
                "warnings": result.warnings
            }
        )
    
    # Create machine in database
    normal_ranges = onboarding_service._configure_normal_ranges(result.configured_thresholds)
    
    machine = Machine(
        machine_id=result.machine_id,
        name=machine_name,
        type=machine_type_hint or "auto_detected",
        location=location,
        status="normal",
        thresholds=result.configured_thresholds,
        normal_ranges=normal_ranges,
        sensors=result.detected_sensors
    )
    
    db.add(machine)
    db.commit()
    db.refresh(machine)
    
    return {
        "success": True,
        "message": f"Machine '{machine_name}' onboarded successfully in {result.estimated_setup_time}s",
        "machine": {
            "id": machine.id,
            "machine_id": result.machine_id,
            "name": machine_name,
            "location": location,
            "type": machine_type_hint or "auto_detected"
        },
        "configuration": {
            "detected_sensors": result.detected_sensors,
            "thresholds": result.configured_thresholds,
            "normal_ranges": normal_ranges
        },
        "warnings": result.warnings
    }


@router.get("/machine-types")
def get_machine_types():
    """Get list of supported machine types for onboarding."""
    return {
        "machine_types": onboarding_service.get_machine_types()
    }


@router.post("/validate-sensors")
def validate_sensor_data(sensor_data: Dict[str, float]):
    """
    Validate sensor data before onboarding.
    
    Returns detected sensors and suggested machine type
    without creating the machine.
    """
    detected_sensors = list(sensor_data.keys())
    
    # Try to identify machine type
    suggested_type = onboarding_service._identify_machine_type(
        detected_sensors,
        None
    )
    
    # Generate preview thresholds
    preview_thresholds = onboarding_service._configure_thresholds(
        suggested_type or "generic",
        detected_sensors
    )
    
    return {
        "detected_sensors": detected_sensors,
        "sensor_count": len(detected_sensors),
        "suggested_machine_type": suggested_type,
        "confidence": "high" if suggested_type else "low",
        "preview_thresholds": preview_thresholds,
        "ready_for_onboarding": len(detected_sensors) >= 2
    }


@router.get("/status/{machine_id}")
def get_onboarding_status(machine_id: str, db: Session = Depends(get_db)):
    """Get onboarding status for a machine."""
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    return {
        "machine_id": machine_id,
        "status": machine.status,
        "configured": True,
        "sensors": machine.sensors,
        "thresholds_configured": machine.thresholds is not None,
        "monitoring_active": machine.status != "offline"
    }


@router.post("/quick-setup")
async def quick_machine_setup(
    name: str,
    location: str,
    machine_type: str,
    db: Session = Depends(get_db)
):
    """
    Quick setup with known machine type.
    Uses default thresholds for the machine type.
    """
    if machine_type not in onboarding_service.MACHINE_SIGNATURES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown machine type. Supported: {list(onboarding_service.MACHINE_SIGNATURES.keys())}"
        )
    
    # Generate machine ID
    machine_id = onboarding_service._generate_machine_id(name, machine_type)
    
    # Get default configuration
    signature = onboarding_service.MACHINE_SIGNATURES[machine_type]
    sensors = signature["required_sensors"] + signature["optional_sensors"][:2]
    thresholds = signature["typical_thresholds"]
    normal_ranges = onboarding_service._configure_normal_ranges(thresholds)
    
    # Create machine
    machine = Machine(
        machine_id=machine_id,
        name=name,
        type=machine_type,
        location=location,
        status="normal",
        thresholds=thresholds,
        normal_ranges=normal_ranges,
        sensors=sensors
    )
    
    db.add(machine)
    db.commit()
    db.refresh(machine)
    
    return {
        "success": True,
        "message": f"Machine '{name}' created with {machine_type} defaults",
        "machine": {
            "id": machine.id,
            "machine_id": machine_id,
            "name": name,
            "type": machine_type,
            "location": location
        },
        "configuration": {
            "sensors": sensors,
            "thresholds": thresholds,
            "normal_ranges": normal_ranges
        }
    }
