import random
import math
from typing import Dict, Optional
from datetime import datetime
from simulation.presets import get_machine_preset


class MachineSimulator:
    """
    Physics-based machine degradation simulator.
    Simulates realistic sensor data with gradual degradation over time.
    """
    
    def __init__(self, machine_id: str, preset_id: str = "turbine_alpha"):
        self.machine_id = machine_id
        self.preset = get_machine_preset(preset_id)
        self.degradation_profile = self.preset["degradation_profile"]
        
        # Current sensor values (start at base values)
        self.current_values = {
            sensor: profile["base"] 
            for sensor, profile in self.degradation_profile.items()
        }
        
        # Degradation state
        self.reading_count = 0
        self.degradation_factor = 1.0  # Increases over time to accelerate degradation
        self.failure_mode = None
        
        # Fault injection (for stress testing)
        self.fault_injection = {}
        
    def generate_reading(self) -> Dict:
        """Generate a new sensor reading with realistic degradation."""
        self.reading_count += 1
        
        # Apply gradual degradation
        self._apply_degradation()
        
        # Apply fault injection if active
        self._apply_fault_injection()
        
        # Add noise to each sensor
        sensors = {}
        for sensor, profile in self.degradation_profile.items():
            base_value = self.current_values[sensor]
            noise = random.gauss(0, profile["noise"])
            sensors[sensor] = round(base_value + noise, 2)
        
        return {
            "machine_id": self.machine_id,
            "timestamp": datetime.utcnow().isoformat(),
            "sensors": sensors,
            "reading_number": self.reading_count,
            "degradation_factor": round(self.degradation_factor, 3)
        }
    
    def _apply_degradation(self):
        """Apply gradual degradation to sensor values."""
        # Slowly increase degradation factor
        if self.reading_count % 10 == 0:  # Every 10 readings
            self.degradation_factor += 0.01
        
        for sensor, profile in self.degradation_profile.items():
            drift = profile["drift"] * self.degradation_factor
            self.current_values[sensor] += drift
    
    def _apply_fault_injection(self):
        """Apply any active fault injections."""
        for sensor, fault_config in self.fault_injection.items():
            if sensor in self.current_values:
                self.current_values[sensor] += fault_config.get("offset", 0)
                self.current_values[sensor] *= fault_config.get("multiplier", 1.0)
    
    def inject_fault(self, sensor: str, offset: float = 0, multiplier: float = 1.0):
        """Inject a fault into a specific sensor."""
        self.fault_injection[sensor] = {
            "offset": offset,
            "multiplier": multiplier
        }
    
    def clear_fault(self, sensor: Optional[str] = None):
        """Clear fault injection. If sensor is None, clear all."""
        if sensor is None:
            self.fault_injection = {}
        elif sensor in self.fault_injection:
            del self.fault_injection[sensor]
    
    def reset(self):
        """Reset simulator to initial state."""
        self.current_values = {
            sensor: profile["base"] 
            for sensor, profile in self.degradation_profile.items()
        }
        self.reading_count = 0
        self.degradation_factor = 1.0
        self.failure_mode = None
        self.fault_injection = {}
    
    def accelerate_degradation(self, factor: float = 2.0):
        """Temporarily accelerate degradation for demo purposes."""
        self.degradation_factor *= factor
    
    def get_current_values(self) -> Dict:
        """Get current sensor values without generating a reading."""
        return self.current_values.copy()
    
    def is_near_failure(self, thresholds: Dict) -> bool:
        """Check if machine is approaching failure thresholds."""
        for sensor, value in self.current_values.items():
            if sensor in thresholds:
                critical = thresholds[sensor].get("critical")
                if critical:
                    # Check if within 10% of critical
                    if critical > thresholds[sensor].get("max", critical):
                        # Upper threshold
                        if value >= critical * 0.90:
                            return True
                    else:
                        # Lower threshold
                        if value <= critical * 1.10:
                            return True
        return False


class SimulationManager:
    """Manages multiple machine simulators."""
    
    def __init__(self):
        self.simulators: Dict[str, MachineSimulator] = {}
    
    def create_simulator(self, machine_id: str, preset_id: str = "turbine_alpha") -> MachineSimulator:
        """Create a new machine simulator."""
        simulator = MachineSimulator(machine_id, preset_id)
        self.simulators[machine_id] = simulator
        return simulator
    
    def get_simulator(self, machine_id: str) -> Optional[MachineSimulator]:
        """Get an existing simulator."""
        return self.simulators.get(machine_id)
    
    def remove_simulator(self, machine_id: str):
        """Remove a simulator."""
        if machine_id in self.simulators:
            del self.simulators[machine_id]
    
    def generate_all_readings(self) -> Dict[str, Dict]:
        """Generate readings for all simulators."""
        return {
            machine_id: sim.generate_reading()
            for machine_id, sim in self.simulators.items()
        }
    
    def list_active_simulators(self) -> list:
        """List all active simulator IDs."""
        return list(self.simulators.keys())
    
    def reset_all(self):
        """Reset all simulators."""
        for sim in self.simulators.values():
            sim.reset()
    
    def inject_fault(self, machine_id: str, sensor: str, offset: float = 0, multiplier: float = 1.0):
        """Inject a fault into a specific machine."""
        sim = self.simulators.get(machine_id)
        if sim:
            sim.inject_fault(sensor, offset, multiplier)
    
    def clear_fault(self, machine_id: str, sensor: Optional[str] = None):
        """Clear fault from a specific machine."""
        sim = self.simulators.get(machine_id)
        if sim:
            sim.clear_fault(sensor)


# Global simulation manager instance
simulation_manager = SimulationManager()
