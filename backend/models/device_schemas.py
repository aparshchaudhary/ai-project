"""
Cross-Platform Device Schemas.
Defines schemas for device registration, capability negotiation, remote task dispatch,
and cross-device coordination between Android and Windows agents.
"""

from __future__ import annotations
import time
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class DeviceType(str, Enum):
    ANDROID = "android"
    WINDOWS = "windows"
    CLOUD = "cloud"
    AUTO = "auto"


class DeviceStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    PAIRING = "pairing"


class DeviceCapability(str, Enum):
    # Android specific capabilities
    TELEPHONY_CALL = "telephony.call"
    SMS_SEND = "sms.send"
    CONTACTS_READ = "contacts.read"
    WHATSAPP_SEND = "whatsapp.send"
    GALLERY_READ = "gallery.read"
    NOTIFICATIONS_READ = "notifications.read"
    ALARM_SET = "alarm.set"
    DEVICE_SETTINGS = "device.settings"
    PHONE_APPS = "apps.launch"
    
    # Windows specific capabilities
    FILE_MANAGEMENT = "filesystem.manage"
    PROCESS_LAUNCH = "process.launch"
    BROWSER_AUTOMATION = "browser.automation"
    VS_CODE_CONTROL = "code.editor"
    OFFICE_AUTOMATION = "office.automation"
    SYSTEM_DIAGNOSTICS = "system.diagnostics"
    SCREENSHOT = "screen.capture"
    
    # Cross-device capabilities
    FILE_TRANSFER = "file.transfer"
    NOTIFY_DEVICE = "device.notify"


class DeviceRegistrationRequest(BaseModel):
    device_id: str = Field(..., description="Unique hardware or UUID identifier for the device")
    device_name: str = Field(..., description="Friendly name, e.g., 'Pixel 8' or 'Dell XPS Laptop'")
    device_type: DeviceType = Field(..., description="Type of device: android or windows")
    pairing_code: Optional[str] = Field(None, description="Pre-shared pairing token or security code")
    capabilities: List[str] = Field(default_factory=list, description="List of capability strings")
    system_info: Optional[Dict[str, Any]] = Field(default_factory=dict, description="OS version, model, architecture")


class DeviceHeartbeatRequest(BaseModel):
    device_id: str
    battery_pct: Optional[int] = None
    is_charging: Optional[bool] = None
    ram_usage_pct: Optional[float] = None
    storage_free_gb: Optional[float] = None
    status: DeviceStatus = DeviceStatus.ONLINE


class ConnectedDeviceInfo(BaseModel):
    device_id: str
    device_name: str
    device_type: DeviceType
    status: DeviceStatus
    capabilities: List[str]
    battery_pct: Optional[int] = None
    is_charging: Optional[bool] = False
    ram_usage_pct: Optional[float] = None
    storage_free_gb: Optional[float] = None
    ip_address: Optional[str] = None
    last_seen: float = Field(default_factory=time.time)
    created_at: float = Field(default_factory=time.time)


class RemoteTaskDispatch(BaseModel):
    task_id: str
    intent: str
    target_device_id: str
    target_device_type: DeviceType
    action_params: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: float = 30.0
    created_at: float = Field(default_factory=time.time)


class RemoteTaskResult(BaseModel):
    task_id: str
    device_id: str
    status: str  # "completed", "failed", "in_progress"
    result_data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None


class CrossDeviceTransferMetadata(BaseModel):
    transfer_id: str
    source_device_id: str
    target_device_id: str
    filename: str
    file_size_bytes: int = 0
    mime_type: Optional[str] = "application/octet-stream"
    status: str = "pending"  # pending, ready_for_download, completed, failed
    download_url: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
