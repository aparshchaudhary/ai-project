"""
Google Chrome & Browser Automation Handler.
Handles:
- Chrome application execution & window verification
- Web search automation via direct Chrome process dispatch
- Instant answer extraction & summarization
"""

from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional, Tuple

from backend.automation.handlers.base_handler import BaseAppHandler
from backend.services.browser_automation_service import browser_automation_service
from backend.services.desktop_window_manager import desktop_window_manager
from backend.services.event_notification_service import event_notification_service

logger = logging.getLogger(__name__)


class ChromeHandler(BaseAppHandler):
    def __init__(self):
        super().__init__(
            app_key="chrome",
            display_name="Google Chrome",
            supported_actions=["open", "close", "search_web", "open_url", "summarize"],
            required_permissions=["launch_app", "web_access"],
            timeout_seconds=10.0
        )

    def is_installed(self) -> bool:
        app_def = desktop_window_manager.get_app_definition("chrome")
        if not app_def:
            return False
        return bool(desktop_window_manager.resolve_executable_path(app_def.get("candidate_paths", [])))

    async def execute(self, action: str, params: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        action_clean = action.lower().strip()

        # 1. Open Chrome
        if action_clean in ["open", "launch", "open_application"]:
            await event_notification_service.emit_event(
                event_type="task_started",
                title="Opening Google Chrome...",
                message="Status: In Progress",
                status="In Progress",
                metadata={"application": "chrome"}
            )
            res = desktop_window_manager.launch_or_activate("chrome")
            if res.success:
                await event_notification_service.emit_event(
                    event_type="task_completed",
                    title="Google Chrome opened successfully.",
                    message="Status: Completed",
                    status="Completed",
                    metadata={"application": "chrome"}
                )
                return True, "Google Chrome opened successfully.", res.to_dict()
            else:
                await event_notification_service.emit_event(
                    event_type="task_failed",
                    title="Failed to open Google Chrome",
                    message=res.error or "Application could not be launched",
                    status="Failed",
                    metadata={"application": "chrome"}
                )
                return False, res.error or "Could not open Google Chrome.", res.to_dict()

        # 2. Close Chrome
        elif action_clean in ["close", "terminate"]:
            from backend.services.automation_service import automation_service
            success, msg = automation_service.close_app("chrome")
            return success, msg, {"action": "close", "success": success}

        # 3. Web Search
        elif action_clean == "search_web":
            query = params.get("query", "").strip()
            engine = params.get("engine", "google")
            summarize = bool(params.get("summarize", False))

            await event_notification_service.emit_event(
                event_type="task_started",
                title=f"Searching for {query}...",
                message="Status: In Progress",
                status="In Progress",
                metadata={"query": query, "engine": engine}
            )

            res = browser_automation_service.execute_search(query=query, engine=engine, summarize=summarize)
            if res.get("success"):
                await event_notification_service.emit_event(
                    event_type="task_completed",
                    title="Search completed successfully.",
                    message="Status: Completed",
                    status="Completed",
                    metadata=res
                )
                return True, res.get("message", f"Searched for '{query}'."), res
            else:
                await event_notification_service.emit_event(
                    event_type="task_failed",
                    title=f"Search failed for {query}",
                    message=res.get("error", "Search execution failed"),
                    status="Failed",
                    metadata=res
                )
                return False, res.get("error", f"Search failed for '{query}'."), res

        # 4. Open URL
        elif action_clean == "open_url":
            url = params.get("url", "https://google.com")
            res = browser_automation_service.execute_search(query=url)
            return res.get("success", True), f"Navigated to {url}", res

        return False, f"Unsupported action '{action}' on Google Chrome.", {}

    def verify(self, action: str, params: Dict[str, Any], result_data: Dict[str, Any]) -> bool:
        if action in ["open", "launch"]:
            return result_data.get("process_started", False) or result_data.get("window_detected", False)
        if action == "search_web":
            return result_data.get("success", False)
        return True
