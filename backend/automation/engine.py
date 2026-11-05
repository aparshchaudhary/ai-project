"""
Universal Desktop Automation Engine.
Central coordinator orchestrating:
- Natural Language Instruction Decomposition
- Intent & Application Identification
- Permission & Security Validation
- Modular Application Handlers
- Strict Sequential / Parallel DAG Scheduling
- Real-Time Windows Native & WebSocket Desktop Notifications
- Spoken Voice Feedback
"""

from __future__ import annotations
import time
import logging
from typing import Dict, Any, Optional, List, Tuple

from backend.automation.registry import automation_registry
from backend.automation.validator import task_validator
from backend.automation.executor import task_executor
from backend.models.task_planner_schemas import TaskPlan, TaskItem, TaskStatus
from backend.services.task_planner import task_planner
from backend.services.task_scheduler import task_scheduler
from backend.services.event_notification_service import event_notification_service
from backend.services.tts_service import tts_service

logger = logging.getLogger(__name__)


class UniversalAutomationEngine:
    def __init__(self):
        self.registry = automation_registry
        self.validator = task_validator
        self.executor = task_executor
        self.planner = task_planner
        self.scheduler = task_scheduler

    async def plan_and_validate(self, instruction: str) -> Tuple[bool, Optional[TaskPlan], Optional[str]]:
        """
        Decomposes natural language instruction into a validated TaskPlan.
        """
        plan = self.planner.plan_instruction(instruction)
        valid, err = self.validator.validate_plan(plan)
        if not valid:
            logger.warning(f"Plan validation rejected: {err}")
            return False, None, err
        return True, plan, None

    async def execute_plan(self, plan: TaskPlan, auto_confirm: bool = False) -> TaskPlan:
        """
        Executes a plan via DAG scheduler respecting dependencies and safety gates.
        """
        # Register in active plans map
        self.scheduler._active_plans[plan.plan_id] = plan
        return await self.scheduler.execute_plan(plan, auto_confirm=auto_confirm)

    def get_capabilities(self, app_key: str) -> Dict[str, Any]:
        """Queries application capabilities from registry."""
        handler = self.registry.get_handler(app_key)
        if handler:
            return handler.get_capabilities()
        return {
            "app_key": app_key,
            "installed": False,
            "supported_actions": [],
            "error": f"Application '{app_key}' not registered in automation engine."
        }

    def list_all_handlers(self) -> List[Dict[str, Any]]:
        """Lists all registered automation handlers."""
        return self.registry.list_handlers()


automation_engine = UniversalAutomationEngine()
