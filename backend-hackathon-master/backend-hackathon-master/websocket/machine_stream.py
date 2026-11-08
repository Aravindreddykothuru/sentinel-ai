import asyncio
import json
from typing import Awaitable, Callable, Dict, Optional
from datetime import datetime
from websocket.manager import ConnectionManager


DataGenerator = Callable[[str], Awaitable[Optional[dict]]]


class MachineStreamManager:
    """Manages real-time streaming of machine sensor data via WebSockets."""

    def __init__(self, connection_manager: ConnectionManager, data_generator: Optional[DataGenerator] = None, update_interval: float = 2):
        self.manager = connection_manager
        self.data_generator = data_generator
        self.active_streams: Dict[str, asyncio.Task] = {}
        self.machine_data: Dict[str, dict] = {}
        self.update_interval = update_interval  # seconds

    async def start_machine_stream(self, machine_id: str, data_generator: Optional[DataGenerator] = None):
        """Start streaming data for a specific machine."""
        if machine_id in self.active_streams:
            return  # Already streaming

        task = asyncio.create_task(
            self._stream_machine_data(machine_id, data_generator or self.data_generator)
        )
        self.active_streams[machine_id] = task
        print(f"Started stream for machine {machine_id}")

    async def stop_machine_stream(self, machine_id: str):
        """Stop streaming data for a specific machine."""
        if machine_id in self.active_streams:
            self.active_streams[machine_id].cancel()
            del self.active_streams[machine_id]
            print(f"Stopped stream for machine {machine_id}")

    async def stop_all(self):
        """Cancel every running stream (used on shutdown)."""
        for machine_id in list(self.active_streams):
            await self.stop_machine_stream(machine_id)

    async def _stream_machine_data(self, machine_id: str, data_generator: Optional[DataGenerator] = None):
        """Background task that sends machine data every 2 seconds."""
        try:
            while True:
                # A failing tick must not kill the stream: it stays registered in
                # active_streams and would never be restarted
                try:
                    if self.manager.has_subscribers(machine_id):
                        if data_generator:
                            data = await data_generator(machine_id)
                        else:
                            data = self._generate_mock_data(machine_id)

                        if data:
                            # Store latest data
                            self.machine_data[machine_id] = data

                            # Send to all subscribers
                            await self.manager.send_to_machine_subscribers(machine_id, data)
                except Exception as e:
                    print(f"Error in machine stream {machine_id}: {e}")

                # Wait for next update
                await asyncio.sleep(self.update_interval)

        except asyncio.CancelledError:
            print(f"Stream cancelled for machine {machine_id}")

    def _generate_mock_data(self, machine_id: str) -> dict:
        """Generate mock sensor data for testing."""
        import random

        return {
            "machine_id": machine_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data_source": "local",
            "sensors": {
                "temperature": round(random.uniform(75, 95), 1),
                "vibration": round(random.uniform(1.5, 4.5), 2),
                "rpm": random.randint(2800, 3200),
                "pressure": round(random.uniform(80, 110), 1)
            },
            "tier": {
                "level": 1,
                "label": "NORMAL",
                "consecutive_rises": 0,
                "rising_metric": None
            },
            "health_score": round(random.uniform(85, 100), 1),
            "failure_probability": round(random.uniform(0, 15), 1),
            "reading_number": 0,
            "degradation_factor": 1.0
        }

    def get_latest_data(self, machine_id: str) -> Optional[dict]:
        """Get the latest data for a machine."""
        return self.machine_data.get(machine_id)

    async def broadcast_to_all(self, data: dict):
        """Broadcast data to all connected clients."""
        await self.manager.broadcast_json(data)

    def is_streaming(self, machine_id: str) -> bool:
        """Check if a machine is currently being streamed."""
        return machine_id in self.active_streams

    def get_active_streams(self) -> list:
        """Get list of machine IDs currently being streamed."""
        return list(self.active_streams.keys())
