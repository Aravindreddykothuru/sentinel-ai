"""
Optimal Maintenance Window Calculator for SENTINEL AI.
Advanced algorithm that balances failure urgency, production impact,
parts availability, and mechanic availability.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import math


@dataclass
class WindowScore:
    """Score breakdown for a maintenance window."""
    start_time: datetime
    end_time: datetime
    overall_score: float  # 0-100
    urgency_score: float  # Based on time to failure
    production_score: float  # Based on production impact
    availability_score: float  # Based on parts/mechanic availability
    confidence: float  # Algorithm confidence
    reasoning: List[str]  # Why this score was given


class OptimalWindowCalculator:
    """
    Calculates optimal maintenance windows using multi-factor analysis.
    
    Factors considered:
    1. Failure urgency (time to predicted failure)
    2. Production impact (shift schedules, demand)
    3. Resource availability (parts, mechanics, tools)
    4. Historical success rates
    5. Weather/external factors (optional)
    """
    
    def __init__(
        self,
        production_value_per_hour: float = 10000,
        emergency_cost_multiplier: float = 10.0,
        max_lookahead_days: int = 14
    ):
        self.production_value_per_hour = production_value_per_hour
        self.emergency_cost_multiplier = emergency_cost_multiplier
        self.max_lookahead_days = max_lookahead_days
        
        # Scoring weights (can be adjusted)
        self.weights = {
            'urgency': 0.35,
            'production': 0.30,
            'availability': 0.20,
            'historical': 0.15
        }
    
    def calculate_optimal_windows(
        self,
        machine_id: str,
        predicted_failure_time: datetime,
        shift_schedule: Dict,
        parts_available: bool = True,
        mechanic_available: bool = True,
        maintenance_duration_hours: float = 2.5,
        existing_schedules: List[Tuple[datetime, datetime]] = None
    ) -> List[WindowScore]:
        """
        Calculate and rank optimal maintenance windows.
        
        Args:
            machine_id: Machine identifier
            predicted_failure_time: When failure is predicted
            shift_schedule: Production shift configuration
            parts_available: Whether required parts are in stock
            mechanic_available: Whether mechanic is available
            maintenance_duration_hours: Expected maintenance duration
            existing_schedules: List of (start, end) tuples for existing maintenance
            
        Returns:
            List of WindowScore objects, sorted by overall_score (best first)
        """
        existing_schedules = existing_schedules or []
        windows = []
        
        # Generate candidate windows
        candidates = self._generate_candidate_windows(
            shift_schedule,
            maintenance_duration_hours,
            existing_schedules
        )
        
        for start_time, end_time in candidates:
            # Skip if after predicted failure
            if start_time >= predicted_failure_time:
                continue
            
            # Calculate individual scores
            urgency_score = self._calculate_urgency_score(
                start_time, predicted_failure_time
            )
            
            production_score = self._calculate_production_score(
                start_time, end_time, shift_schedule
            )
            
            availability_score = self._calculate_availability_score(
                parts_available, mechanic_available
            )
            
            historical_score = self._calculate_historical_score(
                machine_id, start_time, shift_schedule
            )
            
            # Calculate weighted overall score
            overall_score = (
                urgency_score * self.weights['urgency'] +
                production_score * self.weights['production'] +
                availability_score * self.weights['availability'] +
                historical_score * self.weights['historical']
            )
            
            # Generate reasoning
            reasoning = self._generate_reasoning(
                urgency_score, production_score, availability_score,
                start_time, predicted_failure_time, shift_schedule
            )
            
            windows.append(WindowScore(
                start_time=start_time,
                end_time=end_time,
                overall_score=round(overall_score, 1),
                urgency_score=round(urgency_score, 1),
                production_score=round(production_score, 1),
                availability_score=round(availability_score, 1),
                confidence=self._calculate_confidence(windows),
                reasoning=reasoning
            ))
        
        # Sort by overall score (descending)
        windows.sort(key=lambda x: x.overall_score, reverse=True)
        
        return windows[:10]  # Return top 10
    
    def _generate_candidate_windows(
        self,
        shift_schedule: Dict,
        duration_hours: float,
        existing_schedules: List[Tuple[datetime, datetime]]
    ) -> List[Tuple[datetime, datetime]]:
        """Generate candidate maintenance windows."""
        candidates = []
        
        shifts = shift_schedule.get('shifts', [])
        maintenance_windows = shift_schedule.get('maintenance_windows', ['13:45', '21:45'])
        weekend_allowed = shift_schedule.get('weekend_maintenance', True)
        
        now = datetime.utcnow()
        
        for day_offset in range(self.max_lookahead_days):
            date = now + timedelta(days=day_offset)
            
            # Skip weekends if not allowed
            if date.weekday() >= 5 and not weekend_allowed:
                continue
            
            # Generate windows for each maintenance slot
            for window_time in maintenance_windows:
                hour, minute = map(int, window_time.split(':'))
                
                start = date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                end = start + timedelta(hours=duration_hours)
                
                # Skip if in the past
                if start < now:
                    continue
                
                # Check for conflicts
                if self._has_conflict(start, end, existing_schedules):
                    continue
                
                candidates.append((start, end))
            
            # Also consider shift changeover times
            for shift in shifts:
                # End of shift is a good maintenance window
                end_hour, end_min = map(int, shift['end'].split(':'))
                start = date.replace(hour=end_hour, minute=end_min, second=0, microsecond=0)
                end = start + timedelta(hours=duration_hours)
                
                if start > now and not self._has_conflict(start, end, existing_schedules):
                    candidates.append((start, end))
        
        return candidates
    
    def _has_conflict(
        self,
        start: datetime,
        end: datetime,
        existing_schedules: List[Tuple[datetime, datetime]]
    ) -> bool:
        """Check if window conflicts with existing schedules."""
        for existing_start, existing_end in existing_schedules:
            if start < existing_end and end > existing_start:
                return True
        return False
    
    def _calculate_urgency_score(
        self,
        window_start: datetime,
        predicted_failure: datetime
    ) -> float:
        """
        Calculate urgency score (0-100).
        Higher score = more urgent to schedule soon.
        """
        time_available = predicted_failure - window_start
        hours_available = time_available.total_seconds() / 3600
        
        if hours_available <= 0:
            return 0  # Too late
        
        if hours_available <= 4:
            return 100  # Critical - less than 4 hours
        elif hours_available <= 8:
            return 90
        elif hours_available <= 24:
            return 80
        elif hours_available <= 48:
            return 70
        elif hours_available <= 72:
            return 60
        else:
            # Gradual decrease after 72 hours
            return max(20, 60 - (hours_available - 72) / 10)
    
    def _calculate_production_score(
        self,
        window_start: datetime,
        window_end: datetime,
        shift_schedule: Dict
    ) -> float:
        """
        Calculate production impact score (0-100).
        Higher score = less production impact.
        """
        shifts = shift_schedule.get('shifts', [])
        
        if not shifts:
            return 100  # No shifts defined = no impact
        
        # Calculate overlap with shifts
        total_shift_minutes = 0
        overlap_minutes = 0
        
        for shift in shifts:
            shift_start = self._time_to_minutes(shift['start'])
            shift_end = self._time_to_minutes(shift['end'])
            
            # Handle overnight shifts
            if shift_end < shift_start:
                shift_end += 24 * 60
            
            shift_duration = shift_end - shift_start
            total_shift_minutes += shift_duration
            
            # Calculate overlap
            window_start_min = window_start.hour * 60 + window_start.minute
            window_end_min = window_end.hour * 60 + window_end.minute
            
            if window_end_min < window_start_min:
                window_end_min += 24 * 60
            
            overlap_start = max(window_start_min, shift_start)
            overlap_end = min(window_end_min, shift_end)
            
            if overlap_end > overlap_start:
                overlap_minutes += overlap_end - overlap_start
        
        # Score based on overlap percentage
        window_duration = (window_end - window_start).total_seconds() / 60
        overlap_percentage = overlap_minutes / window_duration if window_duration > 0 else 0
        
        # Invert: less overlap = higher score
        return max(0, 100 - (overlap_percentage * 100))
    
    def _calculate_availability_score(
        self,
        parts_available: bool,
        mechanic_available: bool
    ) -> float:
        """
        Calculate resource availability score (0-100).
        """
        score = 100
        
        if not parts_available:
            score -= 40
        
        if not mechanic_available:
            score -= 40
        
        return max(0, score)
    
    def _calculate_historical_score(
        self,
        machine_id: str,
        window_start: datetime,
        shift_schedule: Dict
    ) -> float:
        """
        Calculate historical success score (0-100).
        Based on past maintenance success rates for similar conditions.
        """
        # Default score - would be enhanced with actual historical data
        score = 75
        
        # Weekend maintenance might have different success rates
        if window_start.weekday() >= 5:
            # Check if weekend maintenance is typically allowed
            if shift_schedule.get('weekend_maintenance', True):
                score -= 5  # Slight penalty for weekend
            else:
                score -= 30  # Major penalty if not typically done
        
        # Night shifts might have lower success rates
        hour = window_start.hour
        if hour < 6 or hour > 22:
            score -= 10
        
        return max(0, score)
    
    def _calculate_confidence(self, windows: List[WindowScore]) -> float:
        """Calculate confidence in the scoring (0-100)."""
        if len(windows) < 3:
            return 60
        
        # Higher confidence if we have multiple good options
        top_scores = [w.overall_score for w in windows[:3]]
        score_variance = max(top_scores) - min(top_scores)
        
        if score_variance < 10:
            return 85  # Multiple similar good options
        elif score_variance < 20:
            return 75
        else:
            return 90  # Clear winner
    
    def _generate_reasoning(
        self,
        urgency_score: float,
        production_score: float,
        availability_score: float,
        window_start: datetime,
        predicted_failure: datetime,
        shift_schedule: Dict
    ) -> List[str]:
        """Generate human-readable reasoning for the scores."""
        reasoning = []
        
        # Urgency reasoning
        hours_to_failure = (predicted_failure - window_start).total_seconds() / 3600
        if hours_to_failure < 8:
            reasoning.append(f"CRITICAL: Only {hours_to_failure:.1f} hours before predicted failure")
        elif hours_to_failure < 24:
            reasoning.append(f"URGENT: {hours_to_failure:.1f} hours available for maintenance")
        else:
            reasoning.append(f"ADEQUATE TIME: {hours_to_failure:.1f} hours before failure")
        
        # Production reasoning
        if production_score >= 80:
            reasoning.append("MINIMAL PRODUCTION IMPACT: Off-shift or low-demand window")
        elif production_score >= 50:
            reasoning.append("MODERATE IMPACT: Some production overlap")
        else:
            reasoning.append("HIGH IMPACT: Significant production disruption")
        
        # Availability reasoning
        if availability_score >= 80:
            reasoning.append("RESOURCES READY: Parts and mechanics available")
        elif availability_score >= 40:
            reasoning.append("PARTIAL AVAILABILITY: Some resources need confirmation")
        else:
            reasoning.append("RESOURCE CONSTRAINTS: Parts or mechanics not confirmed")
        
        # Time of day reasoning
        hour = window_start.hour
        if 6 <= hour < 18:
            reasoning.append("DAYTIME: Standard working hours")
        elif 18 <= hour < 22:
            reasoning.append("EVENING: Extended hours available")
        else:
            reasoning.append("NIGHT/OFF-HOURS: After-hours maintenance")
        
        return reasoning
    
    def _time_to_minutes(self, time_str: str) -> int:
        """Convert HH:MM to minutes since midnight."""
        hour, minute = map(int, time_str.split(':'))
        return hour * 60 + minute
    
    def get_recommendation_summary(
        self,
        windows: List[WindowScore]
    ) -> Dict:
        """Get a summary recommendation from calculated windows."""
        if not windows:
            return {
                "recommendation": "NO_SUITABLE_WINDOW",
                "message": "No suitable maintenance windows found before predicted failure",
                "action_required": "Consider emergency maintenance or production shutdown"
            }
        
        best = windows[0]
        
        if best.overall_score >= 80:
            recommendation = "OPTIMAL"
            message = "Excellent maintenance window found"
        elif best.overall_score >= 60:
            recommendation = "ACCEPTABLE"
            message = "Good maintenance window with minor trade-offs"
        elif best.overall_score >= 40:
            recommendation = "SUBOPTIMAL"
            message = "Maintenance possible but with significant compromises"
        else:
            recommendation = "EMERGENCY"
            message = "Limited options - consider emergency procedures"
        
        return {
            "recommendation": recommendation,
            "message": message,
            "best_window": {
                "start": best.start_time.isoformat(),
                "end": best.end_time.isoformat(),
                "score": best.overall_score,
                "confidence": best.confidence
            },
            "alternatives_count": len(windows) - 1,
            "top_reasoning": best.reasoning[:3]
        }


# Global calculator instance
window_calculator = OptimalWindowCalculator()
