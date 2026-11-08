"""
Ginning Press Machine Validation API for SENTINEL AI.
Uses real sensor data for model validation and threshold calibration.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional

from services.ginning_data_processor import (
    ginning_processor,
    get_ginning_thresholds,
    get_ginning_baseline
)

router = APIRouter(prefix="/ginning-validation", tags=["ginning-validation"])


@router.get("/baseline")
def get_baseline_statistics():
    """
    Get baseline statistics from real ginning press data.
    
    Returns statistical analysis of 200 normal operation readings
    including means, standard deviations, and recommended thresholds.
    """
    try:
        baseline = get_ginning_baseline()
        return {
            "status": "success",
            "data_source": "ginning_press_machine_normal_200_rows.csv",
            **baseline
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load baseline: {str(e)}")


@router.get("/thresholds")
def get_recommended_thresholds():
    """
    Get recommended thresholds based on real data percentiles.
    
    Uses 5th/95th percentile for normal range,
    1st/99th percentile for critical thresholds.
    """
    try:
        thresholds = get_ginning_thresholds()
        return {
            "status": "success",
            "machine_type": "ginning_press",
            "thresholds": thresholds,
            "methodology": "Percentile-based (5th/95th normal, 1st/99th critical)"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate thresholds: {str(e)}")


@router.get("/sensor-stats/{sensor_name}")
def get_sensor_statistics(sensor_name: str):
    """Get detailed statistics for a specific sensor."""
    try:
        processor = ginning_processor
        if not processor.processed_data:
            processor.process()
        
        if sensor_name not in processor.processed_data.sensor_stats:
            raise HTTPException(status_code=404, detail=f"Sensor '{sensor_name}' not found")
        
        stats = processor.processed_data.sensor_stats[sensor_name]
        
        return {
            "status": "success",
            "sensor": sensor_name,
            "statistics": {
                "mean": round(stats.mean, 2),
                "std": round(stats.std, 2),
                "min": round(stats.min, 2),
                "max": round(stats.max, 2),
                "percentiles": {
                    "p1": round(stats.p1, 2),
                    "p5": round(stats.p5, 2),
                    "p95": round(stats.p95, 2),
                    "p99": round(stats.p99, 2)
                },
                "unit": stats.unit
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.get("/correlations")
def get_sensor_correlations():
    """Get correlation matrix between sensors."""
    try:
        processor = ginning_processor
        if not processor.processed_data:
            processor.process()
        
        return {
            "status": "success",
            "correlations": processor.processed_data.sensor_correlations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get correlations: {str(e)}")


@router.get("/anomalies")
def detect_anomalies():
    """Detect anomalous readings in the dataset."""
    try:
        processor = ginning_processor
        if not processor.processed_data:
            processor.process()
        
        anomalies = processor.detect_anomalies_in_data()
        
        return {
            "status": "success",
            "total_readings": processor.processed_data.total_readings,
            "anomalies_detected": len(anomalies),
            "anomaly_rate": round(len(anomalies) / processor.processed_data.total_readings * 100, 2),
            "anomalies": anomalies[:10]  # Limit to first 10
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to detect anomalies: {str(e)}")


@router.get("/validate-prediction")
def validate_prediction_against_real_data(
    sensor_name: str,
    predicted_value: float
):
    """
    Validate a prediction against real data distribution.
    
    Returns how many standard deviations the prediction is from mean,
    and whether it falls within normal operating range.
    """
    try:
        processor = ginning_processor
        if not processor.processed_data:
            processor.process()
        
        if sensor_name not in processor.processed_data.sensor_stats:
            raise HTTPException(status_code=404, detail=f"Sensor '{sensor_name}' not found")
        
        stats = processor.processed_data.sensor_stats[sensor_name]
        
        # Calculate deviation
        deviation = predicted_value - stats.mean
        sigma_deviation = deviation / stats.std if stats.std > 0 else 0
        
        # Check against thresholds
        is_normal = stats.recommended_min <= predicted_value <= stats.recommended_max
        is_critical = predicted_value < stats.recommended_critical_low or predicted_value > stats.recommended_critical_high
        
        return {
            "status": "success",
            "sensor": sensor_name,
            "prediction": predicted_value,
            "baseline_mean": round(stats.mean, 2),
            "baseline_std": round(stats.std, 2),
            "deviation_from_mean": round(deviation, 2),
            "deviation_sigma": round(sigma_deviation, 2),
            "within_normal_range": is_normal,
            "is_critical": is_critical,
            "assessment": "normal" if is_normal else "critical" if is_critical else "warning"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.get("/dataset-info")
def get_dataset_info():
    """Get information about the ginning press dataset."""
    try:
        processor = ginning_processor
        if not processor.processed_data:
            processor.process()
        
        return {
            "status": "success",
            "dataset": {
                "name": "Ginning Press Machine - Normal Operation",
                "file": "ginning_press_machine_normal_200_rows.csv",
                "total_readings": processor.processed_data.total_readings,
                "sensors": list(processor.processed_data.sensor_stats.keys()),
                "time_range": {
                    "start": processor.processed_data.time_range[0].isoformat(),
                    "end": processor.processed_data.time_range[1].isoformat()
                },
                "duration_minutes": (processor.processed_data.time_range[1] - processor.processed_data.time_range[0]).total_seconds() / 60,
                "data_quality_score": round(processor.processed_data.data_quality_score, 2)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dataset info: {str(e)}")


@router.post("/compare-with-synthetic")
def compare_with_synthetic_data():
    """
    Compare synthetic Grok-generated data against real data.
    
    Returns statistics comparing the distributions.
    """
    try:
        processor = ginning_processor
        if not processor.processed_data:
            processor.process()
        
        comparison = {}
        
        for sensor_name, stats in processor.processed_data.sensor_stats.items():
            # These would be populated from actual synthetic data comparison
            comparison[sensor_name] = {
                "real_mean": round(stats.mean, 2),
                "real_std": round(stats.std, 2),
                "synthetic_mean": None,  # To be filled
                "synthetic_std": None,   # To be filled
                "mean_difference": None,
                "std_difference": None,
                "distribution_match": None
            }
        
        return {
            "status": "success",
            "comparison": comparison,
            "note": "Synthetic data comparison requires running synthetic data generation"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")
