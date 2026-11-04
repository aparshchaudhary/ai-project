"""
Pydantic Schemas for Multi-Command Execution, Task Planning, and Cross-App Automation.
"""

from __future__ import annotations
import time
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class TaskStatus(str, Enum):
    PENDING = "Pending"
    PLANNING = "Planning"
    RUNNING = "Running"
    WAITING_CONFIRMATION = "Waiting for Confirmation"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"
    SKIPPED = "Skipped"


class TaskItem(BaseModel):
    id: str = Field(description="Unique task identifier, e.g., task_1")
    title: str = Field(description="Human-readable step description, e.g., Open Google Chrome")
    intent: str = Field(description="Normalized action intent: open_application, search_web, send_message, etc.")
    application: Optional[str] = None
    query: Optional[str] = None
    engine: Optional[str] = "google"
    contact: Optional[str] = None
    message: Optional[str] = None
    phone: Optional[str] = None
    url: Optional[str] = None
    summarize: Optional[bool] = False
    depends_on: List[str] = Field(default_factory=list, description="IDs of tasks that must finish before this task runs")
    requires_confirmation: bool = False
    risk_level: str = "low"  # low, medium, high
    status: TaskStatus = TaskStatus.PENDING
    start_time: Optional[float] = None
    execution_time_ms: Optional[float] = None
    result: Optional[str] = None
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "intent": self.intent,
            "application": self.application,
            "query": self.query,
            "engine": self.engine,
            "contact": self.contact,
            "message": self.message,
            "phone": self.phone,
            "url": self.url,
            "summarize": self.summarize,
            "depends_on": self.depends_on,
            "requires_confirmation": self.requires_confirmation,
            "risk_level": self.risk_level,
            "status": self.status.value if isinstance(self.status, TaskStatus) else str(self.status),
            "start_time": self.start_time,
            "execution_time_ms": round(self.execution_time_ms, 1) if self.execution_time_ms is not None else None,
            "result": self.result,
            "error": self.error,
            "data": self.data or {}
        }


class TaskPlan(BaseModel):
    plan_id: str
    original_instruction: str
    tasks: List[TaskItem] = Field(default_factory=list)
    status: str = "created"  # created, planning, running, waiting_confirmation, completed, partially_failed, failed, cancelled
    created_at: float = Field(default_factory=time.time)
    summary: Optional[str] = None
    requires_confirmation: bool = False
    confirmation_id: Optional[str] = None
    ambiguous_contacts: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "original_instruction": self.original_instruction,
            "tasks": [t.to_dict() for t in self.tasks],
            "status": self.status,
            "created_at": self.created_at,
            "summary": self.summary,
            "requires_confirmation": self.requires_confirmation,
            "confirmation_id": self.confirmation_id,
            "ambiguous_contacts": self.ambiguous_contacts or []
        }


class ContactSchema(BaseModel):
    id: Optional[int] = None
    name: str
    phone: str
    email: Optional[str] = None
    relationship: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
