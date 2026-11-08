from fastapi import WebSocket
from typing import Dict, List
import json


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.machine_subscribers: Dict[str, List[str]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        print(f"Client {client_id} connected. Total: {len(self.active_connections)}")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        # Remove from machine subscriptions
        for machine_id, subscribers in self.machine_subscribers.items():
            if client_id in subscribers:
                subscribers.remove(client_id)
        print(f"Client {client_id} disconnected. Total: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(message)
            except Exception:
                # Socket closed underneath us; drop the client instead of failing the caller
                self.disconnect(client_id)

    async def send_json_message(self, data: dict, client_id: str):
        await self.send_personal_message(json.dumps(data), client_id)

    async def broadcast(self, message: str):
        for client_id in list(self.active_connections):
            await self.send_personal_message(message, client_id)

    async def broadcast_json(self, data: dict):
        await self.broadcast(json.dumps(data))

    def subscribe_to_machine(self, client_id: str, machine_id: str):
        if machine_id not in self.machine_subscribers:
            self.machine_subscribers[machine_id] = []
        if client_id not in self.machine_subscribers[machine_id]:
            self.machine_subscribers[machine_id].append(client_id)
            print(f"[WS] Client {client_id} subscribed to {machine_id}. Subscribers: {self.machine_subscribers[machine_id]}")

    def unsubscribe_from_machine(self, client_id: str, machine_id: str):
        if machine_id in self.machine_subscribers and client_id in self.machine_subscribers[machine_id]:
            self.machine_subscribers[machine_id].remove(client_id)

    def has_subscribers(self, machine_id: str) -> bool:
        return bool(self.machine_subscribers.get(machine_id))

    async def send_to_machine_subscribers(self, machine_id: str, data: dict):
        message = json.dumps(data)
        # Copy: a failed send disconnects the client, which mutates the list
        for client_id in list(self.machine_subscribers.get(machine_id, [])):
            await self.send_personal_message(message, client_id)
