"""
Notepad Desktop Automation Handler.
Handles:
- Launching and verifying Notepad window
- Writing meeting notes, saving files in Documents or custom directories
- Opening existing text documents in Notepad
"""

from __future__ import annotations
import os
import time
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from backend.automation.handlers.base_handler import BaseAppHandler
from backend.services.desktop_window_manager import desktop_window_manager, IS_WINDOWS
from backend.services.event_notification_service import event_notification_service

logger = logging.getLogger(__name__)


class NotepadHandler(BaseAppHandler):
    def __init__(self):
        super().__init__(
            app_key="notepad",
            display_name="Notepad",
            supported_actions=["open", "close", "write_note", "write_text", "save_file", "create_note"],
            required_permissions=["launch_app", "write_file"],
            timeout_seconds=8.0
        )

    def is_installed(self) -> bool:
        app_def = desktop_window_manager.get_app_definition("notepad")
        if not app_def:
            return False
        return bool(desktop_window_manager.resolve_executable_path(app_def.get("candidate_paths", [])))

    async def execute(self, action: str, params: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        action_clean = action.lower().strip()

        # 1. Open Notepad
        if action_clean in ["open", "launch", "open_application"]:
            await event_notification_service.emit_event(
                event_type="task_started",
                title="Opening Notepad...",
                message="Status: In Progress",
                status="In Progress",
                metadata={"application": "notepad"}
            )
            res = desktop_window_manager.launch_or_activate("notepad")
            if res.success:
                await event_notification_service.emit_event(
                    event_type="task_completed",
                    title="Notepad opened successfully.",
                    message="Status: Completed",
                    status="Completed",
                    metadata={"application": "notepad"}
                )
                return True, "Notepad opened successfully.", res.to_dict()
            else:
                await event_notification_service.emit_event(
                    event_type="task_failed",
                    title="Failed to open Notepad",
                    message=res.error or "Notepad could not be opened",
                    status="Failed",
                    metadata={"application": "notepad"}
                )
                return False, res.error or "Could not open Notepad.", res.to_dict()

        # 2. Close Notepad
        elif action_clean in ["close", "terminate"]:
            from backend.services.automation_service import automation_service
            success, msg = automation_service.close_app("notepad")
            return success, msg, {"action": "close", "success": success}

        # 3. Write Note / Save File in Documents
        elif action_clean in ["write_note", "write_text", "save_file", "create_note"]:
            note_content = params.get("text") or params.get("content") or params.get("notes") or "Meeting Notes"
            filename = params.get("filename") or "meeting_notes.txt"
            folder = params.get("folder") or "Documents"

            # Resolve user's Documents folder safely
            user_home = Path.home()
            target_dir = user_home / folder
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / filename

            await event_notification_service.emit_event(
                event_type="task_started",
                title=f"Writing note to {filename} in {folder}...",
                message="Status: In Progress",
                status="In Progress",
                metadata={"filename": filename, "folder": folder}
            )

            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            formatted_entry = f"\n--- {timestamp} ---\n{note_content}\n"

            try:
                with open(target_path, "a" if target_path.exists() else "w", encoding="utf-8") as f:
                    f.write(formatted_entry)

                # Open the file in Notepad so user sees it in front of them
                if IS_WINDOWS:
                    subprocess.Popen(["notepad.exe", str(target_path)])
                    time.sleep(0.4)
                    desktop_window_manager.focus_process_window("notepad.exe")

                await event_notification_service.emit_event(
                    event_type="task_completed",
                    title=f"Note saved to {filename} and opened in Notepad.",
                    message="Status: Completed",
                    status="Completed",
                    metadata={"file_path": str(target_path), "filename": filename}
                )

                return True, f"Meeting notes saved to {filename} in {folder} and opened in Notepad.", {
                    "file_path": str(target_path),
                    "filename": filename,
                    "folder": folder,
                    "status": "Completed"
                }

            except Exception as e:
                logger.error(f"Error writing note in Notepad: {e}")
                await event_notification_service.emit_event(
                    event_type="task_failed",
                    title="Failed to write note",
                    message=str(e),
                    status="Failed",
                    metadata={"error": str(e)}
                )
                return False, f"Could not save note to {filename}: {e}", {"error": str(e)}

        return False, f"Unsupported action '{action}' on Notepad.", {}

    def verify(self, action: str, params: Dict[str, Any], result_data: Dict[str, Any]) -> bool:
        if action in ["open", "launch"]:
            return result_data.get("process_started", False) or result_data.get("window_detected", False)
        if action in ["write_note", "save_file"]:
            file_path = result_data.get("file_path")
            return bool(file_path and os.path.exists(file_path))
        return True
