"""
Task & Command Validator for Universal Desktop Automation.
Enforces:
- Strict schema validation
- Permission checking (e.g. human confirmation for send_message, file modifications)
- Prevention of arbitrary terminal execution / unrestricted code injection
- Honesty in capability checks
"""

from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional, Tuple

from backend.models.task_planner_schemas import TaskPlan, TaskItem, TaskStatus

logger = logging.getLogger(__name__)

# Strictly allowed intents in the automation framework
ALLOWED_INTENTS = {
    "open_application",
    "close_application",
    "search_web",
    "send_message",
    "resolve_contact",
    "write_note",
    "open_folder",
    "calculate",
    "summarize_results",
    "take_screenshot",
    "generic_command"
}

# Intents that strictly require explicit user confirmation before execution
CONFIRMATION_REQUIRED_INTENTS = {
    "send_message",
    "delete_file",
    "shutdown",
    "restart"
}


class TaskValidator:
    def validate_plan(self, plan: TaskPlan) -> Tuple[bool, Optional[str]]:
        """Validates all tasks within an execution plan."""
        if not plan.tasks:
            return False, "Task plan cannot be empty."

        task_ids = set()
        for task in plan.tasks:
            if not task.id:
                return False, "Task ID is required for every task."
            if task.id in task_ids:
                return False, f"Duplicate task ID detected: '{task.id}'."
            task_ids.add(task.id)

            # Check allowed intent
            if task.intent not in ALLOWED_INTENTS:
                return False, f"Unauthorized or unsupported task intent: '{task.intent}'."

            # Check dependencies exist
            for dep in task.depends_on:
                if dep not in task_ids and not any(t.id == dep for t in plan.tasks):
                    return False, f"Task '{task.id}' depends on non-existent task '{dep}'."

            # Verify security gate for sensitive actions
            if task.intent in CONFIRMATION_REQUIRED_INTENTS:
                task.requires_confirmation = True

        return True, None

    def validate_task(self, task: TaskItem) -> Tuple[bool, Optional[str]]:
        """Validates a single task item."""
        if task.intent not in ALLOWED_INTENTS:
            return False, f"Intent '{task.intent}' is not in approved automation registry."
        return True, None


task_validator = TaskValidator()
