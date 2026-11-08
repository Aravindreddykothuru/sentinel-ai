from typing import Dict, Optional, Callable
from datetime import datetime

from engine.tier_detector import TierDetector, TierResult, TierLevel
from engine.trend_analyzer import TrendAnalyzer, TrendAnalysis


class MonitoringEngine:
    """
    Main 3-Tier Monitoring Engine that orchestrates:
    - Tier 1 (Normal): No AI calls, basic health checks
    - Tier 2 (Trending): Math-based trend analysis, no AI calls
    - Tier 3 (Critical): Triggers Gemini diagnosis
    """
    
    def __init__(self, machine_id: str, thresholds: Dict, normal_ranges: Dict):
        self.machine_id = machine_id
        self.tier_detector = TierDetector(thresholds, normal_ranges)
        self.trend_analyzer = TrendAnalyzer()
        self.current_tier: Optional[TierResult] = None
        self.gemini_trigger_count = 0
        self.total_readings = 0
        
        # Callback for when Gemini should be triggered
        self.on_gemini_trigger: Optional[Callable] = None
    
    def process_reading(self, reading: Dict) -> Dict:
        """
        Process a new sensor reading through the 3-tier system.
        Returns enriched reading with tier information.
        """
        self.total_readings += 1
        
        # Add to trend analyzer
        self.trend_analyzer.add_reading(reading)
        
        # Determine tier
        tier_result = self.tier_detector.add_reading(reading)
        self.current_tier = tier_result
        
        # Analyze trends (Tier 2 logic)
        trend_analyses = self.trend_analyzer.analyze_all_metrics()
        
        # Calculate health score
        health_score = self.trend_analyzer.get_health_score()
        
        # Calculate failure probability
        failure_probability = self._calculate_failure_probability(
            tier_result, trend_analyses, health_score
        )
        
        # Check if Gemini should be triggered (Tier 3)
        gemini_triggered = False
        if self.tier_detector.should_trigger_gemini(tier_result):
            gemini_triggered = True
            self.gemini_trigger_count += 1
            if self.on_gemini_trigger:
                self.on_gemini_trigger(self.machine_id, reading, tier_result)
        
        # Build enriched reading
        enriched = {
            "machine_id": self.machine_id,
            "timestamp": reading.get('timestamp', datetime.utcnow().isoformat()),
            "sensors": reading.get('sensors', reading),
            "tier": {
                "level": tier_result.level.value,
                "label": tier_result.label,
                "consecutive_rises": tier_result.consecutive_rises,
                "rising_metric": tier_result.rising_metric,
                "reason": tier_result.reason
            },
            "trends": self._format_trends(trend_analyses),
            "health_score": health_score,
            "failure_probability": failure_probability,
            "gemini_triggered": gemini_triggered,
            "total_readings": self.total_readings,
            "gemini_calls": self.gemini_trigger_count
        }
        
        return enriched
    
    def _calculate_failure_probability(
        self, 
        tier_result: TierResult, 
        trend_analyses: Dict[str, TrendAnalysis],
        health_score: float
    ) -> float:
        """Calculate failure probability (0-100)."""
        probability = 0.0
        
        # Base probability from tier
        if tier_result.level == TierLevel.CRITICAL:
            probability += 70
        elif tier_result.level == TierLevel.TRENDING:
            probability += 30
        
        # Adjust based on health score
        probability += (100 - health_score) * 0.3
        
        # Adjust based on trends
        for analysis in trend_analyses.values():
            if analysis.trend_direction == 'rising':
                probability += min(20, abs(analysis.slope) * 5)
            
            # High volatility increases risk
            if analysis.volatility > 5:
                probability += 10
        
        return min(100, round(probability, 1))
    
    def _format_trends(self, trend_analyses: Dict[str, TrendAnalysis]) -> Dict:
        """Format trend analyses for output."""
        formatted = {}
        for metric, analysis in trend_analyses.items():
            formatted[metric] = {
                "direction": analysis.trend_direction,
                "slope": round(analysis.slope, 4),
                "volatility": round(analysis.volatility, 2),
                "prediction": round(analysis.prediction, 2) if analysis.prediction else None,
                "confidence": analysis.confidence
            }
        return formatted
    
    def get_current_tier(self) -> Optional[TierResult]:
        """Get current tier status."""
        return self.current_tier
    
    def get_stats(self) -> Dict:
        """Get engine statistics."""
        return {
            "machine_id": self.machine_id,
            "total_readings": self.total_readings,
            "gemini_triggers": self.gemini_trigger_count,
            "current_tier": self.current_tier.label if self.current_tier else "UNKNOWN",
            "efficiency": self._calculate_efficiency()
        }
    
    def _calculate_efficiency(self) -> float:
        """Calculate API efficiency (lower is better)."""
        if self.total_readings == 0:
            return 0.0
        return round((self.gemini_trigger_count / self.total_readings) * 100, 2)
    
    def reset(self):
        """Reset the engine state."""
        self.tier_detector.clear_history()
        self.trend_analyzer = TrendAnalyzer()
        self.current_tier = None
        self.gemini_trigger_count = 0
        self.total_readings = 0
    
    def set_gemini_callback(self, callback: Callable):
        """Set callback function for Gemini triggers."""
        self.on_gemini_trigger = callback
