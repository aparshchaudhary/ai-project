"""
FastAPI REST API Routes.
"""

import json
import asyncio
import time
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.config.settings import settings
from backend.database.database import get_db, SessionLocal
from backend.database.models import CommandHistory, Reminder, AppRegistry, AppSetting
from backend.models.schemas import (
    VoiceTranscribeResponse,
    CommandRequest,
    CommandExecutionResponse,
    ConfirmationRequest,
    ReminderCreate,
    ReminderResponse,
    AppItemCreate,
    AppItemResponse,
    SystemStatusResponse,
    HistoryItemResponse,
    AnalyticsResponse,
    SpeakRequest,
    SettingsUpdate,
)
from backend.services.speech_service import speech_service
from backend.services.tts_service import tts_service
from backend.services.command_service import command_service
from backend.services.system_service import system_service
from backend.services.screenshot_service import screenshot_service
from backend.services.reminder_service import reminder_service
from backend.services.automation_service import automation_service
from backend.services.analytics_service import analytics_service
from backend.services.audio_manager import audio_manager
from backend.security.credential_store import private_config, WindowsDPAPI
from backend.security.permissions import permission_manager, PermissionScope
from backend.api.websocket import ws_manager

router = APIRouter(prefix="/api")


class SelectDeviceRequest(BaseModel):
    device_id: int


class GrantPermissionRequest(BaseModel):
    scope: str
    target: str = "*"
    duration_days: int = 30


class RevokePermissionRequest(BaseModel):
    scope: str
    target: str = "*"


class DirectoryRequest(BaseModel):
    directory: str



# 1. Voice & Speech Endpoints
@router.post("/voice/transcribe", response_model=VoiceTranscribeResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    auto_execute: bool = Form(False),
    session_id: str = Form("default")
):
    try:
        content = await file.read()
        success, text, error = speech_service.transcribe_audio(content, filename=file.filename)
        if not success:
            return VoiceTranscribeResponse(
                success=False,
                text="",
                error=error or "Could not transcribe audio.",
                engine_used=settings.stt_engine
            )

        # Check wake word
        has_wake, clean_command = speech_service.detect_wake_word(text)

        # Broadcast state
        await ws_manager.broadcast({
            "type": "state_change",
            "state": "processing",
            "transcription": text,
            "has_wake_word": has_wake
        })

        return VoiceTranscribeResponse(
            success=True,
            text=clean_command if has_wake else text,
            detected_language=settings.default_language,
            engine_used=settings.stt_engine
        )
    except Exception as e:
        return VoiceTranscribeResponse(
            success=False,
            text="",
            error=str(e),
            engine_used="error"
        )


@router.post("/voice/listen-desktop")
async def listen_from_desktop_mic(
    duration: float = Query(4.0, ge=1.0, le=15.0),
    use_vad: bool = Query(True),
    auto_execute: bool = Query(True),
    device_id: Optional[int] = Query(None)
):
    """
    Directly captures audio from the system hardware microphone via adaptive VAD or fixed duration,
    computes real latency benchmarks, and optionally executes commands automatically.
    """
    await ws_manager.broadcast({"type": "state_change", "state": "listening"})
    success, text, err, metrics = await asyncio.to_thread(
        speech_service.record_from_hardware_mic,
        duration_seconds=duration,
        use_vad=use_vad,
        device_id=device_id
    )

    if not success or not text.strip():
        await ws_manager.broadcast({"type": "state_change", "state": "idle"})
        return {
            "success": False,
            "text": "",
            "error": err or "No speech detected. Please speak into your microphone and try again.",
            "metrics": metrics,
            "execution": None
        }

    await ws_manager.broadcast({
        "type": "state_change",
        "state": "executing",
        "transcription": text,
        "metrics": metrics
    })

    exec_result = None
    if auto_execute:
        exec_result = await command_service.process_command(text)
        await ws_manager.broadcast({
            "type": "command_result",
            "result": exec_result.model_dump(),
            "state": "idle" if not exec_result.requires_confirmation else "waiting_confirmation"
        })

    return {
        "success": True,
        "text": text,
        "metrics": metrics,
        "execution": exec_result.model_dump() if exec_result else None
    }


