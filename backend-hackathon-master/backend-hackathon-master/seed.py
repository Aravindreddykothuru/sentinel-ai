"""
Demo data for SENTINEL AI.
Seeds the four machines the dashboard ships with, using the same IDs, sensors and
normal ranges as the frontend, so live data lines up with what the UI expects.
"""

from datetime import datetime
from sqlalchemy.orm import Session

from models import Machine, SensorReading
from services.scheduled_grok_generator import compute_health


def _ranges(temperature, vibration, rpm, pressure):
    return {
        "temperature": {"low": temperature[0], "high": temperature[1]},
        "vibration": {"low": vibration[0], "high": vibration[1]},
        "rpm": {"low": rpm[0], "high": rpm[1]},
        "pressure": {"low": pressure[0], "high": pressure[1]},
    }


def thresholds_from_normal_ranges(normal_ranges: dict) -> dict:
    """Alarm limits 15% past the normal range, critical at 30% above the normal high."""
    thresholds = {}
    for sensor, normal in normal_ranges.items():
        low = normal.get("low", normal.get("min", 0))
        high = normal.get("high", normal.get("max", 0))
        thresholds[sensor] = {
            "min": round(low * 0.85, 2),
            "max": round(high * 1.15, 2),
            "critical": round(high * 1.3, 2),
        }
    return thresholds


DEMO_MACHINES = [
    {
        "machine_id": "A",
        "name": "Turbine Alpha",
        "type": "Gas Turbine",
        "location": "Bay 1",
        "industry_preset": "power_plant",
        "normal_ranges": _ranges((20, 95), (0, 4.5), (2000, 4000), (60, 110)),
        "initial": {"temperature": 78, "vibration": 2.1, "rpm": 3200, "pressure": 82},
    },
    {
        "machine_id": "B",
        "name": "Compressor Beta",
        "type": "Air Compressor",
        "location": "Bay 2",
        "industry_preset": "automotive",
        "normal_ranges": _ranges((20, 85), (0, 3.5), (1500, 3500), (50, 100)),
        "initial": {"temperature": 91, "vibration": 3.8, "rpm": 2800, "pressure": 105},
    },
    {
        "machine_id": "C",
        "name": "Pump Gamma",
        "type": "Hydraulic Pump",
        "location": "Bay 3",
        "industry_preset": "oil_gas",
        "normal_ranges": _ranges((20, 75), (0, 3.0), (1200, 3000), (40, 90)),
        "initial": {"temperature": 104, "vibration": 6.2, "rpm": 2100, "pressure": 112},
    },
    {
        "machine_id": "D",
        "name": "Motor Delta",
        "type": "Drive Motor",
        "location": "Bay 4",
        "industry_preset": "automotive",
        "normal_ranges": _ranges((20, 80), (0, 3.0), (1000, 4500), (30, 80)),
        "initial": {"temperature": 62, "vibration": 1.4, "rpm": 3600, "pressure": 58},
    },
]


def seed_demo_machines(db: Session) -> int:
    """Insert any missing demo machines, each with a starting reading. Returns how many were added."""
    added = 0
    for spec in DEMO_MACHINES:
        if db.query(Machine).filter(Machine.machine_id == spec["machine_id"]).first():
            continue

        thresholds = thresholds_from_normal_ranges(spec["normal_ranges"])
        health, failure_probability = compute_health(spec["initial"], thresholds, spec["normal_ranges"])
        machine = Machine(
            machine_id=spec["machine_id"],
            name=spec["name"],
            type=spec["type"],
            location=spec["location"],
            industry_preset=spec["industry_preset"],
            thresholds=thresholds,
            normal_ranges=spec["normal_ranges"],
            health_score=health,
            failure_probability=failure_probability,
        )
        db.add(machine)
        db.flush()

        db.add(SensorReading(
            machine_id=machine.id,
            timestamp=datetime.utcnow(),
            data_source="seed",
            reading_number=0,
            degradation_factor=1.0,
            sensor_values=spec["initial"],
            health_score=health,
            failure_probability=failure_probability,
        ))
        added += 1

    db.commit()
    return added
