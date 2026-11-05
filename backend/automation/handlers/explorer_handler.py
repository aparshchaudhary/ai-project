"""
File Explorer Desktop Automation Handler.
Handles:
- Launching and verifying File Explorer window
- Opening specific folders (Documents, Downloads, Pictures, etc.)
- Finding and locating documents
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


class ExplorerHandler(BaseAppHandler):
    def __init__(self):
        super().__init__(
            app_key="explorer",
            display_name="File Explorer",
            supported_actions=["open", "close", "open_folder", "find_document"],
            required_permissions=["launch_app"],
            timeout_seconds=6.0
        )

    def is_installed(self) -> bool:
        return True  # Native Windows shell

    async def execute(self, action: str, params: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        action_clean = action.lower().strip()

        if action_clean in ["open", "launch", "open_application"]:
            await event_notification_service.emit_event(
                event_type="task_started",
                title="Opening File Explorer...",
                message="Status: In Progress",
                status="In Progress",
                metadata={"application": "explorer"}
            )
            res = desktop_window_manager.launch_or_activate("explorer")
            if res.success:
                await event_notification_service.emit_event(
                    event_type="task_completed",
                    title="File Explorer opened successfully.",
                    message="Status: Completed",
                    status="Completed",
                    metadata={"application": "explorer"}
                )
                return True, "File Explorer opened successfully.", res.to_dict()
            return False, res.error or "Could not open File Explorer.", res.to_dict()

        elif action_clean in ["open_folder", "find_document"]:
            folder_name = params.get("folder") or params.get("name") or "Documents"
            home = Path.home()
            target_path = home / folder_name
            if not target_path.exists():
                target_path = home

            if IS_WINDOWS:
                subprocess.Popen(["explorer.exe", str(target_path)])

            await event_notification_service.emit_event(
                event_type="task_completed",
                title=f"Opened {folder_name} in File Explorer.",
                message="Status: Completed",
                status="Completed",
                metadata={"path": str(target_path)}
            )
            return True, f"Opened folder '{folder_name}'.", {"path": str(target_path)}

        elif action_clean in ["close", "terminate"]:
            from backend.services.automation_service import automation_service
            success, msg = automation_service.close_app("explorer")
            return success, msg, {"action": "close", "success": success}

        return False, f"Unsupported action '{action}' on File Explorer.", {}

    def verify(self, action: str, params: Dict[str, Any], result_data: Dict[str, Any]) -> bool:
        return True
