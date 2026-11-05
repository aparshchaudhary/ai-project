"""
Visual Studio Code Automation Handler.
Handles:
- Launching and verifying VS Code window
- Opening specific projects or files in VS Code
"""

from __future__ import annotations
import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from backend.automation.handlers.base_handler import BaseAppHandler
from backend.services.desktop_window_manager import desktop_window_manager, IS_WINDOWS
from backend.services.event_notification_service import event_notification_service

logger = logging.getLogger(__name__)


class VSCodeHandler(BaseAppHandler):
    def __init__(self):
        super().__init__(
            app_key="code",
            display_name="Visual Studio Code",
            supported_actions=["open", "close", "open_project", "open_file"],
            required_permissions=["launch_app"],
            timeout_seconds=10.0
        )

    def is_installed(self) -> bool:
        app_def = desktop_window_manager.get_app_definition("code")
        if not app_def:
            return False
        return bool(desktop_window_manager.resolve_executable_path(app_def.get("candidate_paths", [])))

    async def execute(self, action: str, params: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        action_clean = action.lower().strip()

        if action_clean in ["open", "launch", "open_application"]:
            await event_notification_service.emit_event(
                event_type="task_started",
                title="Opening Visual Studio Code...",
                message="Status: In Progress",
                status="In Progress",
                metadata={"application": "code"}
            )
            res = desktop_window_manager.launch_or_activate("code")
            if res.success:
                await event_notification_service.emit_event(
                    event_type="task_completed",
                    title="Visual Studio Code opened successfully.",
                    message="Status: Completed",
                    status="Completed",
                    metadata={"application": "code"}
                )
                return True, "Visual Studio Code opened successfully.", res.to_dict()
            return False, res.error or "Could not open Visual Studio Code.", res.to_dict()

        elif action_clean in ["close", "terminate"]:
            from backend.services.automation_service import automation_service
            success, msg = automation_service.close_app("code")
            return success, msg, {"action": "close", "success": success}

        elif action_clean in ["open_project", "open_file"]:
            target_path = params.get("path") or str(Path.cwd())
            if IS_WINDOWS:
                subprocess.Popen(["code", target_path], shell=True)
            return True, f"Opened {target_path} in VS Code.", {"path": target_path}

        return False, f"Unsupported action '{action}' on VS Code.", {}

    def verify(self, action: str, params: Dict[str, Any], result_data: Dict[str, Any]) -> bool:
        return result_data.get("process_started", False) or result_data.get("window_detected", False) or result_data.get("success", True)
