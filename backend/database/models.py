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
