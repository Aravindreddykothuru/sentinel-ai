"""
Digital Twin API Routes for SENTINEL AI.
Physics-based simulation and what-if scenario analysis.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.digital_twin import (
    DigitalTwin, get_or_create_twin, run_maintenance_optimization,
    MaintenanceAction
)

router = APIRouter(prefix="/twin", tags=["digital-twin"])


class MaintenanceActionInput(BaseModel):
    name: str
    affected_sensors: List[str]
    effectiveness: float
    duration_hours: float
    cost: float
    description: str


class SimulationRequest(BaseModel):
    scenario_name: str
    hours: float
    maintenance_actions: Optional[List[MaintenanceActionInput]] = []
    stress_factor: float = 1.0


class ScenarioComparisonRequest(BaseModel):
    scenarios: List[SimulationRequest]


@router.get("/state/{machine_id}")
def get_twin_state(machine_id: str, machine_type: str = "ginning_press"):
    """Get current state of a machine's digital twin."""
    try:
        twin = get_or_create_twin(machine_id, machine_type)
        return {
            "status": "success",
            "twin_state": twin.get_current_state()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get twin state: {str(e)}")


@router.post("/simulate/{machine_id}")
def run_simulation(machine_id: str, request: SimulationRequest, machine_type: str = "ginning_press"):
    """
    Run a what-if simulation scenario.
    
    Simulates machine behavior over time with optional maintenance actions.
    """
    try:
        twin = get_or_create_twin(machine_id, machine_type)
        
        # Convert input actions
        actions = [
            MaintenanceAction(
                name=a.name,
                affected_sensors=a.affected_sensors,
                effectiveness=a.effectiveness,
                duration_hours=a.duration_hours,
                cost=a.cost,
                description=a.description
            )
            for a in (request.maintenance_actions or [])
        ]
        
        result = twin.simulate_scenario(
            scenario_name=request.scenario_name,
            hours=request.hours,
            maintenance_actions=actions,
            stress_factor=request.stress_factor
        )
        
        return {
            "status": "success",
            "simulation": {
                "scenario_name": result.scenario_name,
                "hours_simulated": len(result.timeline),
                "failure_predicted": result.failure_predicted,
                "failure_time_hours": result.failure_time_hours,
                "final_sensor_values": result.final_sensor_values,
                "maintenance_cost": result.maintenance_cost,
                "downtime_hours": result.downtime_hours,
                "health_trajectory": result.health_trajectory,
                "timeline_sample": result.timeline[:10]  # First 10 hours
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")


@router.post("/compare/{machine_id}")
def compare_scenarios(machine_id: str, request: ScenarioComparisonRequest, machine_type: str = "ginning_press"):
    """Compare multiple what-if scenarios side by side."""
    try:
        twin = get_or_create_twin(machine_id, machine_type)
        
        scenarios = []
        for sim_req in request.scenarios:
            actions = [
                MaintenanceAction(
                    name=a.name,
                    affected_sensors=a.affected_sensors,
                    effectiveness=a.effectiveness,
                    duration_hours=a.duration_hours,
                    cost=a.cost,
                    description=a.description
                )
                for a in (sim_req.maintenance_actions or [])
            ]
            scenarios.append((sim_req.scenario_name, sim_req.hours, actions))
        
        results = twin.compare_scenarios(scenarios)
        
        return {
            "status": "success",
            "machine_id": machine_id,
            "comparisons": [
                {
                    "scenario_name": r.scenario_name,
                    "failure_predicted": r.failure_predicted,
                    "failure_time_hours": r.failure_time_hours,
                    "final_health": r.health_trajectory[-1] if r.health_trajectory else 0,
                    "min_health": min(r.health_trajectory) if r.health_trajectory else 0,
                    "maintenance_cost": r.maintenance_cost,
                    "downtime_hours": r.downtime_hours,
                    "cost_per_health_point": round(r.maintenance_cost / (r.health_trajectory[-1] + 1), 2) if r.health_trajectory else 0
                }
                for r in results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@router.post("/optimize/{machine_id}")
def optimize_maintenance(
    machine_id: str,
    current_health: float,
    predicted_failure_hours: float,
    machine_type: str = "ginning_press"
):
    """
    Run maintenance optimization to find best strategy.
    
    Compares multiple maintenance scenarios and recommends optimal timing.
    """
    try:
        result = run_maintenance_optimization(
            machine_id=machine_id,
            machine_type=machine_type,
            current_health=current_health,
            predicted_failure_hours=predicted_failure_hours
        )
        
        return {
            "status": "success",
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


@router.get("/presets/{machine_type}")
def get_maintenance_presets(machine_type: str):
    """Get predefined maintenance action presets for a machine type."""
    presets = {
        "ginning_press": [
            {
                "name": "Full Overhaul",
                "affected_sensors": ["pressure_bar", "temperature_c", "vibration_mm_s", "rpm"],
                "effectiveness": 0.85,
                "duration_hours": 8,
                "cost": 2500,
                "description": "Complete machine overhaul - restores to near-factory condition"
            },
            {
                "name": "Preventive Maintenance",
                "affected_sensors": ["pressure_bar", "temperature_c", "vibration_mm_s"],
                "effectiveness": 0.6,
                "duration_hours": 4,
                "cost": 800,
                "description": "Scheduled maintenance - addresses normal wear"
            },
            {
                "name": "Quick Inspection",
                "affected_sensors": ["vibration_mm_s"],
                "effectiveness": 0.3,
                "duration_hours": 1,
                "cost": 200,
                "description": "Visual inspection and minor adjustments"
            },
            {
                "name": "Temperature System Service",
                "affected_sensors": ["temperature_c", "pressure_bar"],
                "effectiveness": 0.5,
                "duration_hours": 3,
                "cost": 600,
                "description": "Cooling system maintenance and calibration"
            }
        ],
        "gas_turbine": [
            {
                "name": "Full Service",
                "affected_sensors": ["temperature", "pressure", "vibration", "rpm"],
                "effectiveness": 0.8,
                "duration_hours": 12,
                "cost": 5000,
                "description": "Complete turbine service"
            },
            {
                "name": "Hot Section Inspection",
                "affected_sensors": ["temperature", "pressure"],
                "effectiveness": 0.5,
                "duration_hours": 6,
                "cost": 2000,
                "description": "Combustor and turbine blade inspection"
            }
        ]
    }
    
    return {
        "status": "success",
        "machine_type": machine_type,
        "presets": presets.get(machine_type, presets["ginning_press"])
    }


@router.post("/reset/{machine_id}")
def reset_twin(machine_id: str, machine_type: str = "ginning_press"):
    """Reset digital twin to initial state."""
    try:
        from services.digital_twin import digital_twins
        if machine_id in digital_twins:
            del digital_twins[machine_id]
        
        twin = get_or_create_twin(machine_id, machine_type)
        
        return {
            "status": "success",
            "message": f"Digital twin for {machine_id} reset to initial state",
            "initial_state": twin.get_current_state()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")
