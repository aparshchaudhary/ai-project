"""
Comprehensive Test Suite for Cross-Platform Autonomous Personal AI Agent.
Validates:
1. Device Registration, Presence, and Telemetry (Android & Windows).
2. Dynamic Device & Capability Selection.
3. Android-Native Commands (Calling, WhatsApp, Contacts, Alarms, Settings, Gallery, Notifications).
4. Windows-Native Commands (Explorer, VS Code, Downloads, Folder Creation, Specs).
5. Cross-Device Workflows & DAG Coordination (Laptop -> Phone file send, Battery display, Transfer).
6. Cross-Device File Relay Service (Staging, metadata, retrieval).
7. REST API Endpoints for Device Mesh.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.task_planner import task_planner
from backend.services.task_scheduler import task_scheduler
from backend.services.device_registry_service import device_registry_service
from backend.services.cross_device_relay_service import cross_device_relay_service
from backend.models.device_schemas import (
    DeviceRegistrationRequest,
    DeviceHeartbeatRequest,
    DeviceType,
    DeviceStatus,
    DeviceCapability,
    RemoteTaskDispatch,
    RemoteTaskResult
)
from backend.models.task_planner_schemas import TaskStatus

client = TestClient(app)


# ==========================================
# 1. Device Registry & Capability Tests
# ==========================================

class TestDeviceRegistryAndCapabilities:
    def test_register_android_device(self):
        req = DeviceRegistrationRequest(
            device_id="android_pixel_8",
            device_name="Google Pixel 8",
            device_type=DeviceType.ANDROID,
            pairing_code="123456",
            capabilities=[
                DeviceCapability.TELEPHONY_CALL.value,
                DeviceCapability.WHATSAPP_SEND.value,
                DeviceCapability.CONTACTS_READ.value,
                DeviceCapability.ALARM_SET.value,
                DeviceCapability.DEVICE_SETTINGS.value,
                DeviceCapability.GALLERY_READ.value,
                DeviceCapability.NOTIFICATIONS_READ.value,
            ],
            system_info={"os": "Android 15", "model": "Pixel 8"}
        )
        info = device_registry_service.register_device(req, ip_address="192.168.1.105")
        assert info.device_id == "android_pixel_8"
        assert info.device_type == DeviceType.ANDROID
        assert info.status == DeviceStatus.ONLINE
        assert DeviceCapability.TELEPHONY_CALL.value in info.capabilities

    def test_device_heartbeat_telemetry(self):
        hb = DeviceHeartbeatRequest(
            device_id="android_pixel_8",
            battery_pct=88,
            is_charging=True,
            ram_usage_pct=41.5,
            storage_free_gb=72.0,
            status=DeviceStatus.ONLINE
        )
        ok = device_registry_service.update_heartbeat(hb)
        assert ok is True

        devices = device_registry_service.get_connected_devices()
        dev = next(d for d in devices if d.device_id == "android_pixel_8")
        assert dev.battery_pct == 88
        assert dev.is_charging is True
        assert dev.ram_usage_pct == 41.5

    def test_find_device_for_capability(self):
        # Telephony -> Android
        target_call = device_registry_service.find_device_for_capability(
            DeviceCapability.TELEPHONY_CALL.value,
            preferred_device_type=DeviceType.ANDROID
        )
        assert target_call is not None
        assert target_call.device_type == DeviceType.ANDROID

        # Filesystem -> Windows
        target_fs = device_registry_service.find_device_for_capability(
            DeviceCapability.FILE_MANAGEMENT.value,
            preferred_device_type=DeviceType.WINDOWS
        )
        assert target_fs is not None
        assert target_fs.device_type == DeviceType.WINDOWS


# ==========================================
# 2. Android-Native Commands
# ==========================================

class TestAndroidNativeCommands:
    def test_call_dad(self):
        plan = task_planner.plan_instruction("Call Dad")
        assert len(plan.tasks) == 1
        t = plan.tasks[0]
        assert t.intent == "make_call"
        assert t.contact == "Dad"
        assert t.target_device == "android"
        assert t.requires_confirmation is True

    def test_call_mom(self):
        plan = task_planner.plan_instruction("Call Mom")
        assert len(plan.tasks) == 1
        t = plan.tasks[0]
        assert t.intent == "make_call"
        assert t.contact == "Mom"
        assert t.target_device == "android"
        assert t.requires_confirmation is True

    def test_find_rahul_in_contacts(self):
        plan = task_planner.plan_instruction("Find Rahul in my contacts")
        assert len(plan.tasks) == 1
        t = plan.tasks[0]
        assert t.intent == "query_contacts"
        assert t.contact == "Rahul"
        assert t.target_device == "android"

    def test_tell_rahul_in_10_minutes(self):
        plan = task_planner.plan_instruction("Tell Rahul that I will reach in 10 minutes")
        assert len(plan.tasks) == 1
        t = plan.tasks[0]
        assert t.intent == "send_message"
        assert "Rahul" in t.contact
        assert "10 minutes" in (t.message or "")
        assert t.requires_confirmation is True

    def test_turn_on_bluetooth(self):
        plan = task_planner.plan_instruction("Turn on Bluetooth")
        assert len(plan.tasks) == 1
        t = plan.tasks[0]
        assert t.intent == "control_device_setting"
        assert t.target_device == "android"
        assert t.data.get("action") == "on"

    def test_open_phone_settings(self):
        plan = task_planner.plan_instruction("Open my phone settings")
        assert len(plan.tasks) == 1
        t = plan.tasks[0]
        assert t.intent == "open_phone_app"
        assert t.application == "settings"
        assert t.target_device == "android"

    def test_set_alarm_7am(self):
        plan = task_planner.plan_instruction("Set an alarm for 7 AM")
        assert len(plan.tasks) == 1
        t = plan.tasks[0]
        assert t.intent == "set_alarm"
        assert t.target_device == "android"
        assert "7" in t.data.get("time", "")

    def test_read_notifications(self):
        plan = task_planner.plan_instruction("Read my notifications")
        assert len(plan.tasks) == 1
        t = plan.tasks[0]
        assert t.intent == "read_notifications"
        assert t.target_device == "android"

    def test_open_gallery_and_photos(self):
        plan = task_planner.plan_instruction("Open my gallery and find yesterday's photos")
        assert len(plan.tasks) == 1
        t = plan.tasks[0]
        assert t.intent == "query_gallery"
        assert t.target_device == "android"
        assert "yesterday" in (t.query or "")


# ==========================================
# 3. Windows-Native Commands
# ==========================================

class TestWindowsNativeCommands:
    def test_open_file_explorer(self):
        plan = task_planner.plan_instruction("Open File Explorer")
        assert len(plan.tasks) == 1
        t = plan.tasks[0]
        assert t.intent == "open_application"
        assert t.application == "explorer"
        assert t.target_device == "windows"

    def test_open_downloads_folder(self):
        plan = task_planner.plan_instruction("Open my Downloads folder")
        assert len(plan.tasks) == 1
        t = plan.tasks[0]
        assert t.intent == "open_file"
        assert t.target_device == "windows"
        assert t.data.get("folder") == "downloads"

    def test_open_vs_code(self):
        plan = task_planner.plan_instruction("Open VS Code")
        assert len(plan.tasks) == 1
        t = plan.tasks[0]
        assert t.intent == "open_application"
        assert t.application == "code"
        assert t.target_device == "windows"

    def test_create_folder_ai_projects(self):
        plan = task_planner.plan_instruction("Create a folder called AI Projects")
        assert len(plan.tasks) == 1
        t = plan.tasks[0]
        assert t.intent == "create_folder"
        assert t.target_device == "windows"
        assert t.data.get("folder_name") == "AI Projects"

    def test_find_my_resume(self):
        plan = task_planner.plan_instruction("Find my resume")
        assert len(plan.tasks) == 1
        t = plan.tasks[0]
        assert t.intent == "manage_files"
        assert t.target_device == "windows"
        assert "resume" in (t.query or "")

    def test_check_laptop_ram_and_storage(self):
        plan = task_planner.plan_instruction("Check my laptop's RAM and storage")
        assert len(plan.tasks) == 1
        t = plan.tasks[0]
        assert t.intent == "system_specs"
        assert t.target_device == "windows"


# ==========================================
# 4. Cross-Device Coordination Workflows
# ==========================================

class TestCrossDeviceWorkflows:
    def test_cross_device_resume_to_dad(self):
        text = "Find my resume on my laptop and send it to Dad on WhatsApp"
        plan = task_planner.plan_instruction(text)
        assert len(plan.tasks) == 3

        # Task 1: Windows file search
        t1 = plan.tasks[0]
        assert t1.target_device == "windows"
        assert t1.intent == "manage_files"
        assert "resume" in (t1.query or "").lower()

        # Task 2: Cloud relay staging
        t2 = plan.tasks[1]
        assert t2.target_device == "cloud"
        assert t2.intent == "relay_file"
        assert t2.depends_on == ["task_1"]

        # Task 3: Android WhatsApp dispatch
        t3 = plan.tasks[2]
        assert t3.target_device == "android"
        assert t3.intent == "send_message"
        assert t3.contact == "Dad"
        assert t3.depends_on == ["task_2"]
        assert t3.requires_confirmation is True

    def test_show_laptop_battery_on_phone(self):
        text = "Show my laptop's battery status on my phone"
        plan = task_planner.plan_instruction(text)
        assert len(plan.tasks) == 2

        t1 = plan.tasks[0]
        assert t1.target_device == "windows"
        assert t1.intent == "system_specs"

        t2 = plan.tasks[1]
        assert t2.target_device == "android"
        assert t2.intent == "notify_device"
        assert t2.depends_on == ["task_1"]

    def test_find_pdf_on_phone_open_on_laptop(self):
        text = "Find the PDF on my phone and open it on my laptop"
        plan = task_planner.plan_instruction(text)
        assert len(plan.tasks) == 3

        t1 = plan.tasks[0]
        assert t1.target_device == "android"
        assert t1.intent == "find_phone_file"

        t2 = plan.tasks[1]
        assert t2.target_device == "cloud"
        assert t2.intent == "relay_file"
        assert t2.depends_on == ["task_1"]

        t3 = plan.tasks[2]
        assert t3.target_device == "windows"
        assert t3.intent == "open_file"
        assert t3.depends_on == ["task_2"]

    def test_transfer_file_laptop_to_phone(self):
        text = "Transfer this file from my laptop to my phone"
        plan = task_planner.plan_instruction(text)
        assert len(plan.tasks) == 2

        t1 = plan.tasks[0]
        assert t1.target_device == "windows"
        assert t1.intent == "transfer_file"

        t2 = plan.tasks[1]
        assert t2.target_device == "android"
        assert t2.intent == "receive_file"
        assert t2.depends_on == ["task_1"]


# ==========================================
# 5. Cross-Device File Relay Service
# ==========================================

class TestCrossDeviceFileRelay:
    def test_stage_and_retrieve_relay_file(self):
        sample_bytes = b"Hello from Windows AI Agent. Cross-device document test."
        meta = cross_device_relay_service.stage_file_from_bytes(
            source_device_id="local_windows",
            target_device_id="android_pixel_8",
            filename="agent_notes.txt",
            data=sample_bytes
        )
        assert meta.transfer_id.startswith("relay_")
        assert meta.filename == "agent_notes.txt"
        assert meta.file_size_bytes == len(sample_bytes)

        retrieved = cross_device_relay_service.get_staged_file(meta.transfer_id)
        assert retrieved is not None
        path, fname, mime = retrieved
        assert fname == "agent_notes.txt"
        assert path.read_bytes() == sample_bytes


# ==========================================
# 6. REST API Endpoints
# ==========================================

class TestCrossPlatformApiEndpoints:
    def test_list_devices_endpoint(self):
        res = client.get("/api/devices")
        assert res.status_code == 200
        data = res.json()
        assert "devices" in data
        assert any(d["device_type"] == "windows" for d in data["devices"])

    def test_pair_device_endpoint(self):
        payload = {
            "device_id": "test_galaxy_s24",
            "device_name": "Samsung Galaxy S24",
            "device_type": "android",
            "pairing_code": "999888",
            "capabilities": ["telephony.call", "whatsapp.send"],
            "system_info": {"os": "Android 14"}
        }
        res = client.post("/api/devices/pair", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["device"]["device_id"] == "test_galaxy_s24"

    def test_device_heartbeat_endpoint(self):
        payload = {
            "device_id": "test_galaxy_s24",
            "battery_pct": 92,
            "is_charging": False,
            "ram_usage_pct": 52.0,
            "storage_free_gb": 110.5,
            "status": "online"
        }
        res = client.post("/api/devices/heartbeat", json=payload)
        assert res.status_code == 200
        assert res.json()["success"] is True

    def test_relay_upload_and_download(self):
        # Upload
        files = {"file": ("test_report.pdf", b"%PDF-1.4 sample content", "application/pdf")}
        data = {"source_device_id": "android_phone", "target_device_id": "local_windows"}
        up_res = client.post("/api/relay/upload", files=files, data=data)
        assert up_res.status_code == 200
        transfer_id = up_res.json()["metadata"]["transfer_id"]

        # Download
        down_res = client.get(f"/api/relay/download/{transfer_id}")
        assert down_res.status_code == 200
        assert down_res.content == b"%PDF-1.4 sample content"