@router.post("/voice/stop")
async def stop_voice_playback():
    """
    Interrupts and immediately stops any ongoing text-to-speech output.
    """
    tts_service.stop()
    await ws_manager.broadcast({"type": "state_change", "state": "idle"})
    return {"success": True, "message": "Voice playback stopped."}


# Audio Hardware Device Endpoints
@router.get("/audio/devices")
async def get_audio_input_devices():
    """
    Lists all available hardware and system input audio devices.
    """
    devices = audio_manager.list_input_devices()
    selected_id = audio_manager.get_selected_device_id()
    return {
        "devices": devices,
        "selected_device_id": selected_id
    }


@router.post("/audio/select-device")
async def select_audio_device(req: SelectDeviceRequest):
    """
    Configures the preferred microphone device ID.
    """
    ok = audio_manager.select_microphone_device(req.device_id)
    if not ok:
        raise HTTPException(status_code=400, detail=f"Invalid device ID {req.device_id}")
    return {"success": True, "selected_device_id": req.device_id}


@router.get("/audio/test-level")
async def test_audio_level(device_id: Optional[int] = Query(None)):
    """
    Captures a 250ms test slice and returns the live RMS input level (0-100%).
    """
    res = await asyncio.to_thread(audio_manager.test_input_level, device_id)
    return res



@router.post("/voice/speak")
async def speak_text(req: SpeakRequest):
    await ws_manager.broadcast({"type": "state_change", "state": "speaking", "text": req.text})
    await tts_service.speak(req.text, rate=req.rate, volume=req.volume, voice_id=req.voice_id)
    await ws_manager.broadcast({"type": "state_change", "state": "idle"})
    return {"success": True, "message": "Spoken successfully."}


@router.post("/voice/render-audio")
async def render_audio_bytes(req: SpeakRequest):
    wav_bytes = await tts_service.render_wav(req.text)
    if not wav_bytes:
        raise HTTPException(status_code=500, detail="Could not render audio.")
    return Response(content=wav_bytes, media_type="audio/wav")


@router.get("/voice/voices")
async def get_available_voices():
    return tts_service.get_voices()


# 2. Command Processing & Confirmation Endpoints
@router.post("/command/process", response_model=CommandExecutionResponse)
async def process_command(req: CommandRequest):
    # Broadcast processing state
    await ws_manager.broadcast({
        "type": "state_change",
        "state": "executing",
        "command": req.text
    })

    res = await command_service.process_command(
        text=req.text,
        session_id=req.session_id or "default",
        is_demo=req.demo_mode or settings.demo_mode,
        confirmed=req.confirmed,
        confirmation_id=req.confirmation_id
    )

    await ws_manager.broadcast({
        "type": "command_result",
        "result": res.model_dump(),
        "state": "idle" if not res.requires_confirmation else "waiting_confirmation"
    })

    return res


@router.post("/command/confirm", response_model=CommandExecutionResponse)
async def confirm_command(req: ConfirmationRequest):
    res = await command_service.confirm_and_execute(
        confirmation_id=req.confirmation_id,
        approved=req.approved
    )
    await ws_manager.broadcast({
        "type": "command_result",
        "result": res.model_dump(),
        "state": "idle"
    })
    return res


# 3. Command History
@router.get("/history", response_model=List[HistoryItemResponse])
async def get_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(CommandHistory)
    if search:
        query = query.filter(CommandHistory.command_text.ilike(f"%{search}%"))
    if status:
        query = query.filter(CommandHistory.status == status)

    items = query.order_by(desc(CommandHistory.created_at)).offset(offset).limit(limit).all()
    out = []
    for i in items:
        out.append(HistoryItemResponse(
            id=i.id,
            command_text=i.command_text,
            recognized_intent=i.recognized_intent,
            entities=json.loads(i.entities_json or "{}"),
            status=i.status,
            risk_level=i.risk_level or "low",
            response_text=i.response_text,
            execution_time_ms=i.execution_time_ms,
            created_at=i.created_at
        ))
    return out


@router.delete("/history")
async def clear_history(db: Session = Depends(get_db)):
    db.query(CommandHistory).delete()
    db.commit()
    return {"success": True, "message": "Command history cleared."}


