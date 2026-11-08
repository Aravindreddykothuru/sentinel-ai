"""
Zero-Config Machine Onboarding Service for SENTINEL AI.
Automatically configures new machines in <5 minutes.
"""

import uuid
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class OnboardingResult:
    """Result of machine onboarding process."""
    success: bool
    machine_id: str
    detected_sensors: List[str]
    configured_thresholds: Dict
    estimated_setup_time: int  # seconds
    errors: List[str]
    warnings: List[str]


class OnboardingService:
    """
    Zero-configuration machine onboarding.
    
    Features:
    - Auto-detects machine type from sensor signatures
    - Auto-configures thresholds based on machine type
    - Auto-assigns optimal monitoring parameters
    - Validates configuration before activation
    """
    
    # Machine type signatures (sensor combinations)
    MACHINE_SIGNATURES = {
        "gas_turbine": {
            "required_sensors": ["temperature", "pressure", "rpm", "vibration"],
            "optional_sensors": ["fuel_flow", "exhaust_temp"],
            "typical_thresholds": {
                "temperature": {"min": 60, "max": 95, "critical": 105},
                "pressure": {"min": 80, "max": 110, "critical": 75},
                "rpm": {"min": 2800, "max": 3600, "critical": 4000},
                "vibration": {"min": 0.5, "max": 3.5, "critical": 5.0}
            }
        },
        "compressor": {
            "required_sensors": ["pressure", "temperature", "flow_rate", "vibration"],
            "optional_sensors": ["power_consumption", "oil_temp"],
            "typical_thresholds": {
                "pressure": {"min": 4.0, "max": 7.0, "critical": 8.0},
                "temperature": {"min": 40, "max": 75, "critical": 85},
                "flow_rate": {"min": 80, "max": 120, "critical": 140},
                "vibration": {"min": 0.2, "max": 2.5, "critical": 4.0}
            }
        },
        "pump": {
            "required_sensors": ["flow_rate", "pressure", "temperature", "current"],
            "optional_sensors": ["vibration", "speed"],
            "typical_thresholds": {
                "flow_rate": {"min": 40, "max": 80, "critical": 90},
                "pressure": {"min": 2.0, "max": 6.0, "critical": 7.0},
                "temperature": {"min": 30, "max": 65, "critical": 80},
                "current": {"min": 5, "max": 15, "critical": 20}
            }
        },
        "motor": {
            "required_sensors": ["current", "temperature", "vibration", "rpm"],
            "optional_sensors": ["voltage", "power_factor"],
            "typical_thresholds": {
                "current": {"min": 8, "max": 25, "critical": 35},
                "temperature": {"min": 35, "max": 75, "critical": 95},
                "vibration": {"min": 0.1, "max": 2.0, "critical": 4.5},
                "rpm": {"min": 1400, "max": 1750, "critical": 2000}
            }
        },
        "generator": {
            "required_sensors": ["voltage", "current", "temperature", "frequency"],
            "optional_sensors": ["power_output", "oil_pressure"],
            "typical_thresholds": {
                "voltage": {"min": 220, "max": 245, "critical": 260},
                "current": {"min": 10, "max": 50, "critical": 70},
                "temperature": {"min": 40, "max": 80, "critical": 100},
                "frequency": {"min": 49.5, "max": 50.5, "critical": 52.0}
            }
        }
    }
    
    def __init__(self):
        self.setup_steps = [
            "detect_sensors",
            "identify_machine_type",
            "configure_thresholds",
            "setup_monitoring",
            "validate_configuration"
        ]
    
    async def onboard_machine(
        self,
        machine_name: str,
        location: str,
        initial_sensor_data: Dict[str, float],
        user_hints: Optional[Dict] = None
    ) -> OnboardingResult:
        """
        Perform zero-config machine onboarding.
        
        Args:
            machine_name: Human-readable machine name
            location: Physical location
            initial_sensor_data: First reading from sensors {sensor_name: value}
            user_hints: Optional hints from user {"machine_type": "gas_turbine"}
            
        Returns:
            OnboardingResult with configuration details
        """
        errors = []
        warnings = []
        start_time = datetime.utcnow()
        
        try:
            # Step 1: Detect sensors from initial data
            detected_sensors = list(initial_sensor_data.keys())
            
            if len(detected_sensors) < 2:
                errors.append("At least 2 sensors required for monitoring")
                return OnboardingResult(
                    success=False,
                    machine_id="",
                    detected_sensors=detected_sensors,
                    configured_thresholds={},
                    estimated_setup_time=0,
                    errors=errors,
                    warnings=warnings
                )
            
            # Step 2: Identify machine type
            machine_type = self._identify_machine_type(
                detected_sensors,
                user_hints
            )
            
            if not machine_type:
                warnings.append("Could not auto-identify machine type - using generic configuration")
                machine_type = "generic"
            
            # Step 3: Configure thresholds
            thresholds = self._configure_thresholds(machine_type, detected_sensors)
            normal_ranges = self._configure_normal_ranges(thresholds)
            
            # Step 4: Generate machine ID
            machine_id = self._generate_machine_id(machine_name, machine_type)
            
            # Step 5: Validate configuration
            validation = self._validate_configuration(
                machine_type,
                detected_sensors,
                thresholds
            )
            
            warnings.extend(validation["warnings"])
            
            # Calculate setup time
            setup_time = (datetime.utcnow() - start_time).total_seconds()
            
            return OnboardingResult(
                success=len(errors) == 0,
                machine_id=machine_id,
                detected_sensors=detected_sensors,
                configured_thresholds=thresholds,
                estimated_setup_time=int(setup_time),
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            errors.append(f"Onboarding failed: {str(e)}")
            return OnboardingResult(
                success=False,
                machine_id="",
                detected_sensors=list(initial_sensor_data.keys()),
                configured_thresholds={},
                estimated_setup_time=0,
                errors=errors,
                warnings=warnings
            )
    
    def _identify_machine_type(
        self,
        detected_sensors: List[str],
        user_hints: Optional[Dict]
    ) -> Optional[str]:
        """Identify machine type from sensor signature."""
        # Check user hint first
        if user_hints and "machine_type" in user_hints:
            hint = user_hints["machine_type"]
            if hint in self.MACHINE_SIGNATURES:
                return hint
        
        # Auto-detect from sensor signature
        detected_set = set(detected_sensors)
        best_match = None
        best_score = 0
        
        for machine_type, signature in self.MACHINE_SIGNATURES.items():
            required = set(signature["required_sensors"])
            optional = set(signature["optional_sensors"])
            
            # Score based on required sensor matches
            required_matches = len(detected_set & required)
            optional_matches = len(detected_set & optional)
            
            # Must have at least 70% of required sensors
            if required_matches >= len(required) * 0.7:
                score = required_matches * 2 + optional_matches
                if score > best_score:
                    best_score = score
                    best_match = machine_type
        
        return best_match
    
    def _configure_thresholds(
        self,
        machine_type: str,
        detected_sensors: List[str]
    ) -> Dict:
        """Configure thresholds based on machine type."""
        if machine_type not in self.MACHINE_SIGNATURES:
            # Generic thresholds
            return self._generate_generic_thresholds(detected_sensors)
        
        signature = self.MACHINE_SIGNATURES[machine_type]
        typical = signature["typical_thresholds"]
        
        configured = {}
        for sensor in detected_sensors:
            if sensor in typical:
                configured[sensor] = typical[sensor]
            else:
                # Generate generic threshold for unknown sensor
                configured[sensor] = self._estimate_threshold(sensor)
        
        return configured
    
    def _configure_normal_ranges(self, thresholds: Dict) -> Dict:
        """Configure normal operating ranges from thresholds."""
        normal_ranges = {}
        
        for sensor, threshold in thresholds.items():
            min_val = threshold.get("min", 0)
            max_val = threshold.get("max", 100)
            
            # Normal range is 80% of threshold range
            range_val = max_val - min_val
            buffer = range_val * 0.1
            
            normal_ranges[sensor] = {
                "low": min_val + buffer,
                "high": max_val - buffer
            }
        
        return normal_ranges
    
    def _generate_generic_thresholds(self, sensors: List[str]) -> Dict:
        """Generate generic thresholds when machine type unknown."""
        return {sensor: self._estimate_threshold(sensor) for sensor in sensors}
    
    def _estimate_threshold(self, sensor_name: str) -> Dict:
        """Estimate threshold for unknown sensor based on name patterns."""
        sensor_lower = sensor_name.lower()
        
        # Temperature sensors
        if any(word in sensor_lower for word in ["temp", "thermal", "heat"]):
            return {"min": 20, "max": 80, "critical": 100}
        
        # Pressure sensors
        if any(word in sensor_lower for word in ["pressure", "psi", "bar"]):
            return {"min": 1, "max": 10, "critical": 15}
        
        # Flow sensors
        if any(word in sensor_lower for word in ["flow", "rate"]):
            return {"min": 10, "max": 100, "critical": 120}
        
        # Vibration sensors
        if any(word in sensor_lower for word in ["vibration", "accel"]):
            return {"min": 0.1, "max": 3.0, "critical": 5.0}
        
        # Electrical sensors
        if any(word in sensor_lower for word in ["current", "amp"]):
            return {"min": 1, "max": 20, "critical": 30}
        
        if any(word in sensor_lower for word in ["voltage", "volt"]):
            return {"min": 200, "max": 250, "critical": 280}
        
        # Speed/RPM sensors
        if any(word in sensor_lower for word in ["rpm", "speed", "rotation"]):
            return {"min": 1000, "max": 3000, "critical": 3500}
        
        # Default
        return {"min": 0, "max": 100, "critical": 120}
    
    def _generate_machine_id(self, name: str, machine_type: str) -> str:
        """Generate unique machine ID."""
        # Create ID from type and random suffix
        type_prefix = machine_type[:3].upper() if machine_type != "generic" else "MCH"
        suffix = uuid.uuid4().hex[:4].upper()
        return f"{type_prefix}-{suffix}"
    
    def _validate_configuration(
        self,
        machine_type: str,
        sensors: List[str],
        thresholds: Dict
    ) -> Dict:
        """Validate the generated configuration."""
        warnings = []
        
        # Check for minimum sensors
        if len(sensors) < 3:
            warnings.append(f"Only {len(sensors)} sensors detected - recommend adding more for better monitoring")
        
        # Check for critical thresholds
        for sensor, threshold in thresholds.items():
            if "critical" not in threshold:
                warnings.append(f"No critical threshold set for {sensor}")
        
        # Check machine type confidence
        if machine_type == "generic":
            warnings.append("Using generic configuration - fine-tune thresholds after observation period")
        
        return {"warnings": warnings}
    
    def get_machine_types(self) -> List[Dict]:
        """Get list of supported machine types with descriptions."""
        return [
            {
                "type": "gas_turbine",
                "name": "Gas Turbine",
                "description": "Power generation turbines",
                "typical_sensors": ["temperature", "pressure", "rpm", "vibration"]
            },
            {
                "type": "compressor",
                "name": "Industrial Compressor",
                "description": "Air and gas compressors",
                "typical_sensors": ["pressure", "temperature", "flow_rate", "vibration"]
            },
            {
                "type": "pump",
                "name": "Industrial Pump",
                "description": "Fluid transfer pumps",
                "typical_sensors": ["flow_rate", "pressure", "temperature", "current"]
            },
            {
                "type": "motor",
                "name": "Electric Motor",
                "description": "Industrial electric motors",
                "typical_sensors": ["current", "temperature", "vibration", "rpm"]
            },
            {
                "type": "generator",
                "name": "Power Generator",
                "description": "Electrical power generators",
                "typical_sensors": ["voltage", "current", "temperature", "frequency"]
            }
        ]


# Global service instance
onboarding_service = OnboardingService()
