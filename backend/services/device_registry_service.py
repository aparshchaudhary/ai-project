"""
Cross-Platform Device Registry & Orchestration Service.
Manages connected Android and Windows execution nodes, tracks real-time capabilities,
handles WebSocket device communication, and dispatches remote tasks.
"""

from __future__ import annotations
import json
import time
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set
from fastapi import WebSocket

from backend.database.database import SessionLocal
from backend.database.models import ConnectedDevice
from backend.models.device_schemas import (
    DeviceType,
    DeviceStatus,
    DeviceCapability,
    DeviceRegistrationRequest,
    DeviceHeartbeatRequest,
    ConnectedDeviceInfo,
    RemoteTaskDispatch,
    RemoteTaskResult,
)

logger = logging.getLogger(__name__)


class DeviceRegistryService:
    def __init__(self):
        self._device_websockets: Dict[str, WebSocket] = {}
        self._pending_task_futures: Dict[str, asyncio.Future] = {}
        self._cached_devices: Dict[str, ConnectedDeviceInfo] = {}
        self._init_default_local_nodes()

    def _init_default_local_nodes(self):
        """Initializes default local Windows node capability record."""
        # By default, local Windows host is available
        self._cached_devices["local_windows"] = ConnectedDeviceInfo(
            device_id="local_windows",
            device_name="Windows Workstation",
            device_type=DeviceType.WINDOWS,
            status=DeviceStatus.ONLINE,
            capabilities=[
                DeviceCapability.FILE_MANAGEMENT.value,
                DeviceCapability.PROCESS_LAUNCH.value,
                DeviceCapability.BROWSER_AUTOMATION.value,
                DeviceCapability.VS_CODE_CONTROL.value,
                DeviceCapability.OFFICE_AUTOMATION.value,
                DeviceCapability.SYSTEM_DIAGNOSTICS.value,
                DeviceCapability.SCREENSHOT.value,
                DeviceCapability.FILE_TRANSFER.value,
            ],
            battery_pct=None,
            is_charging=True,
            ram_usage_pct=42.0,
            storage_free_gb=128.5,
            last_seen=time.time(),
        )

    def register_device(self, req: DeviceRegistrationRequest, ip_address: Optional[str] = None) -> ConnectedDeviceInfo:
        """Registers a new or existing device in database and cache."""
        with SessionLocal() as db:
            dev = db.query(ConnectedDevice).filter(ConnectedDevice.device_id == req.device_id).first()
            caps_json = json.dumps(req.capabilities)
            sys_json = json.dumps(req.system_info or {})
            now = datetime.now(timezone.utc)

            if not dev:
                dev = ConnectedDevice(
                    device_id=req.device_id,
                    device_name=req.device_name,
                    device_type=req.device_type.value if hasattr(req.device_type, "value") else str(req.device_type),
                    pairing_token=req.pairing_code,
                    status=DeviceStatus.ONLINE.value,
                    ip_address=ip_address,
                    capabilities_json=caps_json,
                    system_info_json=sys_json,
                    last_seen=now,
                )
                db.add(dev)
            else:
                dev.device_name = req.device_name
                dev.status = DeviceStatus.ONLINE.value
                dev.capabilities_json = caps_json
                dev.system_info_json = sys_json
                dev.ip_address = ip_address or dev.ip_address
                dev.last_seen = now

            db.commit()
            db.refresh(dev)

            info = ConnectedDeviceInfo(
                device_id=dev.device_id,
                device_name=dev.device_name,
                device_type=DeviceType(dev.device_type),
                status=DeviceStatus(dev.status),
                capabilities=json.loads(dev.capabilities_json or "[]"),
                battery_pct=dev.battery_pct,
                is_charging=dev.is_charging,
                ram_usage_pct=dev.ram_usage_pct,
                storage_free_gb=dev.storage_free_gb,
                ip_address=dev.ip_address,
                last_seen=time.time(),
            )
            self._cached_devices[dev.device_id] = info
            logger.info(f"Device registered: {dev.device_id} ({dev.device_name}) [{dev.device_type}]")
            return info

    def update_heartbeat(self, req: DeviceHeartbeatRequest) -> bool:
        """Updates live metrics for a connected device."""
        with SessionLocal() as db:
            dev = db.query(ConnectedDevice).filter(ConnectedDevice.device_id == req.device_id).first()
            if not dev:
                return False

            dev.status = req.status.value
            dev.battery_pct = req.battery_pct
            dev.is_charging = req.is_charging
            dev.ram_usage_pct = req.ram_usage_pct
            dev.storage_free_gb = req.storage_free_gb
            dev.last_seen = datetime.now(timezone.utc)
            db.commit()

            if req.device_id in self._cached_devices:
                c = self._cached_devices[req.device_id]
                c.status = req.status
                c.battery_pct = req.battery_pct
                c.is_charging = req.is_charging
                c.ram_usage_pct = req.ram_usage_pct
                c.storage_free_gb = req.storage_free_gb
                c.last_seen = time.time()
            return True

    def attach_websocket(self, device_id: str, ws: WebSocket):
        """Associates an active WebSocket connection with a device."""
        self._device_websockets[device_id] = ws
        if device_id in self._cached_devices:
            self._cached_devices[device_id].status = DeviceStatus.ONLINE
        logger.info(f"WebSocket attached for device {device_id}")

    def detach_websocket(self, device_id: str):
        """Detaches a WebSocket when a device disconnects."""
        self._device_websockets.pop(device_id, None)
        if device_id in self._cached_devices and device_id != "local_windows":
            self._cached_devices[device_id].status = DeviceStatus.OFFLINE
        logger.info(f"WebSocket detached for device {device_id}")

    def get_connected_devices(self) -> List[ConnectedDeviceInfo]:
        """Lists all registered devices and their current status."""
        with SessionLocal() as db:
            rows = db.query(ConnectedDevice).all()
            result = list(self._cached_devices.values())
            for r in rows:
                if r.device_id not in self._cached_devices:
                    result.append(ConnectedDeviceInfo(
                        device_id=r.device_id,
                        device_name=r.device_name,
                        device_type=DeviceType(r.device_type),
                        status=DeviceStatus(r.status),
                        capabilities=json.loads(r.capabilities_json or "[]"),
                        battery_pct=r.battery_pct,
                        is_charging=r.is_charging,
                        ram_usage_pct=r.ram_usage_pct,
                        storage_free_gb=r.storage_free_gb,
                        ip_address=r.ip_address,
                        last_seen=r.last_seen.timestamp() if r.last_seen else time.time(),
                    ))
            return result

    def find_device_for_capability(
        self,
        capability: str,
        preferred_device_type: Optional[DeviceType] = None
    ) -> Optional[ConnectedDeviceInfo]:
        """
        Discovers an online device equipped with the requested capability.
        Prefers preferred_device_type if specified.
        """
        candidates: List[ConnectedDeviceInfo] = []
        for dev in self.get_connected_devices():
            if dev.status == DeviceStatus.ONLINE and (capability in dev.capabilities or not dev.capabilities):
                candidates.append(dev)

        if not candidates:
            # Fallback for local windows node if asking for windows capability
            if preferred_device_type == DeviceType.WINDOWS or capability.startswith(("filesystem", "process", "browser", "code", "system")):
                return self._cached_devices.get("local_windows")
            return None

        if preferred_device_type:
            for c in candidates:
                if c.device_type == preferred_device_type:
                    return c

        return candidates[0]

    def get_device_by_type(self, device_type: DeviceType) -> Optional[ConnectedDeviceInfo]:
        """Gets the primary online device for a given type (android or windows)."""
        for dev in self.get_connected_devices():
            if dev.device_type == device_type and dev.status == DeviceStatus.ONLINE:
                return dev
        if device_type == DeviceType.WINDOWS:
            return self._cached_devices.get("local_windows")
        return None

    async def dispatch_task(self, dispatch: RemoteTaskDispatch) -> RemoteTaskResult:
        """
        Dispatches a task to a remote device over WebSocket and awaits completion.
        """
        device_id = dispatch.target_device_id
        ws = self._device_websockets.get(device_id)

        start_time = time.time()
        if not ws:
            logger.warning(f"Device {device_id} not connected via active WebSocket")
            return RemoteTaskResult(
                task_id=dispatch.task_id,
                device_id=device_id,
                status="failed",
                error=f"Device '{device_id}' is currently offline. Please ensure the agent application is open on the target device.",
                execution_time_ms=(time.time() - start_time) * 1000
            )

        future = asyncio.get_running_loop().create_future()
        self._pending_task_futures[dispatch.task_id] = future

        try:
            payload = {
                "type": "remote_task_dispatch",
                "dispatch": dispatch.model_dump()
            }
            await ws.send_text(json.dumps(payload))
            logger.info(f"Dispatched task {dispatch.task_id} to device {device_id}")

            # Await remote result with timeout
            result = await asyncio.wait_for(future, timeout=dispatch.timeout_seconds)
            return result
        except asyncio.TimeoutError:
            logger.error(f"Task {dispatch.task_id} timed out on device {device_id}")
            return RemoteTaskResult(
                task_id=dispatch.task_id,
                device_id=device_id,
                status="failed",
                error=f"Task timed out after {dispatch.timeout_seconds} seconds waiting for device response.",
                execution_time_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            logger.error(f"Error dispatching task {dispatch.task_id}: {e}")
            return RemoteTaskResult(
                task_id=dispatch.task_id,
                device_id=device_id,
                status="failed",
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000
            )
        finally:
            self._pending_task_futures.pop(dispatch.task_id, None)

    def handle_remote_task_result(self, result: RemoteTaskResult):
        """Resolves the waiting task Future with the remote response."""
        future = self._pending_task_futures.get(result.task_id)
        if future and not future.done():
            future.set_result(result)
            logger.info(f"Resolved remote task result for {result.task_id}: {result.status}")


device_registry_service = DeviceRegistryService()
