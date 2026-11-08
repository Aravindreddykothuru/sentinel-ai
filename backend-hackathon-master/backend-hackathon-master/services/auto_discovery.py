"""
Auto-Discovery & Configuration Service for SENTINEL AI.
Automatically detects sensors and tunes thresholds based on historical data.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import deque


@dataclass
class SensorProfile:
    """Profile of a detected sensor."""
    name: str
    sensor_type: str  # temperature, pressure, vibration, etc.
    unit: str
    sampling_rate: float  # Hz
    data_range: Tuple[float, float]
    normal_range: Tuple[float, float]
    stability_score: float  # 0-1, how stable the readings are
    anomaly_rate: float  # percentage of anomalous readings


@dataclass
class ThresholdRecommendation:
    """Recommended threshold configuration."""
    sensor_name: str
    current_threshold: Dict
    recommended_threshold: Dict
    confidence: float
    reasoning: str
    expected_false_positive_rate: float


class AutoDiscoveryService:
    """
    Automatic sensor discovery and threshold tuning.
    
    Features:
    - Detects sensor types from data patterns
    - Analyzes historical data for threshold optimization
    - Learns normal operating ranges
    - Reduces false positives through statistical analysis
    """
    
    # Sensor type patterns (name keywords -> type mapping)
    SENSOR_PATTERNS = {
        "temperature": {
            "keywords": ["temp", "thermal", "heat", "celsius", "fahrenheit", "kelvin"],
            "unit": "°C",
            "typical_range": (0, 200)
        },
        "pressure": {
            "keywords": ["pressure", "psi", "bar", "pascal", "mpa", "kpa"],
            "unit": "bar",
            "typical_range": (0, 100)
        },
        "vibration": {
            "keywords": ["vibration", "accel", "acceleration", "g_force", "rms"],
            "unit": "mm/s",
            "typical_range": (0, 20)
        },
        "flow_rate": {
            "keywords": ["flow", "rate", "flowrate", "gpm", "lpm", "m3/h"],
            "unit": "m³/h",
            "typical_range": (0, 500)
        },
        "rpm": {
            "keywords": ["rpm", "speed", "rotation", "rps", "hz"],
            "unit": "RPM",
            "typical_range": (0, 10000)
        },
        "current": {
            "keywords": ["current", "amp", "amperage", "a"],
            "unit": "A",
            "typical_range": (0, 100)
        },
        "voltage": {
            "keywords": ["voltage", "volt", "v", "potential"],
            "unit": "V",
            "typical_range": (0, 500)
        },
        "power": {
            "keywords": ["power", "watt", "kw", "mw", "consumption"],
            "unit": "kW",
            "typical_range": (0, 1000)
        }
    }
    
    def __init__(self):
        self.reading_history: Dict[str, deque] = {}  # sensor_name -> deque of readings
        self.max_history_size = 1000
        self.discovered_sensors: Dict[str, SensorProfile] = {}
    
    def discover_sensors_from_data(
        self,
        data_samples: List[Dict[str, float]],
        timestamp_field: str = "timestamp"
    ) -> List[SensorProfile]:
        """
        Discover and profile sensors from data samples.
        
        Args:
            data_samples: List of sensor reading dictionaries
            timestamp_field: Field name for timestamp (excluded from sensors)
            
        Returns:
            List of SensorProfile objects
        """
        if not data_samples:
            return []
        
        # Extract sensor names from first sample
        sensor_names = [
            key for key in data_samples[0].keys()
            if key != timestamp_field
        ]
        
        profiles = []
        for sensor_name in sensor_names:
            # Extract values for this sensor
            values = [
                sample[sensor_name]
                for sample in data_samples
                if sensor_name in sample and sample[sensor_name] is not None
            ]
            
            if len(values) < 2:
                continue
            
            profile = self._analyze_sensor(sensor_name, values)
            profiles.append(profile)
            self.discovered_sensors[sensor_name] = profile
        
        return profiles
    
    def _analyze_sensor(self, name: str, values: List[float]) -> SensorProfile:
        """Analyze sensor data to create profile."""
        # Detect sensor type
        sensor_type, unit = self._detect_sensor_type(name)
        
        # Calculate statistics
        values_array = np.array(values)
        min_val = float(np.min(values_array))
        max_val = float(np.max(values_array))
        mean_val = float(np.mean(values_array))
        std_val = float(np.std(values_array))
        
        # Calculate sampling rate (if timestamps available)
        sampling_rate = 1.0  # Default 1 Hz
        
        # Calculate stability score (lower std = higher stability)
        range_val = max_val - min_val if max_val != min_val else 1
        stability_score = max(0, 1 - (std_val / range_val)) if range_val > 0 else 1
        
        # Calculate anomaly rate (values beyond 3 sigma)
        anomalies = np.abs(values_array - mean_val) > (3 * std_val)
        anomaly_rate = float(np.sum(anomalies) / len(values_array) * 100)
        
        # Determine normal operating range (95% confidence interval)
        normal_low = float(mean_val - 2 * std_val)
        normal_high = float(mean_val + 2 * std_val)
        
        return SensorProfile(
            name=name,
            sensor_type=sensor_type,
            unit=unit,
            sampling_rate=sampling_rate,
            data_range=(min_val, max_val),
            normal_range=(normal_low, normal_high),
            stability_score=stability_score,
            anomaly_rate=anomaly_rate
        )
    
    def _detect_sensor_type(self, name: str) -> Tuple[str, str]:
        """Detect sensor type from name."""
        name_lower = name.lower()
        
        for sensor_type, config in self.SENSOR_PATTERNS.items():
            if any(keyword in name_lower for keyword in config["keywords"]):
                return sensor_type, config["unit"]
        
        return "unknown", "units"
    
    def recommend_thresholds(
        self,
        sensor_name: str,
        current_thresholds: Optional[Dict] = None,
        historical_data: Optional[List[float]] = None
    ) -> ThresholdRecommendation:
        """
        Recommend optimized thresholds based on historical data.
        
        Uses statistical analysis to minimize false positives while
        maintaining sensitivity to real anomalies.
        """
        if historical_data is None or len(historical_data) < 10:
            return ThresholdRecommendation(
                sensor_name=sensor_name,
                current_threshold=current_thresholds or {},
                recommended_threshold=current_thresholds or {},
                confidence=0.0,
                reasoning="Insufficient historical data (need at least 10 readings)",
                expected_false_positive_rate=0.0
            )
        
        values = np.array(historical_data)
        
        # Calculate percentiles for threshold recommendations
        p1 = np.percentile(values, 1)
        p5 = np.percentile(values, 5)
        p95 = np.percentile(values, 95)
        p99 = np.percentile(values, 99)
        
        # Recommended thresholds using percentile-based approach
        recommended = {
            "min": round(float(p5), 2),
            "max": round(float(p95), 2),
            "critical_low": round(float(p1), 2),
            "critical_high": round(float(p99), 2)
        }
        
        # Calculate confidence based on data quality
        data_points = len(values)
        confidence = min(1.0, data_points / 100)  # Max confidence at 100+ points
        
        # Estimate false positive rate
        # Values outside 5th-95th percentile are considered warnings
        outside_range = np.sum((values < p5) | (values > p95))
        fp_rate = outside_range / len(values) * 100
        
        reasoning = (
            f"Thresholds based on {data_points} historical readings. "
            f"Min/Max set at 5th/95th percentile to capture normal variation. "
            f"Critical thresholds at 1st/99th percentile for extreme events."
        )
        
        return ThresholdRecommendation(
            sensor_name=sensor_name,
            current_threshold=current_thresholds or {},
            recommended_threshold=recommended,
            confidence=confidence,
            reasoning=reasoning,
            expected_false_positive_rate=round(fp_rate, 2)
        )
    
    def auto_tune_machine(
        self,
        machine_id: str,
        readings_history: Dict[str, List[float]],
        current_thresholds: Dict[str, Dict]
    ) -> Dict:
        """
        Automatically tune all thresholds for a machine.
        
        Args:
            machine_id: Machine identifier
            readings_history: Dict of sensor_name -> list of historical values
            current_thresholds: Current threshold configuration
            
        Returns:
            Tuning results with recommendations for each sensor
        """
        recommendations = []
        
        for sensor_name, history in readings_history.items():
            current = current_thresholds.get(sensor_name, {})
            
            rec = self.recommend_thresholds(
                sensor_name=sensor_name,
                current_thresholds=current,
                historical_data=history
            )
            
            recommendations.append({
                "sensor": sensor_name,
                "current": rec.current_threshold,
                "recommended": rec.recommended_threshold,
                "confidence": rec.confidence,
                "reasoning": rec.reasoning,
                "expected_fp_rate": rec.expected_false_positive_rate
            })
        
        # Calculate overall tuning confidence
        avg_confidence = np.mean([r["confidence"] for r in recommendations]) if recommendations else 0
        
        return {
            "machine_id": machine_id,
            "tuning_timestamp": datetime.utcnow().isoformat(),
            "sensors_analyzed": len(recommendations),
            "overall_confidence": round(float(avg_confidence), 2),
            "recommendations": recommendations,
            "summary": {
                "high_confidence": sum(1 for r in recommendations if r["confidence"] > 0.8),
                "medium_confidence": sum(1 for r in recommendations if 0.5 <= r["confidence"] <= 0.8),
                "low_confidence": sum(1 for r in recommendations if r["confidence"] < 0.5)
            }
        }
    
    def detect_new_sensors(
        self,
        machine_id: str,
        previous_sensors: List[str],
        current_reading: Dict[str, float]
    ) -> List[str]:
        """Detect any new sensors that appeared in readings."""
        current_sensors = set(current_reading.keys())
        previous_set = set(previous_sensors)
        
        new_sensors = list(current_sensors - previous_set)
        
        return new_sensors
    
    def validate_sensor_health(
        self,
        sensor_name: str,
        recent_readings: List[float]
    ) -> Dict:
        """
        Validate if a sensor is healthy and providing good data.
        
        Checks for:
        - Stuck values (no variation)
        - Excessive noise
        - Missing data
        - Out-of-range values
        """
        if len(recent_readings) < 5:
            return {
                "sensor": sensor_name,
                "healthy": False,
                "issues": ["Insufficient data for health check"],
                "recommendation": "Collect more readings"
            }
        
        values = np.array(recent_readings)
        issues = []
        
        # Check for stuck values
        unique_values = len(np.unique(values))
        if unique_values < 3:
            issues.append("Sensor appears stuck (very few unique values)")
        
        # Check for excessive noise
        std_val = np.std(values)
        mean_val = np.mean(values)
        if mean_val != 0 and std_val / abs(mean_val) > 0.5:
            issues.append("High noise level detected")
        
        # Check for missing data (represented as None or NaN)
        missing_count = np.sum(np.isnan(values))
        if missing_count > 0:
            issues.append(f"Missing data: {missing_count}/{len(values)} readings")
        
        # Check for out-of-range values
        profile = self.discovered_sensors.get(sensor_name)
        if profile:
            min_val, max_val = profile.data_range
            out_of_range = np.sum((values < min_val * 0.5) | (values > max_val * 2))
            if out_of_range > 0:
                issues.append(f"{out_of_range} readings significantly out of expected range")
        
        healthy = len(issues) == 0
        
        return {
            "sensor": sensor_name,
            "healthy": healthy,
            "issues": issues,
            "recommendation": "Sensor OK" if healthy else "Review sensor configuration",
            "data_quality_score": round(1 - (len(issues) * 0.2), 2)
        }


# Global service instance
auto_discovery_service = AutoDiscoveryService()
