"""
FastAPI Main Application Entry Point.
"""

import os
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config.settings import settings
from backend.api.routes import router
from backend.api.websocket import ws_manager
from backend.services.reminder_service import reminder_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("voice-assistant")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Aura AI Voice Assistant...")
    # Register reminder broadcast callback
    reminder_service.register_notifier(ws_manager.broadcast)
    reminder_task = asyncio.create_task(reminder_service.run_reminder_loop())
    
    yield

    logger.info("Shutting down Aura Voice Assistant...")
    reminder_service._running = False
    reminder_task.cancel()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Production-grade AI Voice Command Assistant for desktop automation and natural interaction.",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount screenshots directory
settings.screenshots_dir.mkdir(parents=True, exist_ok=True)
app.mount("/screenshots", StaticFiles(directory=str(settings.screenshots_dir.resolve())), name="screenshots")

# Include API routes
app.include_router(router)


# WebSocket endpoint for real-time assistant state
@app.websocket("/ws/assistant")
async def websocket_assistant_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.debug(f"WebSocket client error: {e}")
        ws_manager.disconnect(websocket)


# WebSocket endpoint for connected Android and Windows device agents
@app.websocket("/ws/device/{device_type}/{device_id}")
async def websocket_device_endpoint(websocket: WebSocket, device_type: str, device_id: str):
    import json
    from backend.services.device_registry_service import device_registry_service
    from backend.models.device_schemas import RemoteTaskResult, DeviceHeartbeatRequest, DeviceStatus
    from backend.services.command_service import command_service

    await websocket.accept()
    device_registry_service.attach_websocket(device_id, websocket)

    # Broadcast device online
    await ws_manager.broadcast({
        "type": "device_status_change",
        "device_id": device_id,
        "device_type": device_type,
        "status": "online"
    })

    try:
        while True:
            raw_msg = await websocket.receive_text()
            try:
                data = json.loads(raw_msg)
                msg_type = data.get("type")

                if msg_type == "task_result":
                    res = RemoteTaskResult(
                        task_id=data.get("task_id", ""),
                        device_id=device_id,
                        status=data.get("status", "completed"),
                        result_data=data.get("result_data", {}),
                        error=data.get("error"),
                        execution_time_ms=data.get("execution_time_ms")
                    )
                    device_registry_service.handle_remote_task_result(res)

                elif msg_type == "heartbeat":
                    hb = DeviceHeartbeatRequest(
                        device_id=device_id,
                        battery_pct=data.get("battery_pct"),
                        is_charging=data.get("is_charging"),
                        ram_usage_pct=data.get("ram_usage_pct"),
                        storage_free_gb=data.get("storage_free_gb"),
                        status=DeviceStatus.ONLINE
                    )
                    device_registry_service.update_heartbeat(hb)
                    await ws_manager.broadcast({
                        "type": "device_heartbeat",
                        "device_id": device_id,
                        "data": data
                    })

                elif msg_type == "voice_command":
                    text = data.get("text", "")
                    if text:
                        exec_res = await command_service.process_command(text)
                        await websocket.send_text(json.dumps({
                            "type": "command_execution_result",
                            "result": exec_res.model_dump()
                        }))

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from device {device_id}: {raw_msg}")

    except WebSocketDisconnect:
        device_registry_service.detach_websocket(device_id)
        await ws_manager.broadcast({
            "type": "device_status_change",
            "device_id": device_id,
            "device_type": device_type,
            "status": "offline"
        })
    except Exception as e:
        logger.error(f"Device WebSocket error for {device_id}: {e}")
        device_registry_service.detach_websocket(device_id)



# Mount frontend dist static assets and SPA fallback
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if (frontend_dist / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str((frontend_dist / "assets").resolve())), name="assets")


@app.get("/{full_path:path}")
async def serve_spa_frontend(full_path: str):
    if not frontend_dist.exists():
        return {"status": "Aura Backend Running", "docs": "/docs"}
    
    target_file = frontend_dist / full_path
    if full_path and target_file.exists() and target_file.is_file():
        return FileResponse(target_file)
    
    index_file = frontend_dist / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    
    return {"status": "Frontend not built yet. Run npm run build."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.host, port=settings.port, reload=True)
