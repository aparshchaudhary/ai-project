"""
Microsoft Office Automation Handlers (Word, Excel, PowerPoint).
Provides concrete capability definitions:
- Launching / activating
- Creating documents
- Opening files
- Window verification
"""

from __future__ import annotations
import os
import subprocess
import logging
from typing import Dict, Any, List, Optional, Tuple

from backend.automation.handlers.base_handler import BaseAppHandler
from backend.services.desktop_window_manager import desktop_window_manager, IS_WINDOWS

logger = logging.getLogger(__name__)


class WordHandler(BaseAppHandler):
    def __init__(self):
        super().__init__(
            app_key="word",
            display_name="Microsoft Word",
            supported_actions=["open", "close", "create_document", "open_document"],
            required_permissions=["launch_apps", "access_filesystem"],
            timeout_seconds=10.0
        )

    def is_installed(self) -> bool:
        app_def = desktop_window_manager.get_app_definition("word")
        return bool(app_def and desktop_window_manager.resolve_executable_path(app_def.get("candidate_paths", [])))

    def verify(self, action: str, params: Dict[str, Any], result_data: Dict[str, Any]) -> bool:
        return bool(result_data.get("success") or result_data.get("window_detected") or result_data.get("process_started"))

    async def execute(self, action: str, params: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        action_clean = action.lower().strip()
        if action_clean in ["open", "launch", "open_application"]:
            res = desktop_window_manager.launch_or_activate("word")
            msg = "Microsoft Word is now open." if res.success else res.final_speech_confirmation
            return res.success, msg, res.to_dict()
        elif action_clean == "create_document":
            res = desktop_window_manager.launch_or_activate("word")
            return res.success, "Opened Word with a new document.", res.to_dict()
        elif action_clean == "open_document":
            file_path = params.get("file_path", "")
            if file_path and os.path.exists(file_path):
                if IS_WINDOWS and hasattr(os, "startfile"):
                    os.startfile(file_path)
                    return True, f"Opened document in Word: {os.path.basename(file_path)}", {"file_path": file_path}
            res = desktop_window_manager.launch_or_activate("word")
            return res.success, "Opened Microsoft Word.", res.to_dict()
        return False, f"Unsupported action '{action}' on Word.", {}


class ExcelHandler(BaseAppHandler):
    def __init__(self):
        super().__init__(
            app_key="excel",
            display_name="Microsoft Excel",
            supported_actions=["open", "close", "create_sheet", "open_sheet"],
            required_permissions=["launch_apps", "access_filesystem"],
            timeout_seconds=10.0
        )

    def is_installed(self) -> bool:
        app_def = desktop_window_manager.get_app_definition("excel")
        return bool(app_def and desktop_window_manager.resolve_executable_path(app_def.get("candidate_paths", [])))

    def verify(self, action: str, params: Dict[str, Any], result_data: Dict[str, Any]) -> bool:
        return bool(result_data.get("success") or result_data.get("window_detected") or result_data.get("process_started"))

    async def execute(self, action: str, params: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        action_clean = action.lower().strip()
        if action_clean in ["open", "launch", "open_application"]:
            res = desktop_window_manager.launch_or_activate("excel")
            msg = "Microsoft Excel is now open." if res.success else res.final_speech_confirmation
            return res.success, msg, res.to_dict()
        elif action_clean == "create_sheet":
            res = desktop_window_manager.launch_or_activate("excel")
            return res.success, "Opened Excel with a new spreadsheet.", res.to_dict()
        return False, f"Unsupported action '{action}' on Excel.", {}


class PowerPointHandler(BaseAppHandler):
    def __init__(self):
        super().__init__(
            app_key="powerpoint",
            display_name="Microsoft PowerPoint",
            supported_actions=["open", "close", "create_presentation", "open_presentation"],
            required_permissions=["launch_apps", "access_filesystem"],
            timeout_seconds=10.0
        )

    def is_installed(self) -> bool:
        app_def = desktop_window_manager.get_app_definition("powerpoint")
        return bool(app_def and desktop_window_manager.resolve_executable_path(app_def.get("candidate_paths", [])))

    def verify(self, action: str, params: Dict[str, Any], result_data: Dict[str, Any]) -> bool:
        return bool(result_data.get("success") or result_data.get("window_detected") or result_data.get("process_started"))

    async def execute(self, action: str, params: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        action_clean = action.lower().strip()
        if action_clean in ["open", "launch", "open_application"]:
            res = desktop_window_manager.launch_or_activate("powerpoint")
            msg = "Microsoft PowerPoint is now open." if res.success else res.final_speech_confirmation
            return res.success, msg, res.to_dict()
        return False, f"Unsupported action '{action}' on PowerPoint.", {}
