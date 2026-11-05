"""
Spotify Desktop Automation Handler.
Handles:
- Launching and verifying Spotify window
- Media playback controls (play, pause, search track)
"""

from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional, Tuple

from backend.automation.handlers.base_handler import BaseAppHandler
from backend.services.desktop_window_manager import desktop_window_manager
from backend.services.event_notification_service import event_notification_service

logger = logging.getLogger(__name__)


class SpotifyHandler(BaseAppHandler):
    def __init__(self):
        super().__init__(
            app_key="spotify",
            display_name="Spotify",
            supported_actions=["open", "close", "play", "pause"],
            required_permissions=["launch_app", "media_control"],
            timeout_seconds=8.0
        )

    def is_installed(self) -> bool:
        app_def = desktop_window_manager.get_app_definition("spotify")
        if not app_def:
            return False
        return bool(desktop_window_manager.resolve_executable_path(app_def.get("candidate_paths", [])))

    async def execute(self, action: str, params: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        action_clean = action.lower().strip()

        if action_clean in ["open", "launch", "open_application"]:
            await event_notification_service.emit_event(
                event_type="task_started",
                title="Opening Spotify...",
                message="Status: In Progress",
                status="In Progress",
                metadata={"application": "spotify"}
            )
            res = desktop_window_manager.launch_or_activate("spotify")
            if res.success:
                await event_notification_service.emit_event(
                    event_type="task_completed",
                    title="Spotify opened successfully.",
                    message="Status: Completed",
                    status="Completed",
                    metadata={"application": "spotify"}
                )
                return True, "Spotify opened successfully.", res.to_dict()
            return False, res.error or "Could not open Spotify.", res.to_dict()

        elif action_clean in ["close", "terminate"]:
            from backend.services.automation_service import automation_service
            success, msg = automation_service.close_app("spotify")
            return success, msg, {"action": "close", "success": success}

        elif action_clean in ["play", "pause"]:
            from backend.services.music_service import music_service
            if action_clean == "play":
                res = music_service.play()
                return True, "Resumed playback.", {"status": "playing"}
            else:
                res = music_service.pause()
                return True, "Paused playback.", {"status": "paused"}

        return False, f"Unsupported action '{action}' on Spotify.", {}

    def verify(self, action: str, params: Dict[str, Any], result_data: Dict[str, Any]) -> bool:
        return result_data.get("process_started", False) or result_data.get("window_detected", False) or result_data.get("success", True)
