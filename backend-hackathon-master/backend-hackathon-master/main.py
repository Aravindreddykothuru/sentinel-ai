import json
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import get_settings
from database import init_db, SessionLocal
from websocket.manager import ConnectionManager
from websocket.machine_stream import MachineStreamManager
from api import machines_router, alerts_router, copilot_router, maintenance_router, production_router, onboarding_router, discovery_router, ginning_validation_router, twin_router
from services.scheduled_grok_generator import scheduled_grok_generator
from notifications.notification_manager import notification_manager
from alerts.alert_manager import alert_manager
from models import Machine
from seed import seed_demo_machines

settings = get_settings()

# Alert notification callback
async def on_alert_created(alert, mechanic):
    """Send notifications when alert is created."""
    from database import SessionLocal
    from config import get_settings
    settings = get_settings()
    
    db = SessionLocal()
    try:
        # Get machine info
        machine = db.query(Machine).filter(Machine.machine_id == alert.machine_id).first()
        machine_info = {
            'machine_id': alert.machine_id,
            'name': machine.name if machine else alert.machine_id,
            'type': machine.type if machine else 'Unknown',
            'location': machine.location if machine else 'Unknown'
        }
        
        # Get mechanic info or use default from .env
        mechanic_info = {}
        if mechanic:
            mechanic_info = {
                'name': mechanic.name,
                'email': mechanic.email,
                'whatsapp_number': mechanic.whatsapp_number or settings.TWILIO_WHATSAPP_TO,
                'phone': mechanic.phone
            }
        else:
            # Use default WhatsApp number from .env
            mechanic_info = {
                'name': 'On-Call Mechanic',
                'email': None,
                'whatsapp_number': settings.TWILIO_WHATSAPP_TO,
                'phone': None
            }
        
        print(f"[Alert] Sending notification to {mechanic_info.get('whatsapp_number')} for {machine_info['name']}")
        
        # Prepare alert data
        alert_data = {
            'alert_id': alert.alert_id,
            'failure_type': alert.failure_type,
            'severity': alert.severity,
            'confidence': alert.confidence,
            'time_to_breach': alert.time_to_breach,
            'recommended_action': alert.recommended_action,
            'sensor_snapshot': alert.sensor_snapshot
        }
        
        # Send notifications
        await notification_manager.send_alert_notification(
            alert_data=alert_data,
            machine_info=machine_info,
            mechanic_info=mechanic_info
        )
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    if settings.SEED_DEMO_DATA:
        db = SessionLocal()
        try:
            added = seed_demo_machines(db)
            if added:
                print(f"Seeded {added} demo machines")
        finally:
            db.close()
    print(f"{settings.APP_NAME} started v1.0")
    print(f"Debug mode: {settings.DEBUG}")
    
    # Start scheduled Grok generator
    scheduled_grok_generator.connection_manager = manager
    await scheduled_grok_generator.start()
    
    yield
    
    # Shutdown
    await stream_manager.stop_all()
    await scheduled_grok_generator.stop()
    print(f"{settings.APP_NAME} shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered predictive maintenance system for industrial machinery",
    version="0.1.0",
    lifespan=lifespan
)

# CORS
cors_origins = settings.cors_origins_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX or None,
    # Browsers reject credentialed requests against a wildcard origin
    allow_credentials="*" not in cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket Managers
manager = ConnectionManager()
stream_manager = MachineStreamManager(
    manager,
    data_generator=scheduled_grok_generator.live_snapshot,
    update_interval=settings.WEBSOCKET_UPDATE_INTERVAL
)

# Connect scheduler to manager
scheduled_grok_generator.connection_manager = manager

# Connect alert manager to notification manager
alert_manager.on_alert_created = on_alert_created

# API Routers
app.include_router(machines_router)
app.include_router(alerts_router)
app.include_router(copilot_router)
app.include_router(maintenance_router)
app.include_router(production_router)
app.include_router(onboarding_router)
app.include_router(discovery_router)
app.include_router(ginning_validation_router)
app.include_router(twin_router)


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "websocket": "ready"
    }


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            message = await websocket.receive_text()
            try:
                data = json.loads(message)
                action = data.get("action")
                
                if action == "subscribe":
                    machine_id = data.get("machine_id")
                    if machine_id:
                        manager.subscribe_to_machine(client_id, machine_id)
                        await manager.send_json_message(
                            {"type": "subscribed", "machine_id": machine_id}, 
                            client_id
                        )
                        # Start streaming if not already
                        if not stream_manager.is_streaming(machine_id):
                            await stream_manager.start_machine_stream(machine_id)
                
                elif action == "unsubscribe":
                    machine_id = data.get("machine_id")
                    if machine_id:
                        manager.unsubscribe_from_machine(client_id, machine_id)
                        await manager.send_json_message(
                            {"type": "unsubscribed", "machine_id": machine_id}, 
                            client_id
                        )
                
                elif action == "get_active_streams":
                    streams = stream_manager.get_active_streams()
                    await manager.send_json_message(
                        {"type": "active_streams", "streams": streams}, 
                        client_id
                    )
                
                else:
                    await manager.send_personal_message(f"Echo: {message}", client_id)
                    
            except json.JSONDecodeError:
                await manager.send_personal_message(f"Echo: {message}", client_id)
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WS] Client {client_id} error: {e}")
    finally:
        manager.disconnect(client_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=settings.DEBUG)
