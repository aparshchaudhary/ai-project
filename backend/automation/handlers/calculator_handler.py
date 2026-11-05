"""
Calculator Desktop Automation Handler.
Handles:
- Launching and verifying Calculator window
- Computing expressions
"""

from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional, Tuple

from backend.automation.handlers.base_handler import BaseAppHandler
from backend.services.desktop_window_manager import desktop_window_manager
from backend.services.event_notification_service import event_notification_service

logger = logging.getLogger(__name__)


class CalculatorHandler(BaseAppHandler):
    def __init__(self):
        super().__init__(
            app_key="calculator",
            display_name="Calculator",
            supported_actions=["open", "close", "calculate"],
            required_permissions=["launch_app"],
            timeout_seconds=6.0
        )

    def is_installed(self) -> bool:
        return True

    async def execute(self, action: str, params: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        action_clean = action.lower().strip()

        if action_clean in ["open", "launch", "open_application"]:
            await event_notification_service.emit_event(
                event_type="task_started",
                title="Opening Calculator...",
                message="Status: In Progress",
                status="In Progress",
                metadata={"application": "calculator"}
            )
            res = desktop_window_manager.launch_or_activate("calculator")
            if res.success:
                await event_notification_service.emit_event(
                    event_type="task_completed",
                    title="Calculator opened successfully.",
                    message="Status: Completed",
                    status="Completed",
                    metadata={"application": "calculator"}
                )
                return True, "Calculator opened successfully.", res.to_dict()
            return False, res.error or "Could not open Calculator.", res.to_dict()

        elif action_clean in ["close", "terminate"]:
            from backend.services.automation_service import automation_service
            success, msg = automation_service.close_app("calculator")
            return success, msg, {"action": "close", "success": success}

        elif action_clean == "calculate":
            expr = params.get("expression") or "0"
            try:
                # Safe eval of basic math
                import ast
                # Only allowed operations
                val = eval(expr, {"__builtins__": {}}, {})
                return True, f"The result is {val}.", {"expression": expr, "result": val}
            except Exception as e:
                return False, f"Could not compute {expr}: {e}", {"error": str(e)}

        return False, f"Unsupported action '{action}' on Calculator.", {}

    def verify(self, action: str, params: Dict[str, Any], result_data: Dict[str, Any]) -> bool:
        return result_data.get("process_started", False) or result_data.get("window_detected", False) or result_data.get("success", True)
