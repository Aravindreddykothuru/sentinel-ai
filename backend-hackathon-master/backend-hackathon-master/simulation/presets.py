"""
Pre-configured machine presets for SENTINEL AI.
Based on the PRD Section 8.1 - Pre-Specified Machines.
"""

from typing import Dict


MACHINE_PRESETS: Dict[str, Dict] = {
    "turbine_alpha": {
        "name": "Turbine Alpha",
        "type": "gas_turbine",
        "location": "Power Plant Block A",
        "industry_preset": "power_plant",
        "sensors": ["temperature", "pressure", "rpm", "fuel_flow"],
        "thresholds": {
            "temperature": {"min": 50, "max": 100, "critical": 105},
            "pressure": {"min": 60, "max": 100, "critical": 80},
            "rpm": {"min": 2500, "max": 3500, "critical": 4000},
            "fuel_flow": {"min": 10, "max": 50, "critical": 60}
        },
        "normal_ranges": {
            "temperature": {"low": 70, "high": 95},
            "pressure": {"low": 80, "high": 95},
            "rpm": {"low": 2800, "high": 3200},
            "fuel_flow": {"low": 20, "high": 40}
        },
        "degradation_profile": {
            "temperature": {"base": 85, "drift": 0.1, "noise": 2.0},
            "pressure": {"base": 90, "drift": -0.05, "noise": 1.5},
            "rpm": {"base": 3000, "drift": 0, "noise": 50},
            "fuel_flow": {"base": 30, "drift": 0.02, "noise": 1.0}
        }
    },
    
    "compressor_beta": {
        "name": "Compressor Beta",
        "type": "air_compressor",
        "location": "Assembly Line B",
        "industry_preset": "automotive",
        "sensors": ["temperature", "pressure", "flow_rate", "vibration"],
        "thresholds": {
            "temperature": {"min": 40, "max": 90, "critical": 95},
            "pressure": {"min": 60, "max": 110, "critical": 50},
            "flow_rate": {"min": 100, "max": 300, "critical": 350},
            "vibration": {"min": 0, "max": 3.0, "critical": 4.0}
        },
        "normal_ranges": {
            "temperature": {"low": 60, "high": 85},
            "pressure": {"low": 80, "high": 100},
            "flow_rate": {"low": 150, "high": 250},
            "vibration": {"low": 0.5, "high": 2.0}
        },
        "degradation_profile": {
            "temperature": {"base": 75, "drift": 0.08, "noise": 1.5},
            "pressure": {"base": 90, "drift": -0.03, "noise": 2.0},
            "flow_rate": {"base": 200, "drift": -0.5, "noise": 10.0},
            "vibration": {"base": 1.2, "drift": 0.01, "noise": 0.2}
        }
    },
    
    "pump_gamma": {
        "name": "Pump Gamma",
        "type": "hydraulic_pump",
        "location": "Hydraulic Station C",
        "industry_preset": "oil_gas",
        "sensors": ["temperature", "vibration", "rpm", "pressure"],
        "thresholds": {
            "temperature": {"min": 50, "max": 95, "critical": 100},
            "vibration": {"min": 0, "max": 3.5, "critical": 4.5},
            "rpm": {"min": 1500, "max": 3000, "critical": 3500},
            "pressure": {"min": 50, "max": 90, "critical": 70}
        },
        "normal_ranges": {
            "temperature": {"low": 65, "high": 85},
            "vibration": {"low": 0.8, "high": 2.5},
            "rpm": {"low": 2200, "high": 2800},
            "pressure": {"low": 75, "high": 85}
        },
        "degradation_profile": {
            "temperature": {"base": 78, "drift": 0.12, "noise": 1.8},
            "vibration": {"base": 1.5, "drift": 0.015, "noise": 0.25},
            "rpm": {"base": 2500, "drift": -2.0, "noise": 30.0},
            "pressure": {"base": 80, "drift": -0.08, "noise": 2.0}
        }
    },
    
    "motor_delta": {
        "name": "Motor Delta",
        "type": "drive_motor",
        "location": "Conveyor Section D",
        "industry_preset": "automotive",
        "sensors": ["temperature", "vibration", "current", "rpm"],
        "thresholds": {
            "temperature": {"min": 40, "max": 85, "critical": 90},
            "vibration": {"min": 0, "max": 4.0, "critical": 5.0},
            "current": {"min": 20, "max": 45, "critical": 48},
            "rpm": {"min": 1500, "max": 3200, "critical": 3600}
        },
        "normal_ranges": {
            "temperature": {"low": 55, "high": 75},
            "vibration": {"low": 1.0, "high": 3.0},
            "current": {"low": 30, "high": 40},
            "rpm": {"low": 2800, "high": 3100}
        },
        "degradation_profile": {
            "temperature": {"base": 68, "drift": 0.09, "noise": 1.2},
            "vibration": {"base": 2.0, "drift": 0.012, "noise": 0.3},
            "current": {"base": 35, "drift": 0.05, "noise": 1.5},
            "rpm": {"base": 2950, "drift": -1.0, "noise": 25.0}
        }
    }
}


INDUSTRY_PRESETS: Dict[str, Dict] = {
    "steel": {
        "name": "Steel & Metal",
        "typical_machines": ["Furnaces", "Rolling Mills", "Cranes"],
        "default_sensors": ["temperature", "vibration", "pressure"]
    },
    "automotive": {
        "name": "Automotive",
        "typical_machines": ["Welding Robots", "Conveyor Belts", "Presses"],
        "default_sensors": ["temperature", "vibration", "current", "rpm"]
    },
    "food": {
        "name": "Food & Beverage",
        "typical_machines": ["Mixers", "Bottling Lines", "Refrigeration"],
        "default_sensors": ["temperature", "pressure", "flow_rate"]
    },
    "oil_gas": {
        "name": "Oil & Gas",
        "typical_machines": ["Pumps", "Compressors", "Separators"],
        "default_sensors": ["temperature", "pressure", "vibration", "flow_rate"]
    },
    "power_plant": {
        "name": "Power Plant",
        "typical_machines": ["Turbines", "Generators", "Cooling Systems"],
        "default_sensors": ["temperature", "pressure", "rpm", "fuel_flow"]
    },
    "custom": {
        "name": "Custom",
        "typical_machines": [],
        "default_sensors": ["temperature", "vibration", "pressure"]
    }
}


def get_machine_preset(preset_id: str) -> Dict:
    """Get a machine preset by ID."""
    return MACHINE_PRESETS.get(preset_id, MACHINE_PRESETS["turbine_alpha"])


def get_industry_preset(industry_id: str) -> Dict:
    """Get an industry preset by ID."""
    return INDUSTRY_PRESETS.get(industry_id, INDUSTRY_PRESETS["custom"])


def list_machine_presets() -> list:
    """List all available machine preset IDs."""
    return list(MACHINE_PRESETS.keys())


def list_industry_presets() -> list:
    """List all available industry preset IDs."""
    return list(INDUSTRY_PRESETS.keys())
