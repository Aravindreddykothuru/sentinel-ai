from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


class TierLevel(Enum):
    NORMAL = 1
    TRENDING = 2
    CRITICAL = 3


@dataclass
class TierResult:
    level: TierLevel
    label: str
    consecutive_rises: int
    rising_metric: Optional[str]
    reason: str


class TierDetector:
    """
    3-Tier Monitoring Engine
    - Tier 1 (Normal): Values within normal range, no AI call
    - Tier 2 (Trending): 5+ consecutive rises in any metric, no AI call
    - Tier 3 (Critical): Approaching thresholds, triggers Gemini diagnosis
    """
    
    def __init__(self, thresholds: Dict, normal_ranges: Dict):
        self.thresholds = thresholds
        self.normal_ranges = normal_ranges
        self.reading_history: List[Dict] = []
        self.max_history = 20  # Keep last 20 readings for trend analysis
    
    def add_reading(self, reading: Dict) -> TierResult:
        """Add a new sensor reading and determine tier."""
        self.reading_history.append(reading)
        if len(self.reading_history) > self.max_history:
            self.reading_history.pop(0)
        
        return self._determine_tier(reading)
    
    def _determine_tier(self, reading: Dict) -> TierResult:
        """Determine the current tier based on sensor data."""
        sensors = reading.get('sensors', reading)  # Handle both formats
        
        # Check for critical conditions first (Tier 3)
        critical_check = self._check_critical_thresholds(sensors)
        if critical_check:
            return TierResult(
                level=TierLevel.CRITICAL,
                label="CRITICAL",
                consecutive_rises=0,
                rising_metric=critical_check[0],
                reason=f"{critical_check[0]} approaching critical threshold: {critical_check[1]}"
            )
        
        # Check for trending (Tier 2) - requires at least 5 readings
        if len(self.reading_history) >= 5:
            trend_check = self._check_trending()
            if trend_check:
                return TierResult(
                    level=TierLevel.TRENDING,
                    label="TRENDING",
                    consecutive_rises=trend_check[1],
                    rising_metric=trend_check[0],
                    reason=f"{trend_check[0]} rising for {trend_check[1]} consecutive readings"
                )
        
        # Default to normal (Tier 1)
        return TierResult(
            level=TierLevel.NORMAL,
            label="NORMAL",
            consecutive_rises=0,
            rising_metric=None,
            reason="All sensors within normal operating ranges"
        )
    
    def _check_critical_thresholds(self, sensors: Dict) -> Optional[Tuple[str, float]]:
        """Check if any sensor is approaching critical thresholds."""
        for metric, value in sensors.items():
            if metric not in self.thresholds:
                continue
            
            threshold_config = self.thresholds[metric]
            critical = threshold_config.get('critical')
            max_val = threshold_config.get('max')
            min_val = threshold_config.get('min')
            
            if critical is None:
                continue
            
            # Check if approaching critical (within 10% of threshold)
            if isinstance(critical, (int, float)):
                if critical > max_val:  # Upper threshold (e.g., temperature)
                    warning_threshold = critical * 0.90  # 90% of critical
                    if value >= warning_threshold:
                        return (metric, value)
                else:  # Lower threshold (e.g., pressure)
                    warning_threshold = critical * 1.10  # 110% of critical
                    if value <= warning_threshold:
                        return (metric, value)
        
        return None
    
    def _check_trending(self) -> Optional[Tuple[str, int]]:
        """Check for 5+ consecutive rises in any metric."""
        if len(self.reading_history) < 5:
            return None
        
        # Get last 5 readings
        recent = self.reading_history[-5:]
        
        # Check each metric
        metrics = ['temperature', 'vibration', 'rpm', 'pressure']
        
        for metric in metrics:
            consecutive_rises = 0
            for i in range(1, len(recent)):
                prev_val = recent[i-1].get('sensors', recent[i-1]).get(metric, 0)
                curr_val = recent[i].get('sensors', recent[i]).get(metric, 0)
                
                if curr_val > prev_val:
                    consecutive_rises += 1
                else:
                    break
            
            if consecutive_rises >= 4:  # 5 readings = 4 consecutive rises
                return (metric, consecutive_rises + 1)
        
        return None
    
    def should_trigger_gemini(self, tier_result: TierResult) -> bool:
        """Determine if current tier should trigger Gemini diagnosis."""
        return tier_result.level == TierLevel.CRITICAL
    
    def get_tier_level_number(self, tier_result: TierResult) -> int:
        """Get numeric tier level (1, 2, or 3)."""
        return tier_result.level.value
    
    def clear_history(self):
        """Clear reading history."""
        self.reading_history = []
