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
            if task.intent == "open_application":
                await self._execute_open_app(task)
            elif task.intent == "search_web":
                await self._execute_search_web(task)
            elif task.intent == "send_message":
                await self._execute_send_message(task)
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

    def confirm_and_resume_plan(self, plan_id: str, confirmation_id: Optional[str] = None) -> Optional[TaskPlan]:
        """Approves pending tasks in the plan and resumes execution."""
        plan = self._active_plans.get(plan_id)
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
            if any(t.intent == "search_web" for t in completed) and any(t.intent == "open_application" for t in completed):
                return "All tasks completed successfully."

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
