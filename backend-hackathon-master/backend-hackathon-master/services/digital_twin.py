"""
Digital Twin Core for SENTINEL AI.
Physics-based simulation engine for virtual machine modeling.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class DegradationModel(Enum):
    """Types of degradation models."""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    WEIBULL = "weibull"


@dataclass
class VirtualSensor:
    """Virtual sensor in the digital twin."""
    name: str
    current_value: float
    normal_range: Tuple[float, float]
    degradation_rate: float
    degradation_model: DegradationModel
    noise_std: float = 0.1
    
    def simulate_step(self, hours: float = 1.0, stress_factor: float = 1.0) -> float:
        """Simulate sensor value after time step."""
        if self.degradation_model == DegradationModel.LINEAR:
            degradation = self.degradation_rate * hours * stress_factor
        elif self.degradation_model == DegradationModel.EXPONENTIAL:
            drift = abs(self.current_value - np.mean(self.normal_range))
            acceleration = 1 + (drift / (self.normal_range[1] - self.normal_range[0]))
            degradation = self.degradation_rate * hours * stress_factor * acceleration
        else:
            degradation = self.degradation_rate * hours * stress_factor
        
        if self.current_value < self.normal_range[0]:
            self.current_value -= degradation
        elif self.current_value > self.normal_range[1]:
            self.current_value += degradation
        else:
            self.current_value += degradation if np.random.random() > 0.5 else -degradation
        
        self.current_value += np.random.normal(0, self.noise_std)
        return self.current_value
    
    def reset(self, value: float):
        """Reset sensor to initial value (after maintenance)."""
        self.current_value = value


@dataclass
class MaintenanceAction:
    """A maintenance action in the simulation."""
    name: str
    affected_sensors: List[str]
    effectiveness: float
    duration_hours: float
    cost: float
    description: str


@dataclass
class SimulationResult:
    """Result of a digital twin simulation."""
    scenario_name: str
    timeline: List[Dict]
    failure_predicted: bool
    failure_time_hours: Optional[float]
    final_sensor_values: Dict[str, float]
    maintenance_cost: float
    downtime_hours: float
    health_trajectory: List[float]


class DigitalTwin:
    """Digital Twin for a machine."""
    
    def __init__(self, machine_id: str, machine_type: str):
        self.machine_id = machine_id
        self.machine_type = machine_type
        self.virtual_sensors: Dict[str, VirtualSensor] = {}
        self.health_score: float = 100.0
        self.total_operating_hours: float = 0.0
        self.last_maintenance_hours: float = 0.0
        self._initialize_sensors()
    
    def _initialize_sensors(self):
        """Initialize virtual sensors based on machine type."""
        configs = {
            "ginning_press": {
                "pressure_bar": (95.0, (90.0, 100.0), 0.5, DegradationModel.EXPONENTIAL, 2.0),
                "temperature_c": (72.0, (68.0, 78.0), 0.3, DegradationModel.EXPONENTIAL, 3.0),
                "vibration_mm_s": (2.0, (1.5, 3.0), 0.05, DegradationModel.LINEAR, 0.3),
                "rpm": (1480.0, (1380.0, 1580.0), 2.0, DegradationModel.LINEAR, 50.0)
            },
            "gas_turbine": {
                "temperature": (75.0, (60.0, 95.0), 0.2, DegradationModel.EXPONENTIAL, 2.0),
                "pressure": (95.0, (80.0, 110.0), 0.3, DegradationModel.EXPONENTIAL, 3.0),
                "vibration": (2.0, (0.5, 3.5), 0.02, DegradationModel.LINEAR, 0.2),
                "rpm": (3200.0, (2800.0, 3600.0), 5.0, DegradationModel.LINEAR, 100.0)
            }
        }
        
        sensor_config = configs.get(self.machine_type, configs["ginning_press"])
        
        for name, (value, normal_range, rate, model, noise) in sensor_config.items():
            self.virtual_sensors[name] = VirtualSensor(
                name=name, current_value=value, normal_range=normal_range,
                degradation_rate=rate, degradation_model=model, noise_std=noise
            )
    
    def simulate_scenario(
        self,
        scenario_name: str,
        hours: float,
        maintenance_actions: List[MaintenanceAction] = None,
        stress_factor: float = 1.0
    ) -> SimulationResult:
        """Run a what-if simulation scenario."""
        timeline = []
        health_trajectory = []
        total_cost = 0.0
        total_downtime = 0.0
        
        # Reset sensors to current state
        initial_values = {name: vs.current_value for name, vs in self.virtual_sensors.items()}
        
        failure_time = None
        
        for hour in range(int(hours)):
            step_data = {"hour": hour, "sensors": {}, "health": 0}
            
            # Apply maintenance at specific hours
            if maintenance_actions:
                for action in maintenance_actions:
                    if action.duration_hours == hour:  # Simplified timing
                        self._apply_maintenance(action)
                        total_cost += action.cost
                        total_downtime += action.duration_hours
            
            # Simulate each sensor
            for name, sensor in self.virtual_sensors.items():
                value = sensor.simulate_step(1.0, stress_factor)
                step_data["sensors"][name] = round(value, 2)
            
            # Calculate health score
            health = self._calculate_health()
            step_data["health"] = round(health, 1)
            health_trajectory.append(health)
            
            timeline.append(step_data)
            
            # Check for failure
            if health < 20 and failure_time is None:
                failure_time = hour
            
            if health < 10:
                break
        
        # Reset sensors after simulation
        for name, value in initial_values.items():
            self.virtual_sensors[name].reset(value)
        
        final_values = {name: vs.current_value for name, vs in self.virtual_sensors.items()}
        
        return SimulationResult(
            scenario_name=scenario_name,
            timeline=timeline,
            failure_predicted=failure_time is not None,
            failure_time_hours=failure_time,
            final_sensor_values=final_values,
            maintenance_cost=total_cost,
            downtime_hours=total_downtime,
            health_trajectory=health_trajectory
        )
    
    def _apply_maintenance(self, action: MaintenanceAction):
        """Apply a maintenance action to sensors."""
        for sensor_name in action.affected_sensors:
            if sensor_name in self.virtual_sensors:
                sensor = self.virtual_sensors[sensor_name]
                # Restore toward normal range
                normal_mid = np.mean(sensor.normal_range)
                current = sensor.current_value
                improvement = (normal_mid - current) * action.effectiveness
                sensor.reset(current + improvement)
    
    def _calculate_health(self) -> float:
        """Calculate overall machine health score."""
        health_scores = []
        
        for sensor in self.virtual_sensors.values():
            min_val, max_val = sensor.normal_range
            current = sensor.current_value
            
            # Calculate distance from normal range
            if min_val <= current <= max_val:
                score = 100.0
            else:
                if current < min_val:
                    deviation = (min_val - current) / (min_val * 0.2)  # 20% buffer
                else:
                    deviation = (current - max_val) / (max_val * 0.2)
                score = max(0, 100 - deviation * 100)
            
            health_scores.append(score)
        
        return np.mean(health_scores)
    
    def compare_scenarios(
        self,
        scenarios: List[Tuple[str, float, List[MaintenanceAction]]]
    ) -> List[SimulationResult]:
        """Compare multiple what-if scenarios."""
        results = []
        
        for name, hours, actions in scenarios:
            result = self.simulate_scenario(name, hours, actions)
            results.append(result)
        
        return results
    
    def get_current_state(self) -> Dict:
        """Get current state of the digital twin."""
        return {
            "machine_id": self.machine_id,
            "machine_type": self.machine_type,
            "health_score": round(self._calculate_health(), 1),
            "operating_hours": self.total_operating_hours,
            "sensors": {
                name: {
                    "value": round(vs.current_value, 2),
                    "normal_range": vs.normal_range,
                    "status": "normal" if vs.normal_range[0] <= vs.current_value <= vs.normal_range[1] else "degraded"
                }
                for name, vs in self.virtual_sensors.items()
            }
        }


# Global twin registry
digital_twins: Dict[str, DigitalTwin] = {}


def get_or_create_twin(machine_id: str, machine_type: str) -> DigitalTwin:
    """Get existing twin or create new one."""
    if machine_id not in digital_twins:
        digital_twins[machine_id] = DigitalTwin(machine_id, machine_type)
    return digital_twins[machine_id]


def run_maintenance_optimization(
    machine_id: str,
    machine_type: str,
    current_health: float,
    predicted_failure_hours: float
) -> Dict:
    """Run optimization to find best maintenance strategy."""
    twin = get_or_create_twin(machine_id, machine_type)
    
    # Define scenarios to compare
    scenarios = [
        ("Do Nothing", predicted_failure_hours + 24, []),
        ("Immediate Maintenance", 1, [
            MaintenanceAction("Full Service", list(twin.virtual_sensors.keys()), 0.8, 4, 1000, "Complete overhaul")
        ]),
        ("Delayed Maintenance", predicted_failure_hours * 0.7, [
            MaintenanceAction("Preventive Maintenance", list(twin.virtual_sensors.keys()), 0.6, 2, 600, "Scheduled maintenance")
        ]),
        ("Partial Maintenance", predicted_failure_hours * 0.5, [
            MaintenanceAction("Quick Fix", ["temperature_c", "pressure_bar"], 0.4, 1, 300, "Critical components only")
        ])
    ]
    
    results = twin.compare_scenarios(scenarios)
    
    # Find best scenario (highest health at lowest cost)
    best = max(results, key=lambda r: (
        r.health_trajectory[-1] if r.health_trajectory else 0
    ) - (r.maintenance_cost / 100))
    
    return {
        "machine_id": machine_id,
        "current_health": current_health,
        "scenarios": [
            {
                "name": r.scenario_name,
                "failure_predicted": r.failure_predicted,
                "failure_time": r.failure_time_hours,
                "final_health": r.health_trajectory[-1] if r.health_trajectory else 0,
                "cost": r.maintenance_cost,
                "downtime": r.downtime_hours
            }
            for r in results
        ],
        "recommended": best.scenario_name,
        "expected_savings": round(best.maintenance_cost * 0.3, 2)  # Estimated savings
    }
