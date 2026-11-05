"""
Centralized Task Event & Desktop Notification Service.
Emits real-time task lifecycle events (command_received, task_started, task_completed, workflow_completed, etc.)
and dispatches genuine native Windows desktop notifications (Action Center Toast / Balloon Tip).
"""

from __future__ import annotations

import os
import time
import subprocess
import threading
import queue
import logging
import asyncio
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class EventNotificationService:
    def __init__(self):
        self._event_history: List[Dict[str, Any]] = []
        self._notify_queue: queue.Queue = queue.Queue()
        self._worker_thread = threading.Thread(target=self._process_native_notifications, daemon=True)
        self._worker_thread.start()

    def _process_native_notifications(self):
        while True:
            try:
                item = self._notify_queue.get()
                if item is None:
                    break
                title, message, status = item
                if os.name == "nt":
                    self._show_windows_toast(title, message, status)
                self._notify_queue.task_done()
            except Exception as e:
                logger.debug(f"Notification worker error: {e}")

    def _show_windows_toast(self, title: str, message: str, status: str = ""):
        safe_title = (title or "Voice Assistant").replace("'", "''").replace('"', '`"').replace("\n", " ").strip()
        safe_msg = (message or "").replace("'", "''").replace('"', '`"').replace("\n", " ").strip()
        if status and status not in safe_msg:
            safe_msg = f"Status: {status} | {safe_msg}" if safe_msg else f"Status: {status}"

        ps_cmd = f'''
try {{
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    `$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
    `$texts = `$template.GetElementsByTagName('text')
    `$null = `$texts.Item(0).AppendChild(`$template.CreateTextNode('{safe_title}'))
    `$null = `$texts.Item(1).AppendChild(`$template.CreateTextNode('{safe_msg}'))
    `$toast = [Windows.UI.Notifications.ToastNotification]::new(`$template)
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Aura Voice Assistant').Show(`$toast)
}} catch {{
    Add-Type -AssemblyName System.Windows.Forms
    `$b = New-Object System.Windows.Forms.NotifyIcon
    `$b.Icon = [System.Drawing.SystemIcons]::Information
    `$b.BalloonTipTitle = '{safe_title}'
    `$b.BalloonTipText = '{safe_msg}'
    `$b.Visible = `$True
    `$b.ShowBalloonTip(3000)
    Start-Sleep -Milliseconds 150
    `$b.Dispose()
}}
'''
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                timeout=4.0
            )
        except Exception as ex:
            logger.debug(f"Native notification failed: {ex}")

    async def emit_event(
        self,
        event_type: str,
        title: str,
        message: str = "",
        status: str = "In Progress",
        task_id: Optional[str] = None,
        plan_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Emits task lifecycle event:
        1. Queues genuine native Windows desktop notification.
        2. Broadcasts WebSocket task_event to UI in real-time.
        3. Records in event history.
        """
        evt = {
            "id": f"evt_{int(time.time() * 1000)}",
            "event_type": event_type,
            "title": title,
            "message": message,
            "status": status,
            "task_id": task_id,
            "plan_id": plan_id,
            "metadata": metadata or {},
            "timestamp": time.strftime("%H:%M:%S")
        }

        self._event_history.append(evt)
        if len(self._event_history) > 100:
            self._event_history.pop(0)

        # 1. Native Windows Desktop Notification (non-blocking)
        self._notify_queue.put((title, message, status))

        # 2. WebSocket real-time broadcast to UI
        try:
            from backend.api.websocket import ws_manager
            await ws_manager.broadcast({
                "type": "task_event",
                "event": evt
            })
        except Exception as ws_err:
            logger.debug(f"WS task_event broadcast error: {ws_err}")

        return evt

    def emit_event_sync(
        self,
        event_type: str,
        title: str,
        message: str = "",
        status: str = "In Progress",
        task_id: Optional[str] = None,
        plan_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Synchronous wrapper for non-async callers."""
        evt = {
            "id": f"evt_{int(time.time() * 1000)}",
            "event_type": event_type,
            "title": title,
            "message": message,
            "status": status,
            "task_id": task_id,
            "plan_id": plan_id,
            "metadata": metadata or {},
            "timestamp": time.strftime("%H:%M:%S")
        }
        self._event_history.append(evt)
        if len(self._event_history) > 100:
            self._event_history.pop(0)

        self._notify_queue.put((title, message, status))
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                from backend.api.websocket import ws_manager
                asyncio.run_coroutine_threadsafe(
                    ws_manager.broadcast({"type": "task_event", "event": evt}),
                    loop
                )
        except Exception:
            pass
        return evt

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._event_history[-limit:]


event_notification_service = EventNotificationService()
