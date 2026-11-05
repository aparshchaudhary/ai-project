"""
Universal Desktop Automation Module.
"""

from backend.automation.engine import automation_engine, UniversalAutomationEngine
from backend.automation.registry import automation_registry, AutomationRegistry
from backend.automation.validator import task_validator, TaskValidator
from backend.automation.executor import task_executor, TaskExecutor
from backend.automation.handlers import (
    BaseAppHandler,
    WhatsAppHandler,
    ChromeHandler,
    NotepadHandler,
    VSCodeHandler,
    ExplorerHandler,
    CalculatorHandler,
    SpotifyHandler
)

__all__ = [
    "automation_engine",
    "UniversalAutomationEngine",
    "automation_registry",
    "AutomationRegistry",
    "task_validator",
    "TaskValidator",
    "task_executor",
    "TaskExecutor",
    "BaseAppHandler",
    "WhatsAppHandler",
    "ChromeHandler",
    "NotepadHandler",
    "VSCodeHandler",
    "ExplorerHandler",
    "CalculatorHandler",
    "SpotifyHandler"
]
