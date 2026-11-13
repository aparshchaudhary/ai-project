"""
SQLAlchemy ORM models for Command History, Reminders, App Registry, and Settings.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, Float, DateTime
from backend.database.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class CommandHistory(Base):
    __tablename__ = "command_history"

    id = Column(Integer, primary_key=True, index=True)
    command_text = Column(String(500), nullable=False)
    recognized_intent = Column(String(100), nullable=False, index=True)
    entities_json = Column(Text, default="{}")
    status = Column(String(50), default="success", index=True)  # success, failed, pending_confirmation, denied
    risk_level = Column(String(20), default="low")  # low, medium, high
    response_text = Column(Text, nullable=True)
    execution_time_ms = Column(Float, default=0.0)
    created_at = Column(DateTime, default=utc_now, index=True)


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    due_time = Column(DateTime, nullable=False, index=True)
    is_completed = Column(Boolean, default=False, index=True)
    is_recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(String(50), nullable=True)  # daily, weekly, hourly
    created_at = Column(DateTime, default=utc_now)


class AppRegistry(Base):
    __tablename__ = "app_registry"

    id = Column(Integer, primary_key=True, index=True)
    app_key = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=False)
    aliases_json = Column(Text, default="[]")
    exec_path = Column(String(500), nullable=False)
    is_custom = Column(Boolean, default=False)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)


class AppSetting(Base):
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value_json = Column(Text, nullable=False)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    phone = Column(String(50), nullable=False)
    email = Column(String(100), nullable=True)
    relationship = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=utc_now)


class UserMemory(Base):
    __tablename__ = "user_memories"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False, index=True)  # preference, workflow, alias, project, app
    key = Column(String(100), nullable=False, index=True)
    value = Column(Text, nullable=False)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class ProductivityItem(Base):
    __tablename__ = "productivity_items"

    id = Column(Integer, primary_key=True, index=True)
    item_type = Column(String(50), nullable=False, index=True)  # voice_note, pomodoro_session, focus_mode, meeting
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)
    status = Column(String(50), default="active")  # active, completed, archived
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=utc_now)


class ConnectedDevice(Base):
    __tablename__ = "connected_devices"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(100), unique=True, index=True, nullable=False)
    device_name = Column(String(100), nullable=False)
    device_type = Column(String(50), nullable=False)  # android | windows | cloud
    pairing_token = Column(String(255), nullable=True)
    status = Column(String(50), default="offline")  # online | offline | busy
    ip_address = Column(String(100), nullable=True)
    capabilities_json = Column(Text, default="[]")
    battery_pct = Column(Integer, nullable=True)
    is_charging = Column(Boolean, default=False)
    ram_usage_pct = Column(Float, nullable=True)
    storage_free_gb = Column(Float, nullable=True)
    system_info_json = Column(Text, default="{}")
    last_seen = Column(DateTime, default=utc_now)
    created_at = Column(DateTime, default=utc_now)


class CrossDeviceTransfer(Base):
    __tablename__ = "cross_device_transfers"

    id = Column(Integer, primary_key=True, index=True)
    transfer_id = Column(String(100), unique=True, index=True, nullable=False)
    source_device_id = Column(String(100), nullable=False)
    target_device_id = Column(String(100), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer, default=0)
    file_path = Column(String(500), nullable=True)
    mime_type = Column(String(100), nullable=True)
    status = Column(String(50), default="pending")  # pending, transferring, completed, failed
    created_at = Column(DateTime, default=utc_now)


