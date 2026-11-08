"""
Scheduled Grok Data Generator Service.
Generates sensor data for all machines every 1 minute using Grok AI.
"""

import asyncio
import random
from typing import Dict, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from config import get_settings
from database import SessionLocal
from models.machine import Machine
from models.sensor_reading import SensorReading
from simulation.grok_client import grok_client
from simulation.presets import get_machine_preset
from websocket.manager import ConnectionManager
from engine.monitoring_engine import MonitoringEngine
from alerts.alert_manager import alert_manager
from ai.gemini_client import gemini_client

settings = get_settings()

TIER_STATUS = {1: "normal", 2: "trending", 3: "critical"}


def _normal_bounds(normal: Dict) -> Tuple[Optional[float], Optional[float]]:
    """Normal ranges are stored as {low, high}; machines created from the dashboard may use {min, max}."""
    return normal.get("low", normal.get("min")), normal.get("high", normal.get("max"))


def compute_health(sensor_values: Dict, thresholds: Dict, normal_ranges: Dict) -> Tuple[float, float]:
    """Health score and failure probability (both 0-100) from how far sensors sit outside their normal range."""
    total_deviation = 0
    sensor_count = 0

    for sensor, value in sensor_values.items():
        if sensor not in thresholds:
            continue
        threshold = thresholds[sensor]
        max_val = threshold.get("max", value * 1.2)
        min_val = threshold.get("min", value * 0.8)

        # Calculate deviation from normal range
        normal_low, normal_high = _normal_bounds(normal_ranges.get(sensor, {}))
        if normal_high is None:
            normal_high = max_val * 0.9
        if normal_low is None:
            normal_low = min_val * 1.1

        if value > normal_high:
            span = max_val - normal_high
            deviation = (value - normal_high) / span if span > 0 else 1.0
        elif value < normal_low:
            span = normal_low - min_val
            deviation = (normal_low - value) / span if span > 0 else 1.0
        else:
            deviation = 0

        total_deviation += min(deviation, 1.0)
        sensor_count += 1

    if sensor_count == 0:
        return 100.0, 0.0
    avg_deviation = total_deviation / sensor_count
    health = max(0, min(100, 100 - (avg_deviation * 100)))
    failure_probability = min(100, avg_deviation * 100 * 1.5)
    return round(health, 1), round(failure_probability, 1)


