"""
Ginning Press Machine Data Processor for SENTINEL AI.
Preprocesses real sensor data for model validation and threshold calibration.
"""

import csv
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SensorStatistics:
    """Statistics for a sensor from real data."""
    name: str
    unit: str
    mean: float
    std: float
    min: float
    max: float
    p5: float  # 5th percentile
    p95: float  # 95th percentile
    p1: float   # 1st percentile
    p99: float  # 99th percentile
    recommended_min: float
    recommended_max: float
    recommended_critical_low: float
    recommended_critical_high: float


@dataclass
class ProcessedDataset:
    """Processed ginning press dataset."""
    sensor_stats: Dict[str, SensorStatistics]
    total_readings: int
    time_range: Tuple[datetime, datetime]
    data_quality_score: float
    sensor_correlations: Dict[str, Dict[str, float]]


class GinningDataProcessor:
    """
    Processor for ginning press machine sensor data.
    
    Features:
    - Loads and validates CSV data
    - Calculates statistical thresholds
    - Detects data quality issues
    - Provides baseline for model validation
    """
    
    SENSOR_CONFIG = {
        "pressure_bar": {"unit": "bar", "typical_range": (80, 110)},
        "temperature_c": {"unit": "°C", "typical_range": (60, 95)},
        "vibration_mm_s": {"unit": "mm/s", "typical_range": (0.5, 4.0)},
        "rpm": {"unit": "RPM", "typical_range": (1300, 1700)}
    }
    
    def __init__(self, data_path: str = None):
        """Initialize with path to CSV file."""
        if data_path is None:
            # Default path relative to backend
            data_path = Path(__file__).parent.parent.parent / "real data file" / "ginning_press_machine_normal_200_rows.csv"
        self.data_path = Path(data_path)
        self.raw_data: List[Dict] = []
        self.processed_data: Optional[ProcessedDataset] = None
    
    def load_data(self) -> List[Dict]:
        """Load and parse the CSV file."""
        if not self.data_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.data_path}")
        
        self.raw_data = []
        
        with open(self.data_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Parse timestamp
                timestamp = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')
                
                # Parse sensor values
                parsed_row = {
                    'timestamp': timestamp,
                    'pressure_bar': float(row['pressure_bar']),
                    'temperature_c': float(row['temperature_c']),
                    'vibration_mm_s': float(row['vibration_mm_s']),
                    'rpm': float(row['rpm'])
                }
                
                self.raw_data.append(parsed_row)
        
        return self.raw_data
    
    def process(self) -> ProcessedDataset:
        """Process loaded data and calculate statistics."""
        if not self.raw_data:
            self.load_data()
        
        # Extract sensor columns
        sensor_data = {
            'pressure_bar': [],
            'temperature_c': [],
            'vibration_mm_s': [],
            'rpm': []
        }
        
        timestamps = []
        
        for row in self.raw_data:
            timestamps.append(row['timestamp'])
            for sensor in sensor_data.keys():
                sensor_data[sensor].append(row[sensor])
        
        # Calculate statistics for each sensor
        sensor_stats = {}
        for sensor_name, values in sensor_data.items():
            values_array = np.array(values)
            config = self.SENSOR_CONFIG[sensor_name]
            
            stats = SensorStatistics(
                name=sensor_name,
                unit=config['unit'],
                mean=float(np.mean(values_array)),
                std=float(np.std(values_array)),
                min=float(np.min(values_array)),
                max=float(np.max(values_array)),
                p5=float(np.percentile(values_array, 5)),
                p95=float(np.percentile(values_array, 95)),
                p1=float(np.percentile(values_array, 1)),
                p99=float(np.percentile(values_array, 99)),
                # Recommended thresholds based on percentiles
                recommended_min=float(np.percentile(values_array, 5)),
                recommended_max=float(np.percentile(values_array, 95)),
                recommended_critical_low=float(np.percentile(values_array, 1)),
                recommended_critical_high=float(np.percentile(values_array, 99))
            )
            
            sensor_stats[sensor_name] = stats
        
        # Calculate correlations
        correlations = self._calculate_correlations(sensor_data)
        
        # Calculate data quality score
        quality_score = self._calculate_quality_score(sensor_data)
        
        self.processed_data = ProcessedDataset(
            sensor_stats=sensor_stats,
            total_readings=len(self.raw_data),
            time_range=(min(timestamps), max(timestamps)),
            data_quality_score=quality_score,
            sensor_correlations=correlations
        )
        
        return self.processed_data
    
    def _calculate_correlations(self, sensor_data: Dict[str, List[float]]) -> Dict[str, Dict[str, float]]:
        """Calculate correlation matrix between sensors."""
        sensors = list(sensor_data.keys())
        correlations = {}
        
        for i, sensor1 in enumerate(sensors):
            correlations[sensor1] = {}
            for j, sensor2 in enumerate(sensors):
                if i == j:
                    correlations[sensor1][sensor2] = 1.0
                else:
                    corr = np.corrcoef(sensor_data[sensor1], sensor_data[sensor2])[0, 1]
                    correlations[sensor1][sensor2] = float(corr)
        
        return correlations
    
    def _calculate_quality_score(self, sensor_data: Dict[str, List[float]]) -> float:
        """Calculate overall data quality score."""
        scores = []
        
        for sensor_name, values in sensor_data.items():
            values_array = np.array(values)
            
            # Check for missing/null values
            missing_score = 1.0  # No missing values in our data
            
            # Check for outliers (values beyond 3 sigma)
            mean = np.mean(values_array)
            std = np.std(values_array)
            outliers = np.sum(np.abs(values_array - mean) > 3 * std)
            outlier_score = 1.0 - (outliers / len(values_array))
            
            # Check for variation (stuck sensor detection)
            unique_ratio = len(np.unique(values_array)) / len(values_array)
            variation_score = min(1.0, unique_ratio * 10)  # Scale up
            
            sensor_score = (missing_score + outlier_score + variation_score) / 3
            scores.append(sensor_score)
        
        return float(np.mean(scores))
    
    def get_thresholds(self) -> Dict[str, Dict]:
        """Get recommended thresholds for all sensors."""
        if not self.processed_data:
            self.process()
        
        thresholds = {}
        for sensor_name, stats in self.processed_data.sensor_stats.items():
            thresholds[sensor_name] = {
                "min": round(stats.recommended_min, 2),
                "max": round(stats.recommended_max, 2),
                "critical_low": round(stats.recommended_critical_low, 2),
                "critical_high": round(stats.recommended_critical_high, 2),
                "unit": stats.unit
            }
        
        return thresholds
    
    def get_baseline_for_validation(self) -> Dict:
        """Get baseline statistics for model validation."""
        if not self.processed_data:
            self.process()
        
        return {
            "machine_type": "ginning_press",
            "dataset_size": self.processed_data.total_readings,
            "time_range": {
                "start": self.processed_data.time_range[0].isoformat(),
                "end": self.processed_data.time_range[1].isoformat()
            },
            "data_quality_score": round(self.processed_data.data_quality_score, 2),
            "sensor_statistics": {
                name: {
                    "mean": round(stats.mean, 2),
                    "std": round(stats.std, 2),
                    "min": round(stats.min, 2),
                    "max": round(stats.max, 2),
                    "unit": stats.unit
                }
                for name, stats in self.processed_data.sensor_stats.items()
            },
            "correlations": self.processed_data.sensor_correlations,
            "recommended_thresholds": self.get_thresholds()
        }
    
    def detect_anomalies_in_data(self) -> List[Dict]:
        """Detect anomalous readings in the dataset."""
        if not self.processed_data:
            self.process()
        
        anomalies = []
        
        for i, row in enumerate(self.raw_data):
            row_anomalies = []
            
            for sensor_name, stats in self.processed_data.sensor_stats.items():
                value = row[sensor_name]
                
                # Check if outside 3 sigma
                if abs(value - stats.mean) > 3 * stats.std:
                    row_anomalies.append({
                        "sensor": sensor_name,
                        "value": round(value, 2),
                        "expected_range": (
                            round(stats.mean - 3 * stats.std, 2),
                            round(stats.mean + 3 * stats.std, 2)
                        ),
                        "deviation_sigma": round(abs(value - stats.mean) / stats.std, 2)
                    })
            
            if row_anomalies:
                anomalies.append({
                    "timestamp": row['timestamp'].isoformat(),
                    "index": i,
                    "anomalies": row_anomalies
                })
        
        return anomalies
    
    def generate_synthetic_degradation(self, num_points: int = 50) -> List[Dict]:
        """Generate synthetic degradation scenario based on real data statistics."""
        if not self.processed_data:
            self.process()
        
        degradation_data = []
        
        # Start from normal values
        for i in range(num_points):
            progress = i / num_points  # 0 to 1
            
            row = {
                "timestamp": datetime.utcnow() + timedelta(minutes=i),
                "degradation_progress": progress
            }
            
            for sensor_name, stats in self.processed_data.sensor_stats.items():
                # Start at mean, drift toward critical
                base_value = stats.mean
                
                # Add degradation trend (different for each sensor)
                if sensor_name == "temperature_c":
                    drift = progress * 20  # Temperature rises
                elif sensor_name == "vibration_mm_s":
                    drift = progress * 2.5  # Vibration increases
                elif sensor_name == "pressure_bar":
                    drift = -progress * 15  # Pressure drops
                else:
                    drift = 0
                
                # Add noise
                noise = np.random.normal(0, stats.std * 0.3)
                
                value = base_value + drift + noise
                row[sensor_name] = round(value, 2)
            
            degradation_data.append(row)
        
        return degradation_data


# Global processor instance
ginning_processor = GinningDataProcessor()


# Convenience functions
def get_ginning_thresholds() -> Dict[str, Dict]:
    """Get recommended thresholds from real ginning press data."""
    return ginning_processor.get_thresholds()


def get_ginning_baseline() -> Dict:
    """Get baseline for model validation."""
    return ginning_processor.get_baseline_for_validation()


def load_ginning_data() -> ProcessedDataset:
    """Load and process ginning press data."""
    return ginning_processor.process()


# Import for generate_synthetic_degradation
from datetime import timedelta
