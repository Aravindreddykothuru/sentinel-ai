from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from statistics import mean, stdev
import math


@dataclass
class TrendAnalysis:
    metric: str
    trend_direction: str  # 'rising', 'falling', 'stable'
    slope: float  # Rate of change per reading
    volatility: float  # Standard deviation
    prediction: Optional[float]  # Predicted value in 10 readings
    confidence: float  # 0-100


class TrendAnalyzer:
    """
    Analyzes sensor trends using statistical methods.
    Used by Tier 2 (Trending) to detect degradation patterns.
    """
    
    def __init__(self, history: List[Dict] = None):
        self.history = history or []
        self.min_samples = 5
    
    def add_reading(self, reading: Dict):
        """Add a reading to history."""
        self.history.append(reading)
        if len(self.history) > 50:  # Keep last 50 readings
            self.history.pop(0)
    
    def analyze_metric(self, metric: str) -> Optional[TrendAnalysis]:
        """Analyze trend for a specific metric."""
        if len(self.history) < self.min_samples:
            return None
        
        # Extract values for the metric
        values = []
        for reading in self.history:
            sensors = reading.get('sensors', reading)
            val = sensors.get(metric)
            if val is not None:
                values.append(val)
        
        if len(values) < self.min_samples:
            return None
        
        # Calculate trend using linear regression
        slope = self._calculate_slope(values)
        volatility = self._calculate_volatility(values)
        
        # Determine direction
        if slope > 0.01:
            direction = 'rising'
        elif slope < -0.01:
            direction = 'falling'
        else:
            direction = 'stable'
        
        # Predict future value
        prediction = self._predict_next(values, slope)
        
        # Calculate confidence based on data quality
        confidence = self._calculate_confidence(values, volatility)
        
        return TrendAnalysis(
            metric=metric,
            trend_direction=direction,
            slope=slope,
            volatility=volatility,
            prediction=prediction,
            confidence=confidence
        )
    
    def analyze_all_metrics(self) -> Dict[str, TrendAnalysis]:
        """Analyze trends for all available metrics."""
        metrics = ['temperature', 'vibration', 'rpm', 'pressure']
        results = {}
        
        for metric in metrics:
            analysis = self.analyze_metric(metric)
            if analysis:
                results[metric] = analysis
        
        return results
    
    def _calculate_slope(self, values: List[float]) -> float:
        """Calculate slope using simple linear regression."""
        n = len(values)
        if n < 2:
            return 0.0
        
        x_mean = (n - 1) / 2
        y_mean = mean(values)
        
        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def _calculate_volatility(self, values: List[float]) -> float:
        """Calculate volatility as standard deviation."""
        if len(values) < 2:
            return 0.0
        
        try:
            return stdev(values)
        except:
            return 0.0
    
    def _predict_next(self, values: List[float], slope: float, steps: int = 10) -> float:
        """Predict value after N more readings."""
        if not values:
            return 0.0
        
        last_value = values[-1]
        return last_value + (slope * steps)
    
    def _calculate_confidence(self, values: List[float], volatility: float) -> float:
        """Calculate confidence score (0-100) based on data quality."""
        if len(values) < 5:
            return 50.0
        
        # More data = higher confidence
        sample_confidence = min(100, len(values) * 2)
        
        # Lower volatility = higher confidence
        if volatility == 0:
            volatility_confidence = 100
        else:
            mean_val = mean(values)
            cv = volatility / mean_val if mean_val != 0 else 1  # Coefficient of variation
            volatility_confidence = max(0, 100 - (cv * 100))
        
        # Average the two
        return round((sample_confidence + volatility_confidence) / 2, 1)
    
    def detect_anomaly(self, metric: str, current_value: float) -> bool:
        """Detect if current value is anomalous based on history."""
        if len(self.history) < 10:
            return False
        
        values = []
        for reading in self.history[:-1]:  # Exclude current
            sensors = reading.get('sensors', reading)
            val = sensors.get(metric)
            if val is not None:
                values.append(val)
        
        if len(values) < 10:
            return False
        
        mean_val = mean(values)
        std_val = stdev(values) if len(values) > 1 else 0
        
        if std_val == 0:
            return False
        
        # Z-score > 3 is considered anomalous
        z_score = abs(current_value - mean_val) / std_val
        return z_score > 3
    
    def get_health_score(self) -> float:
        """Calculate overall health score (0-100) based on trends."""
        if len(self.history) < 5:
            return 100.0
        
        analyses = self.analyze_all_metrics()
        if not analyses:
            return 100.0
        
        scores = []
        for analysis in analyses.values():
            # Start at 100
            score = 100.0
            
            # Penalize rising trends
            if analysis.trend_direction == 'rising':
                score -= min(30, abs(analysis.slope) * 10)
            
            # Penalize high volatility
            score -= min(20, analysis.volatility * 5)
            
            scores.append(max(0, score))
        
        return round(mean(scores), 1) if scores else 100.0