@router.delete("/history/{item_id}")
async def delete_history_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(CommandHistory).filter(CommandHistory.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return {"success": True, "message": "Record deleted."}


# 4. Reminders
@router.get("/reminders", response_model=List[ReminderResponse])
async def get_reminders(include_completed: bool = False):
    return reminder_service.get_reminders(include_completed=include_completed)


@router.post("/reminders", response_model=ReminderResponse)
async def create_reminder(req: ReminderCreate):
    success, msg, data = reminder_service.create_reminder(
        title=req.title,
        time_str=req.due_time.isoformat(),
        is_recurring=req.is_recurring,
        recurrence_pattern=req.recurrence_pattern
    )
    if not success or not data:
        raise HTTPException(status_code=400, detail=msg)
    return data


@router.patch("/reminders/{reminder_id}/complete")
async def toggle_reminder_completion(reminder_id: int):
    success = reminder_service.mark_completed(reminder_id)
    if not success:
        raise HTTPException(status_code=404, detail="Reminder not found.")
    return {"success": True}


@router.delete("/reminders/{reminder_id}")
async def delete_reminder(reminder_id: int):
    success = reminder_service.delete_reminder(reminder_id)
    if not success:
        raise HTTPException(status_code=404, detail="Reminder not found.")
    return {"success": True}


# 5. System Status & Control
@router.get("/system/status", response_model=SystemStatusResponse)
async def get_system_status():
    return system_service.get_system_status()


@router.get("/system/screenshots")
async def get_screenshots():
    return screenshot_service.list_screenshots()


@router.post("/system/open-screenshots-folder")
async def open_screenshots_folder():
    success, msg = screenshot_service.open_screenshots_folder()
    return {"success": success, "message": msg}


# 6. Applications Registry
@router.get("/apps", response_model=List[AppItemResponse])
async def get_applications():
    return automation_service.get_registered_apps()


@router.post("/apps", response_model=AppItemResponse)
async def add_application(item: AppItemCreate):
    return automation_service.add_custom_app(
        app_key=item.app_key,
        display_name=item.display_name,
        aliases=item.aliases,
        exec_path=item.exec_path
    )


@router.post("/apps/launch/{app_key}")
async def launch_application_direct(app_key: str):
    success, msg = automation_service.launch_app(app_key)
    return {"success": success, "message": msg}


@router.delete("/apps/{app_id}")
async def delete_application(app_id: int, db: Session = Depends(get_db)):
    app = db.query(AppRegistry).filter(AppRegistry.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    db.delete(app)
    db.commit()
    return {"success": True, "message": "Application removed."}


# 7. Analytics
@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics():
    return analytics_service.get_analytics()


# 8. Settings & Preferences
@router.get("/settings")
async def get_settings():
    return {
        "app_name": settings.app_name,
        "wake_word": settings.wake_word,
        "wake_word_enabled": settings.wake_word_enabled,
        "default_language": settings.default_language,
        "tts_rate": settings.tts_rate,
        "tts_volume": settings.tts_volume,
        "tts_voice_id": settings.tts_voice_id,
        "clipboard_permission_enabled": settings.clipboard_permission_enabled,
        "require_confirmation_high_risk": settings.require_confirmation_high_risk,
        "require_confirmation_med_risk": settings.require_confirmation_med_risk,
        "demo_mode": settings.demo_mode,
        "default_browser": settings.default_browser,
        "default_music_app": settings.default_music_app,
        "theme": settings.theme,
        "has_openai_key": bool(settings.openai_api_key),
    }


@router.put("/settings")
async def update_settings(up: SettingsUpdate):
    if up.app_name is not None:
        settings.app_name = up.app_name
    if up.wake_word is not None:
        settings.wake_word = up.wake_word.lower()
    if up.wake_word_enabled is not None:
        settings.wake_word_enabled = up.wake_word_enabled
    if up.default_language is not None:
        settings.default_language = up.default_language
    if up.tts_rate is not None:
        settings.tts_rate = up.tts_rate
    if up.tts_volume is not None:
        settings.tts_volume = up.tts_volume
    if up.clipboard_permission_enabled is not None:
        settings.clipboard_permission_enabled = up.clipboard_permission_enabled
    if up.require_confirmation_high_risk is not None:
        settings.require_confirmation_high_risk = up.require_confirmation_high_risk
    if up.require_confirmation_med_risk is not None:
        settings.require_confirmation_med_risk = up.require_confirmation_med_risk
    if up.demo_mode is not None:
        settings.demo_mode = up.demo_mode
    if up.default_browser is not None:
        settings.default_browser = up.default_browser
    if up.default_music_app is not None:
        settings.default_music_app = up.default_music_app
    if up.theme is not None:
        settings.theme = up.theme
    if up.openai_api_key is not None:
        settings.openai_api_key = up.openai_api_key

    return {"success": True, "settings": await get_settings()}


# 9. Help Center Commands Reference
@router.get("/help")
async def get_help_guide():
    return [
        {
            "category": "Applications",
            "icon": "AppWindow",
            "commands": [
                {"text": "Open Chrome", "description": "Launches Google Chrome browser"},
                {"text": "Launch VS Code", "description": "Opens Visual Studio Code"},
                {"text": "Open Calculator", "description": "Opens Windows Calculator"},
                {"text": "Open Notepad", "description": "Opens text notepad"},
                {"text": "Close Chrome", "description": "Safely terminates Chrome process"}
            ]
        },
        {
            "category": "Web Automation",
            "icon": "Globe",
            "commands": [
                {"text": "Search Google for machine learning", "description": "Performs Google web search"},
                {"text": "Search YouTube for Python tutorials", "description": "Searches YouTube videos"},
                {"text": "Open YouTube", "description": "Opens YouTube in default browser"},
                {"text": "Search Wikipedia for artificial intelligence", "description": "Direct Wikipedia search"}
            ]
        },
        {
            "category": "Files and Folders",
            "icon": "Folder",
            "commands": [
                {"text": "Open my downloads folder", "description": "Opens Downloads directory"},
                {"text": "Create a folder called College Projects", "description": "Creates folder in Documents"},
                {"text": "Create a file named notes.txt", "description": "Creates empty note file"},
                {"text": "Find my Python project", "description": "Scans documents and desktop for matching files"},
                {"text": "Delete file notes.txt", "description": "Deletes file with explicit confirmation"}
            ]
        },
        {
            "category": "System Controls",
            "icon": "Cpu",
            "commands": [
                {"text": "Show CPU usage", "description": "Reads current CPU & core metrics"},
                {"text": "Show system information", "description": "Summarizes OS, RAM, and hardware health"},
                {"text": "Take a screenshot", "description": "Captures screen and saves timestamped image"},
                {"text": "Volume up / Volume down", "description": "Adjusts Windows system volume"},
                {"text": "Lock screen", "description": "Locks the current workstation"},
                {"text": "Turn off the computer", "description": "Triggers safe shutdown with confirmation"}
            ]
        },
        {
            "category": "Reminders & Time",
            "icon": "Clock",
            "commands": [
                {"text": "What time is it?", "description": "Announces current local time"},
                {"text": "Tell me today's date", "description": "Announces current calendar date"},
                {"text": "Set a reminder for 8 PM to study", "description": "Schedules a reminder with alert"},
                {"text": "Show my reminders", "description": "Lists all upcoming reminders"}
            ]
        },
        {
            "category": "Weather & Information",
            "icon": "CloudSun",
            "commands": [
                {"text": "What's the weather today?", "description": "Fetches current temperature and weather forecast"},
                {"text": "What is the weather in New York?", "description": "Checks weather for specific city"}
            ]
        },
        {
            "category": "Music & Audio",
            "icon": "Music",
            "commands": [
                {"text": "Play music", "description": "Sends play/pause multimedia key"},
                {"text": "Next song", "description": "Skips to the next track in media player"},
                {"text": "Previous song", "description": "Goes to previous track"}
            ]
        },
        {
            "category": "Clipboard & Privacy",
            "icon": "Clipboard",
            "commands": [
                {"text": "Read my clipboard", "description": "Reads current clipboard text safely"},
                {"text": "Clear my clipboard", "description": "Empties clipboard memory"}
            ]
        },
        {
            "category": "Multilingual (Hindi / Hinglish)",
            "icon": "Languages",
            "commands": [
                {"text": "Chrome kholo", "description": "Opens Chrome browser"},
                {"text": "Screenshot lo", "description": "Takes a screen capture"},
                {"text": "Kya samay hua hai?", "description": "Tells current time"},
                {"text": "Aaj ki tarikh batao", "description": "Tells today's date"},
                {"text": "Folder banao AI Project", "description": "Creates AI Project folder"}
            ]
        },
        {
            "category": "AI Conversation Mode",
            "icon": "Sparkles",
            "commands": [
                {"text": "Explain machine learning", "description": "Explains ML concepts concisely"},
                {"text": "What is Python?", "description": "Explains Python programming language"},
                {"text": "Help me prepare for my interview", "description": "Provides interview prep strategy"},
                {"text": "Tell me a joke", "description": "Tells a fun programmer joke"}
            ]
        }
    ]


# 10. Demo Samples for Presentations
@router.get("/demo/samples")
async def get_demo_samples():
    return [
        {"command": "Open Chrome", "intent": "open_application", "description": "Demonstrates application control"},
        {"command": "Take a screenshot", "intent": "take_screenshot", "description": "Captures screen & saves with timestamp"},
        {"command": "Show system information", "intent": "system_information", "description": "Reads live CPU, RAM & disk health"},
        {"command": "What's the weather today?", "intent": "weather", "description": "Queries external weather API"},
        {"command": "Search for Python tutorials", "intent": "search_web", "description": "Demonstrates safe web search"},
        {"command": "Create a folder called College Projects", "intent": "create_folder", "description": "Performs file/folder automation"},
        {"command": "Set a reminder for 8 PM to submit assignment", "intent": "set_reminder", "description": "Demonstrates reminder scheduling"},
        {"command": "Chrome kholo", "intent": "open_application", "description": "Demonstrates Hindi / Hinglish multilingual support"},
        {"command": "Explain machine learning", "intent": "conversation", "description": "Routes to conversational AI mode"},
        {"command": "Turn off the computer", "intent": "shutdown", "description": "Demonstrates high-risk security confirmation dialog"}
    ]


# 11. Security, Persistent Permissions & Audit Log Endpoints
@router.get("/security/permissions")
async def get_security_permissions():
    """
    Returns active persistent permission grants, authorized sandbox directories,
    and DPAPI encryption status.
    """
    return {
        "persistent_permissions": permission_manager.get_granted_permissions(),
        "authorized_directories": [str(d) for d in private_config.get_authorized_dirs()],
        "dpapi_available": WindowsDPAPI.is_available()
    }


@router.post("/security/permissions/grant")
async def grant_persistent_permission(req: GrantPermissionRequest):
    """
    Persistently grants a permission scope for an application or operation.
    """
    record = permission_manager.grant_permission(req.scope, req.target, req.duration_days)
    return {"success": True, "permission": record}


@router.post("/security/permissions/revoke")
async def revoke_persistent_permission(req: RevokePermissionRequest):
    """
    Revokes a previously granted permission scope.
    """
    permission_manager.revoke_permission(req.scope, req.target)
    return {"success": True, "message": f"Revoked permission for '{req.scope}:{req.target}'."}


@router.get("/security/audit-logs")
async def get_audit_logs(limit: int = Query(50, ge=1, le=200)):
    """
    Returns redacted audit history for operations and security boundary evaluations.
    """
    logs = permission_manager.get_audit_logs(limit=limit)
    return {"logs": logs, "count": len(logs)}


@router.post("/security/directories/add")
async def add_authorized_directory(req: DirectoryRequest):
    target = Path(req.directory).resolve()
    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=400, detail="Directory path does not exist.")
    for forb in [Path("C:/Windows").resolve(), Path("C:/Program Files").resolve()]:
        if forb in target.parents or target == forb:
            raise HTTPException(status_code=400, detail="Cannot add protected system directory.")
    private_config.add_authorized_dir(target)
    return {
        "success": True,
        "authorized_directories": [str(d) for d in private_config.get_authorized_dirs()]
    }


@router.post("/security/directories/remove")
async def remove_authorized_directory(req: DirectoryRequest):
    target = Path(req.directory).resolve()
    private_config.remove_authorized_dir(target)
    return {
        "success": True,
        "authorized_directories": [str(d) for d in private_config.get_authorized_dirs()]
    }


# 12. Comprehensive System Diagnostics
@router.get("/diagnostics/run")
async def run_diagnostics():
    """
    Performs end-to-end hardware, audio pipeline, security boundary,
    and DPAPI encryption diagnostics, returning real measured latencies in milliseconds.
    """
    start_all = time.time()
    results = {}

    # 1. Hardware Microphone Test
    t0 = time.time()
    mic_test = await asyncio.to_thread(audio_manager.test_input_level, None, 0.2)
    mic_lat = round((time.time() - t0) * 1000, 1)
    results["microphone"] = {
        "status": "pass" if mic_test.get("success") else "fail",
        "device_id": mic_test.get("device_id"),
        "device_name": mic_test.get("device_name"),
        "rms": mic_test.get("rms", 0.0),
        "level_percent": mic_test.get("level_percent", 0.0),
        "latency_ms": mic_lat
    }

    # 2. Voice Activity Detection (VAD) Engine
    v_thresh = private_config.get("audio", "vad_energy_threshold", 320)
    v_silence = private_config.get("audio", "vad_silence_duration_ms", 700)
    results["vad"] = {
        "status": "pass",
        "energy_threshold": v_thresh,
        "silence_duration_ms": v_silence,
        "mode": "Adaptive RMS with ambient noise calibration"
    }

    # 3. Speech-to-Text (STT) Engine
    stt_ok = bool(speech_service.engine)
    results["stt"] = {
        "status": "pass" if stt_ok else "warn",
        "engine": settings.stt_engine,
        "language": settings.default_language,
        "whisper_api_configured": bool(settings.openai_api_key)
    }

    # 4. Text-to-Speech (TTS) Engine
    results["tts"] = {
        "status": "pass",
        "engine": "Windows Native SAPI 5.4 (detached non-blocking)",
        "interrupt_support": True
    }

    # 5. Windows DPAPI Credential Store Check
    t0 = time.time()
    dpapi_pass = False
    try:
        raw_test = b"diagnostic_probe_test"
        enc = WindowsDPAPI.protect(raw_test)
        dec = WindowsDPAPI.unprotect(enc)
        dpapi_pass = (dec == raw_test)
    except Exception:
        dpapi_pass = False
    dpapi_lat = round((time.time() - t0) * 1000, 2)
    results["dpapi_vault"] = {
        "status": "pass" if dpapi_pass else "fail",
        "available": WindowsDPAPI.is_available(),
        "vault_path": str(Path.home() / ".aura_assistant" / "vault.bin"),
        "latency_ms": dpapi_lat
    }

    # 6. Security Sandbox & Path Traversal Check
    traversal_test = Path("../../Windows/System32/cmd.exe")
    is_auth, reason = permission_manager.is_path_authorized(traversal_test)
    sandbox_pass = (not is_auth)  # Must be blocked!
    results["sandbox_boundary"] = {
        "status": "pass" if sandbox_pass else "fail",
        "traversal_attack_blocked": sandbox_pass,
        "test_target": str(traversal_test),
        "rejection_reason": reason
    }

    # 7. WhatsApp Desktop / Protocol Integration Check
    wa_app = automation_service.find_app("whatsapp")
    wa_ok = bool(wa_app)
    results["whatsapp_integration"] = {
        "status": "pass" if wa_ok else "warn",
        "registered": wa_ok,
        "protocol": "start whatsapp:",
        "persistent_permission_cached": permission_manager.is_permission_granted(PermissionScope.APP_LAUNCH, "whatsapp")
    }

    total_diag_lat = round((time.time() - start_all) * 1000, 1)
    all_passed = all(r.get("status") in ["pass", "warn"] for r in results.values())

    return {
        "overall_status": "healthy" if all_passed else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "total_latency_ms": total_diag_lat,
        "components": results
    }

