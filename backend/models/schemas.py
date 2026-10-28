"""
Pydantic schemas for request and response data models.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class VoiceTranscribeResponse(BaseModel):
    success: bool
    text: str
    detected_language: Optional[str] = "en"
    duration_seconds: Optional[float] = 0.0
    engine_used: str = "whisper_fallback"
    error: Optional[str] = None


class CommandRequest(BaseModel):
    text: str
    session_id: Optional[str] = "default"
    language: Optional[str] = "en"
    demo_mode: Optional[bool] = False
    confirmed: Optional[bool] = None
    confirmation_id: Optional[str] = None


class IntentResult(BaseModel):
    intent: str
    entities: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    requires_confirmation: bool = False
    risk_level: str = "low"  # low, medium, high
    confirmation_prompt: Optional[str] = None
    response_text: Optional[str] = None
    original_text: str = ""
    is_conversation: bool = False


class CommandExecutionResponse(BaseModel):
    success: bool
    intent: str
    status: str  # success, failed, pending_confirmation, denied
    response_text: str
    entities: Dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "low"
    requires_confirmation: bool = False
    confirmation_id: Optional[str] = None
    execution_time_ms: float = 0.0
    history_id: Optional[int] = None
    data: Optional[Dict[str, Any]] = None


class ConfirmationRequest(BaseModel):
    confirmation_id: str
    approved: bool


class ReminderCreate(BaseModel):
    title: str
    due_time: datetime
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None


class ReminderResponse(BaseModel):
    id: int
    title: str
    due_time: datetime
    is_completed: bool
    is_recurring: bool
    recurrence_pattern: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AppItemCreate(BaseModel):
    app_key: str
    display_name: str
    aliases: List[str] = Field(default_factory=list)
    exec_path: str


class AppItemResponse(BaseModel):
    id: int
    app_key: str
    display_name: str
    aliases: List[str]
    exec_path: str
    is_custom: bool
    is_available: bool

    class Config:
        from_attributes = True


class SystemStatusResponse(BaseModel):
    cpu_percent: float
    cpu_count: int
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_percent: float
    disk_free_gb: float
    disk_total_gb: float
    battery_percent: Optional[float] = None
    is_charging: Optional[bool] = None
    os_name: str
    os_version: str
    hostname: str
    uptime_seconds: float
    is_online: bool


class HistoryItemResponse(BaseModel):
    id: int
    command_text: str
    recognized_intent: str
    entities: Dict[str, Any]
    status: str
    risk_level: str
    response_text: Optional[str]
    execution_time_ms: float
    created_at: datetime


class AnalyticsResponse(BaseModel):
    total_commands: int
    successful_commands: int
    failed_commands: int
    success_rate_percent: float
    average_response_time_ms: float
    commands_today: int
    most_used_intents: List[Dict[str, Any]]
    most_used_apps: List[Dict[str, Any]]
    commands_timeline: List[Dict[str, Any]]


class SpeakRequest(BaseModel):
    text: str
    voice_id: Optional[str] = None
    rate: Optional[int] = None
    volume: Optional[float] = None


class SettingsUpdate(BaseModel):
    app_name: Optional[str] = None
    wake_word: Optional[str] = None
    wake_word_enabled: Optional[bool] = None
    default_language: Optional[str] = None
    tts_rate: Optional[int] = None
    tts_volume: Optional[float] = None
    clipboard_permission_enabled: Optional[bool] = None
    require_confirmation_high_risk: Optional[bool] = None
    require_confirmation_med_risk: Optional[bool] = None
    demo_mode: Optional[bool] = None
    default_browser: Optional[str] = None
    default_music_app: Optional[str] = None
    theme: Optional[str] = None
    openai_api_key: Optional[str] = None
