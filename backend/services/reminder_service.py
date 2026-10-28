"""
Reminder Service.
Parses natural language times, manages reminders in SQLite database,
and performs background checking for due reminders.
"""

import re
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple

from backend.database.database import SessionLocal
from backend.database.models import Reminder
from backend.services.tts_service import tts_service

logger = logging.getLogger(__name__)


class ReminderService:
    def __init__(self):
        self._running = False
        self._active_listeners = []

    def register_notifier(self, callback):
        self._active_listeners.append(callback)

    def parse_due_time(self, time_str: str) -> datetime:
        """
        Parses time expressions like '8 PM', 'tomorrow at 10 AM', 'in 15 minutes'.
        """
        now = datetime.now()
        clean = time_str.lower().strip()

        # Check 'in X minutes / hours'
        in_match = re.search(r"in\s+(\d+)\s*(mins?|minutes?|hours?|hrs?|seconds?|secs?)", clean)
        if in_match:
            amount = int(in_match.group(1))
            unit = in_match.group(2)
            if "sec" in unit:
                return now + timedelta(seconds=amount)
            elif "min" in unit:
                return now + timedelta(minutes=amount)
            elif "hour" in unit or "hr" in unit:
                return now + timedelta(hours=amount)

        # Check 'tomorrow'
        is_tomorrow = "tomorrow" in clean
        target_day = now + timedelta(days=1) if is_tomorrow else now

        # Match 12-hour or 24-hour time like '8 PM', '8:30 pm', '19:00'
        time_match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", clean)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
            meridiem = time_match.group(3)

            if meridiem:
                if meridiem == "pm" and hour < 12:
                    hour += 12
                elif meridiem == "am" and hour == 12:
                    hour = 0
            
            candidate = target_day.replace(hour=hour, minute=minute, second=0, microsecond=0)
            # If not specified tomorrow, but time already passed today, assume tomorrow
            if not is_tomorrow and candidate <= now:
                candidate += timedelta(days=1)
            return candidate

        # Default fallback: 1 hour from now
        return now + timedelta(hours=1)

    def create_reminder(self, title: str, time_str: str, is_recurring: bool = False, recurrence_pattern: Optional[str] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        db = SessionLocal()
        try:
            due_dt = self.parse_due_time(time_str)
            item = Reminder(
                title=title.strip(),
                due_time=due_dt,
                is_completed=False,
                is_recurring=is_recurring,
                recurrence_pattern=recurrence_pattern
            )
            db.add(item)
            db.commit()
            db.refresh(item)

            friendly_time = due_dt.strftime("%A at %I:%M %p")
            msg = f"Reminder set for {friendly_time}: '{title}'."
            data = {
                "id": item.id,
                "title": item.title,
                "due_time": item.due_time.isoformat(),
                "is_completed": item.is_completed,
                "is_recurring": item.is_recurring,
                "recurrence_pattern": item.recurrence_pattern
            }
            return True, msg, data
        except Exception as e:
            db.rollback()
            return False, f"Failed to create reminder: {str(e)}", None
        finally:
            db.close()

    def get_reminders(self, include_completed: bool = False) -> List[Dict[str, Any]]:
        db = SessionLocal()
        try:
            query = db.query(Reminder)
            if not include_completed:
                query = query.filter(Reminder.is_completed == False)
            items = query.order_by(Reminder.due_time.asc()).all()
            return [
                {
                    "id": i.id,
                    "title": i.title,
                    "due_time": i.due_time.isoformat(),
                    "is_completed": i.is_completed,
                    "is_recurring": i.is_recurring,
                    "recurrence_pattern": i.recurrence_pattern,
                    "created_at": i.created_at.isoformat() if i.created_at else None
                }
                for i in items
            ]
        finally:
            db.close()

    def mark_completed(self, reminder_id: int) -> bool:
        db = SessionLocal()
        try:
            item = db.query(Reminder).filter(Reminder.id == reminder_id).first()
            if item:
                item.is_completed = True
                db.commit()
                return True
            return False
        finally:
            db.close()

    def delete_reminder(self, reminder_id: int) -> bool:
        db = SessionLocal()
        try:
            item = db.query(Reminder).filter(Reminder.id == reminder_id).first()
            if item:
                db.delete(item)
                db.commit()
                return True
            return False
        finally:
            db.close()

    async def run_reminder_loop(self):
        """Background task checking for due reminders every 10 seconds."""
        self._running = True
        logger.info("Reminder background monitor started.")
        while self._running:
            try:
                now = datetime.now()
                db = SessionLocal()
                try:
                    due_items = db.query(Reminder).filter(
                        Reminder.due_time <= now,
                        Reminder.is_completed == False
                    ).all()

                    for r in due_items:
                        r.is_completed = True
                        db.commit()
                        logger.info(f"Fired reminder: {r.title}")
                        
                        alert_text = f"Reminder alert: {r.title}."
                        # Notify listeners (e.g. WebSocket)
                        for notifier in self._active_listeners:
                            try:
                                await notifier({
                                    "type": "reminder_alert",
                                    "id": r.id,
                                    "title": r.title,
                                    "due_time": r.due_time.isoformat()
                                })
                            except Exception:
                                pass

                        # Voice announcement in background
                        asyncio.create_task(tts_service.speak(alert_text))

                        # If recurring daily, create next occurrence
                        if r.is_recurring and r.recurrence_pattern == "daily":
                            next_dt = r.due_time + timedelta(days=1)
                            db.add(Reminder(
                                title=r.title,
                                due_time=next_dt,
                                is_completed=False,
                                is_recurring=True,
                                recurrence_pattern="daily"
                            ))
                            db.commit()

                finally:
                    db.close()
            except Exception as e:
                logger.error(f"Error in reminder loop: {e}")

            await asyncio.sleep(10)


reminder_service = ReminderService()
