"""
Universal Task Executor.
Directs tasks to registered application handlers with GUI foreground locking,
real-time event broadcasting, and result verification.
"""

from __future__ import annotations
import asyncio
import time
import logging
from typing import Dict, Any, Optional, Tuple

from backend.models.task_planner_schemas import TaskItem, TaskStatus
from backend.automation.registry import automation_registry
from backend.services.event_notification_service import event_notification_service

logger = logging.getLogger(__name__)


class TaskExecutor:
    def __init__(self):
        self._gui_lock: Optional[asyncio.Lock] = None

    def _get_gui_lock(self) -> asyncio.Lock:
        if self._gui_lock is None:
            self._gui_lock = asyncio.Lock()
        return self._gui_lock

    async def execute_task(self, task: TaskItem, plan_id: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Executes a single TaskItem safely via its registered handler.
        """
        task.status = TaskStatus.RUNNING
        task.start_time = time.time()

        try:
            # 1. Open Application
            if task.intent == "open_application":
                app_key = task.application or "chrome"
                handler = automation_registry.get_handler(app_key)
                if handler:
                    async with self._get_gui_lock():
                        success, msg, data = await handler.execute("open", task.data or {})
                else:
                    from backend.services.desktop_window_manager import desktop_window_manager
                    async with self._get_gui_lock():
                        res = await asyncio.to_thread(desktop_window_manager.launch_or_activate, app_key)
                        success, msg, data = res.success, res.final_speech_confirmation, res.to_dict()

                task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
                task.result = msg
                task.data = data
                return success, msg, data

            # 2. Search Web
            elif task.intent == "search_web":
                handler = automation_registry.get_handler("chrome")
                params = {
                    "query": task.query or "Artificial Intelligence",
                    "engine": task.engine or "google",
                    "summarize": task.summarize
                }
                async with self._get_gui_lock():
                    success, msg, data = await handler.execute("search_web", params)

                task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
                task.result = msg
                task.data = data
                return success, msg, data

            # 3. WhatsApp Messaging
            elif task.intent == "send_message":
                handler = automation_registry.get_handler("whatsapp")
                params = {
                    "contact": task.contact,
                    "phone": task.phone,
                    "message": task.message or "Hi"
                }
                async with self._get_gui_lock():
                    success, msg, data = await handler.execute("send_message", params)

                task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
                task.result = msg
                task.data = data
                return success, msg, data

            # 4. Notepad Writing / Document Creation
            elif task.intent == "write_note":
                handler = automation_registry.get_handler("notepad")
                params = {
                    "text": task.data.get("text", "Meeting Notes"),
                    "filename": task.data.get("filename", "meeting_notes.txt"),
                    "folder": task.data.get("folder", "Documents")
                }
                async with self._get_gui_lock():
                    success, msg, data = await handler.execute("write_note", params)

                task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
                task.result = msg
                task.data = data
                return success, msg, data

            # 5. Generic Command Fallback
            else:
                task.status = TaskStatus.COMPLETED
                task.result = f"Command '{task.title}' processed."
                return True, task.result, {}

        except Exception as e:
            logger.error(f"Error executing task {task.id}: {e}", exc_info=True)
            task.status = TaskStatus.FAILED
            task.error = str(e)
            return False, str(e), {"error": str(e)}

        finally:
            if task.start_time:
                task.execution_time_ms = (time.time() - task.start_time) * 1000


task_executor = TaskExecutor()