class ScheduledGrokGenerator:
    """
    Background service that generates sensor data for all machines every 1 minute.
    Uses Grok AI for physics-based degradation simulation.
    """

    def __init__(self, connection_manager: Optional[ConnectionManager] = None):
        self.connection_manager = connection_manager
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.interval_seconds = settings.SCHEDULER_INTERVAL_SECONDS
        self.force_critical_every = settings.DEMO_FORCE_CRITICAL_EVERY
        self.machine_states: Dict[str, Dict] = {}  # Track current state per machine
        # One engine per machine so tier detection keeps its reading history between runs
        self.engines: Dict[str, MonitoringEngine] = {}

    async def start(self):
        """Start the scheduled generator."""
        if self.running:
            return

        self.running = True
        self.task = asyncio.create_task(self._generation_loop())
        print(f"[GrokScheduler] Started - generating data every {self.interval_seconds}s")

    async def stop(self):
        """Stop the scheduled generator."""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        print("[GrokScheduler] Stopped")

    async def _generation_loop(self):
        """Main loop that generates data every interval."""
        while self.running:
            try:
                await self._generate_for_all_machines()
            except Exception as e:
                print(f"[GrokScheduler] Error in generation loop: {e}")

            # Wait for next interval
            await asyncio.sleep(self.interval_seconds)

    async def _generate_for_all_machines(self):
        """Generate sensor data for all active machines."""
        db = SessionLocal()
        try:
            # Get all machines from database
            machines = db.query(Machine).all()

            if not machines:
                print("[GrokScheduler] No machines found")
                return

            print(f"[GrokScheduler] Generating data for {len(machines)} machines...")

            for machine in machines:
                await self._generate_for_machine(db, machine)

            print(f"[GrokScheduler] Generation complete for {len(machines)} machines")

        finally:
            db.close()

    def _init_state(self, db: Session, machine: Machine) -> Dict:
        """Resume from the machine's latest stored reading, or start from its normal ranges."""
        latest = db.query(SensorReading).filter(
            SensorReading.machine_id == machine.id
        ).order_by(SensorReading.timestamp.desc()).first()

        return {
            "reading_count": latest.reading_number if latest else 0,
            "degradation_factor": latest.degradation_factor if latest else 1.0,
            "current_values": dict(latest.sensor_values) if latest and latest.sensor_values else self._get_initial_values(machine),
            "tier": machine.current_tier or 1,
            "thresholds": machine.thresholds or {},
            "normal_ranges": machine.normal_ranges or {}
        }

    async def _generate_for_machine(self, db: Session, machine: Machine, force_critical: bool = False):
        """Generate sensor data for a single machine using Grok."""
        try:
            machine_id = machine.machine_id

            # Get or initialize machine state
            if machine_id not in self.machine_states:
                self.machine_states[machine_id] = self._init_state(db, machine)

            state = self.machine_states[machine_id]
            state["thresholds"] = machine.thresholds or {}
            state["normal_ranges"] = machine.normal_ranges or {}
            state["reading_count"] += 1

            # Increase degradation factor slowly over time
            if state["reading_count"] % 10 == 0:
                state["degradation_factor"] += 0.05

            # Generate data using Grok
            generated = await grok_client.generate_sensor_data(
                machine_type=machine.type,
                current_values=state["current_values"],
                degradation_factor=state["degradation_factor"],
                reading_number=state["reading_count"]
            )
            new_values = self._sanitize_values(machine, generated, state["current_values"])

            # Optionally force critical values to exercise the alert pipeline
            if force_critical or (self.force_critical_every and state["reading_count"] % self.force_critical_every == 0):
                for sensor, limits in (machine.thresholds or {}).items():
                    critical, max_val = limits.get("critical"), limits.get("max")
                    if sensor in new_values and critical is not None and max_val is not None and critical > max_val:
                        new_values[sensor] = float(critical)
                print(f"[GrokScheduler] {machine.name}: FORCED CRITICAL VALUES for alert testing")

            # Update state with new values
            state["current_values"] = new_values

            # Update machine status
            machine.last_reading_at = datetime.utcnow()
            self._update_machine_health(machine, new_values)

            # Run 3-tier monitoring analysis
            result = await self._run_monitoring_analysis(db, machine, new_values)
            tier = result.get("tier", {}) if result else {}
            state["tier"] = machine.current_tier
            machine.status = TIER_STATUS.get(machine.current_tier, "normal")

            # Store in database
            sensor_reading = SensorReading(
                machine_id=machine.id,
                timestamp=datetime.utcnow(),
                data_source="grok" if grok_client.api_key else "local",
                reading_number=state["reading_count"],
                degradation_factor=state["degradation_factor"],
                sensor_values=new_values,
                tier_level=machine.current_tier,
                tier_label=self._get_tier_label(machine.current_tier),
                consecutive_rises=tier.get("consecutive_rises", 0),
                rising_metric=tier.get("rising_metric"),
                health_score=machine.health_score,
                failure_probability=machine.failure_probability
            )
            db.add(sensor_reading)

            db.commit()

            # Broadcast via WebSocket if available
            if self.connection_manager:
                await self._broadcast_data(machine, new_values, state)

            print(f"[GrokScheduler] {machine.name}: Generated reading #{state['reading_count']}")

        except Exception as e:
            print(f"[GrokScheduler] Error generating for {machine.name}: {e}")
            db.rollback()

    def _sanitize_values(self, machine: Machine, generated: Dict, previous: Dict) -> Dict:
        """Keep the previous sensor set, accept only numeric values, and clamp runaway drift to plausible limits."""
        values = {}
        for sensor, old_value in previous.items():
            try:
                value = float(generated.get(sensor, old_value))
            except (TypeError, ValueError, AttributeError):
                value = float(old_value)

            limits = (machine.thresholds or {}).get(sensor, {})
            if "min" in limits:
                value = max(value, limits["min"])
            if "critical" in limits and "max" in limits:
                value = min(value, max(limits["critical"], limits["max"]) * 1.25)
            values[sensor] = round(value, 2)
        return values

    def _get_initial_values(self, machine: Machine) -> Dict:
        """Get initial sensor values based on machine preset or config."""
        # Start each sensor in the middle of its normal operating range
        values = {}
        for sensor, normal in (machine.normal_ranges or {}).items():
            low, high = _normal_bounds(normal)
            if low is not None and high is not None:
                values[sensor] = round((low + high) / 2, 2)
        if values:
            return values

        # Try to get from preset
        preset = get_machine_preset(machine.type)
        if preset and "degradation_profile" in preset:
            return {
                sensor: profile["base"]
                for sensor, profile in preset["degradation_profile"].items()
            }

        # Fallback: use machine's sensor configuration
        if machine.thresholds:
            sensors = list(machine.thresholds.keys())
            return {sensor: 50.0 for sensor in sensors}  # Default base value

        # Ultimate fallback
        return {"temperature": 75.0, "vibration": 2.0, "rpm": 3000, "pressure": 90.0}

    def _update_machine_health(self, machine: Machine, sensor_values: Dict):
        """Update machine health score based on sensor values."""
        if not machine.thresholds:
            return
        machine.health_score, machine.failure_probability = compute_health(
            sensor_values, machine.thresholds, machine.normal_ranges or {}
        )

    async def live_snapshot(self, machine_id: str) -> Optional[Dict]:
        """Latest simulated state plus small sensor noise, for the 2-second WebSocket stream."""
        state = self.machine_states.get(machine_id)
        if state is None:
            db = SessionLocal()
            try:
                machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
                if not machine:
                    return None
                state = self.machine_states[machine_id] = self._init_state(db, machine)
            finally:
                db.close()

        sensors = {}
        for sensor, value in state["current_values"].items():
            low, high = _normal_bounds(state["normal_ranges"].get(sensor, {}))
            width = (high - low) if low is not None and high is not None and high > low else abs(value) or 1
            sensors[sensor] = round(value + random.gauss(0, width * 0.01), 2)

        health, failure_probability = compute_health(sensors, state["thresholds"], state["normal_ranges"])
        return {
            "machine_id": machine_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data_source": "live",
            "sensors": sensors,
            "reading_number": state["reading_count"],
            "degradation_factor": state["degradation_factor"],
            "health_score": health,
            "failure_probability": failure_probability,
            "tier": {
                "level": state["tier"],
                "label": self._get_tier_label(state["tier"])
            }
        }

    async def _broadcast_data(self, machine: Machine, sensor_values: Dict, state: Dict):
        """Broadcast generated data via WebSocket."""
        if not self.connection_manager:
            return

        data = {
            "machine_id": machine.machine_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data_source": "grok",
            "sensors": sensor_values,
            "reading_number": state["reading_count"],
            "degradation_factor": state["degradation_factor"],
            "health_score": machine.health_score,
            "failure_probability": machine.failure_probability,
            "tier": {
                "level": machine.current_tier,
                "label": self._get_tier_label(machine.current_tier)
            }
        }

        await self.connection_manager.send_to_machine_subscribers(
            machine.machine_id, data
        )

    def _get_tier_label(self, tier_level: int) -> str:
        """Get tier label from level."""
        labels = {1: "NORMAL", 2: "TRENDING", 3: "CRITICAL"}
        return labels.get(tier_level, "UNKNOWN")

    async def trigger_immediate(self, machine_id: Optional[str] = None):
        """Trigger immediate generation for one or all machines."""
        db = SessionLocal()
        try:
            if machine_id:
                machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
                if machine:
                    await self._generate_for_machine(db, machine)
            else:
                await self._generate_for_all_machines()
        finally:
            db.close()

    async def _run_monitoring_analysis(self, db: Session, machine: Machine, sensor_values: Dict) -> Optional[Dict]:
        """Run 3-tier monitoring and trigger alerts if critical."""
        try:
            engine = self.engines.get(machine.machine_id)
            if engine is None:
                engine = self.engines[machine.machine_id] = MonitoringEngine(
                    machine_id=machine.machine_id,
                    thresholds=machine.thresholds or {},
                    normal_ranges=machine.normal_ranges or {}
                )

            # Build reading
            reading = {
                'timestamp': datetime.utcnow().isoformat(),
                'sensors': sensor_values
            }

            # Process through 3-tier system
            result = engine.process_reading(reading)

            # Update machine tier
            machine.current_tier = result['tier']['level']

            # Check if Gemini was triggered (Tier 3 - Critical)
            if result.get('gemini_triggered'):
                # An alert is already open for this machine; don't spend Gemini quota re-diagnosing it
                if alert_manager.confirmation_filter.get_confirmed(machine.machine_id):
                    return result

                print(f"[GrokScheduler] {machine.name}: TIER 3 CRITICAL - Triggering Gemini diagnosis")

                # Get diagnosis from Gemini
                diagnosis = await gemini_client.diagnose_failure(
                    machine_id=machine.machine_id,
                    machine_type=machine.type,
                    sensor_data=sensor_values,
                    tier_info=result['tier']
                )

                # Process through alert manager (2-confirmation system)
                alert_manager.db = db
                alert_result = await alert_manager.process_diagnosis(
                    machine_id=machine.machine_id,
                    diagnosis=diagnosis,
                    sensor_data=sensor_values
                )

                print(f"[GrokScheduler] Alert result: {alert_result['status']}")

            return result

        except Exception as e:
            print(f"[GrokScheduler] Monitoring analysis error: {e}")
            return None

    def get_status(self) -> Dict:
        """Get current scheduler status."""
        return {
            "running": self.running,
            "interval_seconds": self.interval_seconds,
            "machines_tracked": len(self.machine_states),
            "machine_ids": list(self.machine_states.keys())
        }


# Global scheduler instance
scheduled_grok_generator = ScheduledGrokGenerator()
