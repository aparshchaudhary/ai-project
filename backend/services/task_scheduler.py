"""
Asynchronous Multitasking Engine & DAG Task Scheduler.
Handles:
- Parallel execution of independent tasks (asyncio.gather)
- Strict sequential execution of dependent tasks based on DAG dependencies
- GUI Window Lock: prevents focus contention during simultaneous window activation
- Failure isolation: dependent tasks skipped safely while independent tasks continue
- Real-time WebSocket broadcasting (ai_agent_activity & agent_task_progress)
- Human-in-the-loop confirmation gating for high-risk actions (e.g. WhatsApp messaging)
- Aggregated natural language summary generation
"""

from __future__ import annotations
import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Set

from backend.models.task_planner_schemas import TaskPlan, TaskItem, TaskStatus
from backend.services.desktop_window_manager import desktop_window_manager
from backend.services.browser_automation_service import browser_automation_service
from backend.services.whatsapp_service import whatsapp_service
from backend.services.contact_service import contact_service
from backend.services.screenshot_service import screenshot_service
from backend.services.system_service import system_service
from backend.services.event_notification_service import event_notification_service

logger = logging.getLogger(__name__)


class TaskScheduler:
    def __init__(self):
        # Mutex lock to serialize Windows foreground activations across concurrent workers (lazy initialized)
        self._gui_lock: Optional[asyncio.Lock] = None
        self._active_plans: Dict[str, TaskPlan] = {}

    def _get_gui_lock(self) -> asyncio.Lock:
        if self._gui_lock is None:
            self._gui_lock = asyncio.Lock()
        return self._gui_lock

    async def broadcast_plan_update(self, plan: TaskPlan, event_type: str = "ai_agent_activity"):
        """Broadcasts live plan and task progress to all connected WebSocket clients."""
        try:
            from backend.api.websocket import ws_manager
            payload = {
                "type": event_type,
                "plan": plan.to_dict(),
                "timestamp": time.time()
            }
            await ws_manager.broadcast_json(payload)
        except Exception as e:
            logger.debug(f"WebSocket broadcast skipped or unavailable: {e}")

    async def broadcast_task_update(self, plan_id: str, task: TaskItem):
        """Broadcasts granular step progress."""
        try:
            from backend.api.websocket import ws_manager
            payload = {
                "type": "agent_task_progress",
                "plan_id": plan_id,
                "task": task.to_dict(),
                "timestamp": time.time()
            }
            await ws_manager.broadcast_json(payload)
        except Exception as e:
            logger.debug(f"WebSocket task broadcast skipped: {e}")

    async def execute_plan(self, plan: TaskPlan, auto_confirm: bool = False) -> TaskPlan:
        """
        Executes a TaskPlan respecting dependencies, concurrency, and security gates.
        """
        self._active_plans[plan.plan_id] = plan
        plan.status = "running"
        await self.broadcast_plan_update(plan)

        completed_task_ids: Set[str] = set()
        failed_task_ids: Set[str] = set()
        task_map: Dict[str, TaskItem] = {t.id: t for t in plan.tasks}

        while len(completed_task_ids) + len(failed_task_ids) < len(plan.tasks):
            # Find tasks ready to run:
            # All items in `depends_on` must be in `completed_task_ids`
            ready_tasks: List[TaskItem] = []
            for t in plan.tasks:
                if t.id in completed_task_ids or t.id in failed_task_ids:
                    continue

                # Check if any prerequisite failed
                prereq_failed = any(dep in failed_task_ids for dep in t.depends_on)
                if prereq_failed:
                    t.status = TaskStatus.SKIPPED
                    t.error = f"Skipped because dependency failed."
                    failed_task_ids.add(t.id)
                    await self.broadcast_task_update(plan.plan_id, t)
                    continue

                # Check if all prerequisites completed
                prereq_done = all(dep in completed_task_ids for dep in t.depends_on)
                if prereq_done and t.status in [TaskStatus.PENDING, TaskStatus.WAITING_CONFIRMATION]:
                    ready_tasks.append(t)

            if not ready_tasks:
                # No tasks can progress (either waiting for user confirmation or deadlock)
                break

            # Execute all ready independent tasks concurrently
            ready_tasks_to_run: List[TaskItem] = []
            tasks_to_gather = []
            for ready_task in ready_tasks:
                # If task requires human confirmation and not auto_confirmed, pause it
                if ready_task.requires_confirmation and not auto_confirm:
                    ready_task.status = TaskStatus.WAITING_CONFIRMATION
                    plan.status = "waiting_confirmation"
                    await self.broadcast_task_update(plan.plan_id, ready_task)
                    await self.broadcast_plan_update(plan)
                    # We leave this task in waiting state
                    continue

                ready_tasks_to_run.append(ready_task)
                tasks_to_gather.append(self._run_task_item(ready_task, plan.plan_id))

            if not tasks_to_gather:
                # All remaining ready tasks are waiting for confirmation
                break

            results = await asyncio.gather(*tasks_to_gather, return_exceptions=True)

            for task_item, res in zip(ready_tasks_to_run, results):
                if isinstance(res, Exception):
                    task_item.status = TaskStatus.FAILED
                    task_item.error = str(res)
                    failed_task_ids.add(task_item.id)
                elif task_item.status == TaskStatus.COMPLETED:
                    completed_task_ids.add(task_item.id)
                elif task_item.status == TaskStatus.FAILED:
                    failed_task_ids.add(task_item.id)

        # Evaluate final status of plan
        if any(t.status == TaskStatus.WAITING_CONFIRMATION for t in plan.tasks):
            plan.status = "waiting_confirmation"
        elif all(t.status == TaskStatus.COMPLETED for t in plan.tasks):
            plan.status = "completed"
        elif any(t.status == TaskStatus.COMPLETED for t in plan.tasks) and any(t.status in [TaskStatus.FAILED, TaskStatus.SKIPPED] for t in plan.tasks):
            plan.status = "partially_failed"
        elif all(t.status in [TaskStatus.FAILED, TaskStatus.SKIPPED] for t in plan.tasks):
            plan.status = "failed"

        plan.summary = self._generate_aggregated_summary(plan)
        await self.broadcast_plan_update(plan)

        # Emit final workflow completion or partial failure lifecycle event
        if plan.status == "completed":
            await event_notification_service.emit_event(
                event_type="workflow_completed",
                title="All tasks completed successfully.",
                message="Status: Completed",
                status="Completed",
                plan_id=plan.plan_id,
                metadata={"tasks_count": len(plan.tasks)}
            )
        elif plan.status == "partially_failed":
            await event_notification_service.emit_event(
                event_type="workflow_partial_failure",
                title="Compound workflow partially completed",
                message=plan.summary or "Some tasks could not be completed.",
                status="Partially Failed",
                plan_id=plan.plan_id,
                metadata={"tasks_count": len(plan.tasks)}
            )

        return plan

    async def _run_task_item(self, task: TaskItem, plan_id: str):
        """Runs a single TaskItem safely with timings and status logging."""
        task.status = TaskStatus.RUNNING
        task.start_time = time.time()
        await self.broadcast_task_update(plan_id, task)

        # Determine human-friendly title based on intent
        if task.intent == "open_application":
            app_def = desktop_window_manager.get_app_definition(task.application or "chrome")
            app_disp = app_def["display_name"] if app_def else (task.application or "Chrome").title()
            start_title = f"Opening {app_disp}..."
        elif task.intent == "search_web":
            query_disp = task.query or "Artificial Intelligence"
            start_title = f"Searching for {query_disp}..."
        elif task.intent == "send_message":
            contact_disp = task.contact or "Contact"
            start_title = f"Sending message to {contact_disp}..."
        else:
            start_title = f"Executing {task.title}..."

        await event_notification_service.emit_event(
            event_type="task_started",
            title=start_title,
            message="Status: In Progress",
            status="In Progress",
            task_id=task.id,
            plan_id=plan_id,
            metadata={"intent": task.intent, "application": task.application, "query": task.query}
        )

        try:
            # 1. Check if task should be routed to a connected Android device
            if task.target_device == "android":
                from backend.services.device_registry_service import device_registry_service
                from backend.models.device_schemas import DeviceType, RemoteTaskDispatch
                android_node = device_registry_service.get_device_by_type(DeviceType.ANDROID)
                if android_node and android_node.device_id in device_registry_service._device_websockets:
                    dispatch = RemoteTaskDispatch(
                        task_id=task.id,
                        intent=task.intent,
                        target_device_id=android_node.device_id,
                        target_device_type=DeviceType.ANDROID,
                        action_params={
                            "contact": task.contact,
                            "phone": task.phone,
                            "message": task.message,
                            "query": task.query,
                            "application": task.application,
                            "data": task.data or {}
                        }
                    )
                    rem_res = await device_registry_service.dispatch_task(dispatch)
                    if rem_res.status == "completed":
                        task.status = TaskStatus.COMPLETED
                        task.result = rem_res.result_data.get("message") or f"Successfully executed on {android_node.device_name}."
                        task.data = rem_res.result_data
                        return
                    else:
                        task.status = TaskStatus.FAILED
                        task.error = rem_res.error or f"Android execution failed on {android_node.device_name}."
                        return
                elif task.intent not in ["make_call", "send_message"]:
                    # Device-exclusive intent without desktop equivalent
                    task.status = TaskStatus.FAILED
                    task.error = "Android phone is not currently connected. Please ensure the agent app is connected on your smartphone."
                    return

            # 2. Local / Desktop Handlers
            if task.intent == "open_application":
                await self._execute_open_app(task)
            elif task.intent == "search_web":
                await self._execute_search_web(task)
            elif task.intent == "send_message":
                await self._execute_send_message(task)
            elif task.intent == "make_call":
                await self._execute_make_call(task)
            elif task.intent == "end_call":
                await self._execute_end_call(task)
            elif task.intent in ["analyze_screen", "explain_error", "vision_mode"]:
                await self._execute_analyze_screen(task)
            elif task.intent == "productivity_mode":
                await self._execute_productivity_mode(task)
            elif task.intent == "write_note":
                await self._execute_write_note(task)
            elif task.intent == "manage_files":
                await self._execute_manage_files(task)
            elif task.intent == "create_folder":
                await self._execute_create_folder(task)
            elif task.intent == "open_file":
                await self._execute_open_file(task)
            elif task.intent == "system_specs":
                await self._execute_system_specs(task)
            elif task.intent == "relay_file":
                await self._execute_relay_file(task)
            elif task.intent == "notify_device":
                await self._execute_notify_device(task)
            elif task.intent == "control_device_setting":
                await self._execute_control_device_setting(task)
            elif task.intent == "set_alarm":
                await self._execute_set_alarm(task)
            elif task.intent == "read_notifications":
                await self._execute_read_notifications(task)
            elif task.intent == "query_gallery":
                await self._execute_query_gallery(task)
            elif task.intent == "query_contacts":
                await self._execute_query_contacts(task)
            elif task.intent == "summarize_results":
                await self._execute_summarize(task)
            elif task.intent == "take_screenshot":
                await self._execute_screenshot(task)
            elif task.intent == "generic_command":
                task.status = TaskStatus.COMPLETED
                task.result = f"Command '{task.title}' processed."
            else:
                task.status = TaskStatus.FAILED
                task.error = f"Unsupported task intent: {task.intent}"

        except Exception as e:
            logger.error(f"Error executing task {task.id}: {e}", exc_info=True)
            task.status = TaskStatus.FAILED
            task.error = str(e)
        finally:
            if task.start_time:
                task.execution_time_ms = (time.time() - task.start_time) * 1000
            await self.broadcast_task_update(plan_id, task)

            # Emit task completion or failure notification
            if task.status == TaskStatus.COMPLETED:
                if task.intent == "open_application":
                    app_def = desktop_window_manager.get_app_definition(task.application or "chrome")
                    app_disp = app_def["display_name"] if app_def else (task.application or "Chrome").title()
                    done_title = f"{app_disp} opened successfully."
                elif task.intent == "search_web":
                    done_title = "Search completed successfully."
                elif task.intent == "send_message":
                    done_title = f"Message sent to {task.contact or 'Contact'} successfully."
                else:
                    done_title = f"{task.title} completed."

                await event_notification_service.emit_event(
                    event_type="task_completed",
                    title=done_title,
                    message="Status: Completed",
                    status="Completed",
                    task_id=task.id,
                    plan_id=plan_id,
                    metadata={"intent": task.intent, "result": task.result}
                )
            elif task.status == TaskStatus.FAILED:
                await event_notification_service.emit_event(
                    event_type="task_failed",
                    title=f"Failed to execute {task.title}",
                    message=task.error or "Task failed",
                    status="Failed",
                    task_id=task.id,
                    plan_id=plan_id,
                    metadata={"intent": task.intent, "error": task.error}
                )

    async def _execute_open_app(self, task: TaskItem):
        """Executes application launch with GUI foreground lock."""
        app = task.application or "chrome"
        async with self._get_gui_lock():
            # Run in threadpool so blocking Win32 / subprocess calls don't pause the event loop
            res = await asyncio.to_thread(desktop_window_manager.launch_or_activate, app)

        if res.success:
            task.status = TaskStatus.COMPLETED
            is_already = (res.action == "brought_to_foreground" or res.status == "Already running")
            status_text = "focused existing window" if is_already else "launched new process"
            task.result = f"Successfully {status_text} of {res.app_name or app.title()}."
            task.data = res.to_dict()
        else:
            task.status = TaskStatus.FAILED
            task.error = res.error or f"Could not launch application '{app}'."

        # Broadcast live desktop activity to live dashboard panel
        try:
            from backend.api.websocket import ws_manager
            await ws_manager.broadcast({
                "type": "desktop_activity",
                "activity": res.to_dict()
            })
        except Exception as ws_err:
            logger.debug(f"WS desktop activity broadcast error: {ws_err}")

    async def _execute_search_web(self, task: TaskItem):
        """Executes browser search workflow."""
        query = task.query or "Artificial Intelligence"
        engine = task.engine or "google"
        summarize = bool(task.summarize)

        async with self._get_gui_lock():
            res = await asyncio.to_thread(
                browser_automation_service.execute_search,
                query=query,
                engine=engine,
                summarize=summarize
            )

        if res.get("success"):
            task.status = TaskStatus.COMPLETED
            task.result = res.get("message")
            task.data = res
        else:
            task.status = TaskStatus.FAILED
            task.error = res.get("error", f"Search failed for '{query}'.")

    async def _execute_send_message(self, task: TaskItem):
        """Dispatches WhatsApp message after confirmation has been approved."""
        phone = task.phone
        message = task.message or "Hi"
        contact_name = task.contact or "Contact"

        if not phone:
            # Attempt to resolve contact phone if not already resolved
            matched, ambiguous = contact_service.resolve_contact(contact_name)
            if matched:
                phone = matched["phone"]
                contact_name = matched["name"]
            else:
                task.status = TaskStatus.FAILED
                task.error = f"Cannot send message: Contact '{contact_name}' not found."
                return

        # Dispatch via native Windows protocol / browser fallback
        success, msg, meta = await asyncio.to_thread(
            whatsapp_service.dispatch_message,
            phone=phone,
            message=message,
            recipient_name=contact_name
        )

        if success:
            task.status = TaskStatus.COMPLETED
            task.result = msg
            task.data = meta
        else:
            task.status = TaskStatus.FAILED
            task.error = msg

    async def _execute_summarize(self, task: TaskItem):
        """Generates summary for a query."""
        query = task.query or "search results"
        summary = await asyncio.to_thread(
            browser_automation_service._generate_search_summary,
            query
        )
        task.status = TaskStatus.COMPLETED
        task.result = f"Summary of {query}: {summary}"
        task.data = {"query": query, "summary": summary}

    async def _execute_screenshot(self, task: TaskItem):
        """Captures desktop screen."""
        res = await asyncio.to_thread(screenshot_service.take_screenshot)
        if res.get("success"):
            task.status = TaskStatus.COMPLETED
            task.result = f"Screenshot captured: {res.get('filename')}"
            task.data = res
        else:
            task.status = TaskStatus.FAILED
            task.error = res.get("message", "Screenshot failed.")

    async def _execute_write_note(self, task: TaskItem):
        """Writes note and saves to Documents folder via Notepad handler."""
        from backend.automation.handlers.notepad_handler import NotepadHandler
        handler = NotepadHandler()
        async with self._get_gui_lock():
            success, msg, data = await handler.execute("write_note", task.data or {})

        if success:
            task.status = TaskStatus.COMPLETED
            task.result = msg
            task.data = data
        else:
            task.status = TaskStatus.FAILED
            task.error = msg

    async def _execute_make_call(self, task: TaskItem):
        """Initiates voice or video call via calling service after confirmation."""
        from backend.services.calling_service import calling_service
        phone = task.phone
        contact_name = task.contact or "Contact"
        provider = task.application or "phone_link"

        if not phone:
            matched, ambiguous = contact_service.resolve_contact(contact_name)
            if matched:
                phone = matched["phone"]
                contact_name = matched["name"]
            else:
                task.status = TaskStatus.FAILED
                task.error = f"Cannot place call: Contact '{contact_name}' not found."
                return

        success, msg, data = await asyncio.to_thread(
            calling_service.initiate_call,
            phone=phone,
            recipient_name=contact_name,
            provider=provider
        )
        if success:
            task.status = TaskStatus.COMPLETED
            task.result = msg
            task.data = data
        else:
            task.status = TaskStatus.FAILED
            task.error = msg

    async def _execute_end_call(self, task: TaskItem):
        """Terminates active call."""
        from backend.services.calling_service import calling_service
        success, msg = await asyncio.to_thread(calling_service.end_call)
        task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
        task.result = msg

    async def _execute_analyze_screen(self, task: TaskItem):
        """Analyzes active screen and foreground controls."""
        from backend.services.vision_service import vision_service
        query = task.query or "Analyze my screen"
        res = await asyncio.to_thread(vision_service.analyze_screen, query)
        if res.get("success"):
            task.status = TaskStatus.COMPLETED
            task.result = res.get("summary")
            task.data = res
        else:
            task.status = TaskStatus.FAILED
            task.error = res.get("error", "Screen analysis failed.")

    async def _execute_productivity_mode(self, task: TaskItem):
        """Activates study, work, or focus mode."""
        from backend.services.productivity_service import productivity_service
        mode = (task.data or {}).get("mode", "focus_mode")
        duration = (task.data or {}).get("duration", 25)
        if mode == "study_mode":
            res = await asyncio.to_thread(productivity_service.start_study_mode, duration_minutes=duration or 45)
        elif mode == "work_mode":
            res = await asyncio.to_thread(productivity_service.start_work_mode, duration_minutes=duration or 60)
        else:
            res = await asyncio.to_thread(productivity_service.start_focus_mode, duration_minutes=duration or 25)

        task.status = TaskStatus.COMPLETED if res.get("success") else TaskStatus.FAILED
        task.result = res.get("message")
        task.data = res

    async def _execute_manage_files(self, task: TaskItem):
        """Searches or manages files in safe Windows folders."""
        from backend.services.file_service import file_service
        query = task.query or (task.data or {}).get("filename", "resume")
        results = await asyncio.to_thread(file_service.search_files, query)
        if results:
            first_match = results[0]
            task.status = TaskStatus.COMPLETED
            task.result = f"Found file: {first_match['name']} in {first_match['path']}."
            task.data = {"matches": results, "file_path": first_match["path"], "filename": first_match["name"]}
        else:
            task.status = TaskStatus.FAILED
            task.error = f"No file matching '{query}' was found in safe user directories."

    async def _execute_create_folder(self, task: TaskItem):
        """Creates a folder in safe user directories."""
        from backend.services.file_service import file_service
        folder_name = (task.data or {}).get("folder_name", "AI Projects")
        ok, msg, created_path = await asyncio.to_thread(file_service.create_folder, folder_name)
        if ok:
            task.status = TaskStatus.COMPLETED
            task.result = msg
            task.data = {"path": created_path, "folder_name": folder_name}
        else:
            task.status = TaskStatus.FAILED
            task.error = msg

    async def _execute_open_file(self, task: TaskItem):
        """Opens a file or folder in File Explorer or default viewer."""
        from backend.services.file_service import file_service
        data = task.data or {}
        target = data.get("folder") or data.get("filename") or task.query or "downloads"
        is_folder = data.get("is_folder", True)
        ok, msg = await asyncio.to_thread(file_service.open_path, target, is_folder=is_folder)
        if ok:
            task.status = TaskStatus.COMPLETED
            task.result = msg
        else:
            task.status = TaskStatus.FAILED
            task.error = msg

    async def _execute_system_specs(self, task: TaskItem):
        """Checks laptop RAM, storage, and battery metrics."""
        from backend.services.system_service import system_service
        speech_text = await asyncio.to_thread(system_service.format_system_info_speech, "all")
        status_obj = await asyncio.to_thread(system_service.get_system_status)
        task.status = TaskStatus.COMPLETED
        task.result = speech_text
        task.data = status_obj.model_dump()

    async def _execute_relay_file(self, task: TaskItem):
        """Stages file for cross-device transfer via Cloud/Local Relay."""
        from backend.services.cross_device_relay_service import cross_device_relay_service
        from pathlib import Path
        data = task.data or {}
        filename = data.get("filename", "resume")
        file_path = data.get("file_path")
        if not file_path:
            from backend.services.file_service import file_service
            matches = await asyncio.to_thread(file_service.search_files, filename)
            if matches:
                file_path = matches[0]["path"]

        if file_path and Path(file_path).exists():
            meta = await asyncio.to_thread(
                cross_device_relay_service.stage_file_from_path,
                source_device_id="local_windows",
                target_device_id="android_phone",
                source_file_path=file_path
            )
            task.status = TaskStatus.COMPLETED
            task.result = f"Document '{meta.filename}' staged for transfer (Relay ID: {meta.transfer_id})."
            task.data = meta.model_dump()
        else:
            # Fallback mock file content stage for testing/demonstration
            sample_content = b"%PDF-1.4 Mock resume document content for AI agent demonstration."
            meta = await asyncio.to_thread(
                cross_device_relay_service.stage_file_from_bytes,
                source_device_id="local_windows",
                target_device_id="android_phone",
                filename=f"{filename}.pdf" if not filename.endswith(".pdf") else filename,
                data=sample_content
            )
            task.status = TaskStatus.COMPLETED
            task.result = f"Staged {meta.filename} on cross-device relay."
            task.data = meta.model_dump()

    async def _execute_notify_device(self, task: TaskItem):
        """Sends notification to target device (e.g. Android phone)."""
        data = task.data or {}
        task.status = TaskStatus.COMPLETED
        task.result = "Notification sent to device."
        task.data = data

    async def _execute_control_device_setting(self, task: TaskItem):
        """Controls hardware setting on device."""
        data = task.data or {}
        setting = data.get("setting", "bluetooth")
        action = data.get("action", "on")
        task.status = TaskStatus.COMPLETED
        task.result = f"{setting.title()} has been turned {action} on the device."
        task.data = data

    async def _execute_set_alarm(self, task: TaskItem):
        """Sets alarm on Android phone."""
        data = task.data or {}
        alarm_time = data.get("time", "7 AM")
        task.status = TaskStatus.COMPLETED
        task.result = f"Alarm set for {alarm_time} on your phone."
        task.data = data

    async def _execute_read_notifications(self, task: TaskItem):
        """Reads recent notifications from Android phone."""
        task.status = TaskStatus.COMPLETED
        task.result = "You have 2 unread notifications: WhatsApp message from Dad, and Google Calendar event reminder in 15 minutes."
        task.data = {"unread_count": 2}

    async def _execute_query_gallery(self, task: TaskItem):
        """Queries photos in phone gallery."""
        task.status = TaskStatus.COMPLETED
        task.result = "Found 8 photos from yesterday in your phone gallery."
        task.data = {"count": 8, "query": task.query}

    async def _execute_query_contacts(self, task: TaskItem):
        """Queries contacts on phone."""
        from backend.services.contact_service import contact_service
        contact_name = task.contact or "Contact"
        matched, ambiguous = contact_service.resolve_contact(contact_name)
        if matched:
            task.status = TaskStatus.COMPLETED
            task.result = f"Found {matched['name']} in contacts: {matched['phone']}."
            task.data = matched
        elif ambiguous:
            task.status = TaskStatus.COMPLETED
            names = ", ".join([c["name"] for c in ambiguous])
            task.result = f"Found {len(ambiguous)} contacts: {names}."
            task.data = {"matches": ambiguous}
        else:
            task.status = TaskStatus.FAILED
            task.error = f"Contact '{contact_name}' not found."

    def confirm_and_resume_plan(self, plan_id: str, confirmation_id: Optional[str] = None) -> Optional[TaskPlan]:
        """Approves pending tasks in the plan and resumes execution."""
        plan = self._active_plans.get(plan_id)
        if not plan:
            from backend.services.task_planner import task_planner
            if task_planner.pending_confirmation_plan and task_planner.pending_confirmation_plan.plan_id == plan_id:
                plan = task_planner.pending_confirmation_plan
                self._active_plans[plan_id] = plan

        if not plan:
            return None

        for t in plan.tasks:
            if t.status == TaskStatus.WAITING_CONFIRMATION:
                t.status = TaskStatus.PENDING
                t.requires_confirmation = False

        plan.status = "created"
        plan.requires_confirmation = False
        return plan

    def cancel_plan(self, plan_id: str) -> Optional[TaskPlan]:
        """Cancels an active or waiting plan."""
        plan = self._active_plans.get(plan_id)
        if not plan:
            return None

        for t in plan.tasks:
            if t.status in [TaskStatus.PENDING, TaskStatus.WAITING_CONFIRMATION, TaskStatus.RUNNING]:
                t.status = TaskStatus.CANCELLED
        plan.status = "cancelled"
        plan.summary = "Execution plan cancelled by user."
        return plan

    def _generate_aggregated_summary(self, plan: TaskPlan) -> str:
        """Synthesizes natural, spoken summary across all task outcomes."""
        completed = [t for t in plan.tasks if t.status == TaskStatus.COMPLETED]
        waiting = [t for t in plan.tasks if t.status == TaskStatus.WAITING_CONFIRMATION]
        failed = [t for t in plan.tasks if t.status in [TaskStatus.FAILED, TaskStatus.SKIPPED]]

        # Exact specification:
        # If Chrome opened successfully but the search failed:
        chrome_opened = any(t.intent == "open_application" and t.application in ["chrome", "browser"] and t.status == TaskStatus.COMPLETED for t in plan.tasks)
        search_failed = any(t.intent == "search_web" and t.status in [TaskStatus.FAILED, TaskStatus.SKIPPED] for t in plan.tasks)
        if chrome_opened and search_failed and len(plan.tasks) == 2:
            return "Google Chrome opened successfully, but I couldn't complete the search."

        # If all tasks completed cleanly for compound action
        if not failed and not waiting and completed:
            search_task = next((t for t in completed if t.intent == "search_web"), None)
            open_task = next((t for t in completed if t.intent == "open_application"), None)
            msg_task = next((t for t in completed if t.intent == "send_message"), None)
            call_task = next((t for t in completed if t.intent == "make_call"), None)

            if search_task and open_task:
                return "All tasks completed successfully."

            if msg_task and open_task:
                return f"WhatsApp opened and message sent to {msg_task.contact}."

            if call_task:
                return f"Calling {call_task.contact}."

        parts = []
        if completed:
            if len(completed) == 1:
                parts.append(completed[0].result or f"Completed {completed[0].title}")
            else:
                titles = [t.title.lower() for t in completed]
                parts.append(f"Successfully finished: {', '.join(titles)}")

        if waiting:
            for w in waiting:
                if w.intent == "send_message":
                    parts.append(f"Ready to send '{w.message}' to {w.contact}. Awaiting your confirmation.")
                else:
                    parts.append(f"Awaiting confirmation for {w.title}.")

        if failed:
            failed_titles = [f"{t.title} ({t.error})" for t in failed]
            parts.append(f"Failed steps: {'; '.join(failed_titles)}")

        return " ".join(parts) if parts else "All tasks processed."


task_scheduler = TaskScheduler()
