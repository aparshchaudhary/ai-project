"""
Command Service: Central Orchestrator.
Executes the secure pipeline:
AI / Voice -> Intent Detection -> Validation -> Permission Check -> Predefined Function -> Execution -> TTS & Logging.
"""

import time
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from backend.config.settings import settings
from backend.database.database import SessionLocal
from backend.database.models import CommandHistory
from backend.models.schemas import CommandExecutionResponse, IntentResult
from backend.services.nlp_service import nlp_service
from backend.services.security_service import security_service
from backend.services.automation_service import automation_service
from backend.services.file_service import file_service
from backend.services.system_service import system_service
from backend.services.screenshot_service import screenshot_service
from backend.services.reminder_service import reminder_service
from backend.services.clipboard_service import clipboard_service
from backend.services.weather_service import weather_service
from backend.services.music_service import music_service
from backend.services.tts_service import tts_service

logger = logging.getLogger(__name__)


class CommandService:
    async def process_command(
        self,
        text: str,
        session_id: str = "default",
        is_demo: bool = False,
        confirmed: Optional[bool] = None,
        confirmation_id: Optional[str] = None
    ) -> CommandExecutionResponse:
        start_time = time.time()

        # Handle direct confirmation response if provided
        if confirmation_id:
            return await self.confirm_and_execute(confirmation_id, approved=(confirmed is True), session_id=session_id)

        # 1. Natural Language Intent Parsing & Entity Extraction
        intent_res = nlp_service.parse_intent(text, session_id=session_id)
        
        # 2. Risk Assessment & Permission Check
        risk_level, requires_confirmation, conf_prompt = security_service.assess_risk(intent_res)
        intent_res.risk_level = risk_level
        intent_res.requires_confirmation = requires_confirmation
        if conf_prompt:
            intent_res.confirmation_prompt = conf_prompt

        # If confirmation is required and not yet confirmed, hold execution
        if requires_confirmation:
            c_id = security_service.create_confirmation_request(intent_res)
            prompt_msg = intent_res.confirmation_prompt or f"Please confirm you want to proceed with {intent_res.intent}."
            
            # Log pending confirmation in DB
            history_id = self._log_history(
                command_text=text,
                intent=intent_res.intent,
                entities=intent_res.entities,
                status="pending_confirmation",
                risk_level=risk_level,
                response_text=prompt_msg,
                execution_time_ms=(time.time() - start_time) * 1000
            )

            # Speak prompt
            await tts_service.speak(prompt_msg)

            return CommandExecutionResponse(
                success=True,
                intent=intent_res.intent,
                status="pending_confirmation",
                response_text=prompt_msg,
                entities=intent_res.entities,
                risk_level=risk_level,
                requires_confirmation=True,
                confirmation_id=c_id,
                execution_time_ms=(time.time() - start_time) * 1000,
                history_id=history_id
            )

        # 3. Direct Execution of Predefined Functions
        exec_success, response_msg, extra_data = await self._execute_approved_intent(intent_res, is_demo=is_demo)
        exec_time_ms = (time.time() - start_time) * 1000

        # Update session context
        nlp_service.get_context(session_id).update(
            intent=intent_res.intent,
            entities=intent_res.entities,
            user_text=text,
            response_text=response_msg
        )

        # Log history
        status = "success" if exec_success else "failed"
        history_id = self._log_history(
            command_text=text,
            intent=intent_res.intent,
            entities=intent_res.entities,
            status=status,
            risk_level=risk_level,
            response_text=response_msg,
            execution_time_ms=exec_time_ms
        )

        # 4. Spoken Voice Response
        await tts_service.speak(response_msg)

        return CommandExecutionResponse(
            success=exec_success,
            intent=intent_res.intent,
            status=status,
            response_text=response_msg,
            entities=intent_res.entities,
            risk_level=risk_level,
            requires_confirmation=False,
            execution_time_ms=exec_time_ms,
            history_id=history_id,
            data=extra_data
        )

    async def confirm_and_execute(self, confirmation_id: str, approved: bool, session_id: str = "default") -> CommandExecutionResponse:
        start_time = time.time()
        if not approved:
            security_service.cancel_confirmation(confirmation_id)
            cancel_msg = "Action cancelled."
            await tts_service.speak(cancel_msg)
            return CommandExecutionResponse(
                success=True,
                intent="action_cancelled",
                status="denied",
                response_text=cancel_msg,
                risk_level="high",
                requires_confirmation=False,
                execution_time_ms=(time.time() - start_time) * 1000
            )

        intent_res = security_service.consume_confirmation(confirmation_id)
        if not intent_res:
            err_msg = "Confirmation expired or invalid. Please repeat your command."
            await tts_service.speak(err_msg)
            return CommandExecutionResponse(
                success=False,
                intent="expired",
                status="failed",
                response_text=err_msg,
                risk_level="high",
                requires_confirmation=False,
                execution_time_ms=(time.time() - start_time) * 1000
            )

        exec_success, response_msg, extra_data = await self._execute_approved_intent(intent_res, is_demo=False)
        exec_time_ms = (time.time() - start_time) * 1000

        # Log confirmed execution
        history_id = self._log_history(
            command_text=intent_res.original_text,
            intent=intent_res.intent,
            entities=intent_res.entities,
            status="success" if exec_success else "failed",
            risk_level="high",
            response_text=response_msg,
            execution_time_ms=exec_time_ms
        )

        await tts_service.speak(response_msg)

        return CommandExecutionResponse(
            success=exec_success,
            intent=intent_res.intent,
            status="success" if exec_success else "failed",
            response_text=response_msg,
            entities=intent_res.entities,
            risk_level="high",
            requires_confirmation=False,
            execution_time_ms=exec_time_ms,
            history_id=history_id,
            data=extra_data
        )

    async def _execute_approved_intent(self, intent_res: IntentResult, is_demo: bool = False) -> (bool, str, Optional[Dict[str, Any]]):
        intent = intent_res.intent
        entities = intent_res.entities

        # Demo mode simulation for hazardous actions
        if is_demo and intent in ["shutdown", "restart", "sleep_computer", "delete_file"]:
            return True, f"[Demo Mode] Simulating {intent.replace('_', ' ')}: Task completed safely.", {"demo": True}

        # 1. Applications
        if intent == "open_application":
            app = entities.get("application", "")
            success, msg = automation_service.launch_app(app)
            return success, msg, None

        elif intent == "close_application":
            app = entities.get("application", "")
            success, msg = automation_service.close_app(app)
            return success, msg, None

        # 2. Web Automation
        elif intent == "search_web":
            query = entities.get("query", "")
            engine = entities.get("engine", "google")
            success, msg = automation_service.search_web(query, engine)
            return success, msg, None

        elif intent == "open_website":
            url = entities.get("url", "https://google.com")
            success, msg = automation_service.open_website(url)
            return success, msg, None

        # 3. Screenshot
        elif intent == "take_screenshot":
            success, msg, data = screenshot_service.take_screenshot()
            return success, msg, data

        # 4. Files & Folders
        elif intent == "file_search":
            query = entities.get("query", "")
            ext = entities.get("extension")
            results = file_service.search_files(query, ext)
            if results:
                count = len(results)
                top = results[0]["name"]
                speech = f"Found {count} file{'s' if count > 1 else ''}. The top match is {top}."
                return True, speech, {"files": results}
            else:
                return False, f"No files matching '{query}' were found.", {"files": []}

        elif intent == "create_folder":
            folder_name = entities.get("folder_name", "New Folder")
            parent = entities.get("parent_folder", "Documents")
            success, msg, path = file_service.create_folder(folder_name, parent)
            return success, msg, {"path": path} if path else None

        elif intent == "create_file":
            file_name = entities.get("file_name", "notes.txt")
            parent = entities.get("parent_folder", "Documents")
            success, msg, path = file_service.create_file(file_name, parent_folder=parent)
            return success, msg, {"path": path} if path else None

        elif intent == "open_file":
            target = entities.get("file_path", "")
            is_folder = entities.get("is_folder", False)
            success, msg = file_service.open_path(target, is_folder=is_folder)
            return success, msg, None

        elif intent == "delete_file":
            file_name = entities.get("file_name", "")
            success, msg = file_service.delete_file(file_name)
            return success, msg, None

        # 5. System Controls
        elif intent == "system_information":
            metric = entities.get("metric", "all")
            speech = system_service.format_system_info_speech(metric)
            status = system_service.get_system_status()
            return True, speech, status.model_dump()

        elif intent == "lock_screen":
            success, msg = system_service.lock_screen()
            return success, msg, None

        elif intent == "sleep_computer":
            success, msg = system_service.sleep_computer()
            return success, msg, None

        elif intent == "shutdown":
            success, msg = system_service.shutdown()
            return success, msg, None

        elif intent == "restart":
            success, msg = system_service.restart()
            return success, msg, None

        elif intent == "volume_control":
            action = entities.get("action", "up")
            success, msg = system_service.change_volume(action)
            return success, msg, None

        # 6. Time and Date
        elif intent == "get_time":
            now = datetime.now()
            time_str = now.strftime("%I:%M %p")
            return True, f"The current time is {time_str}.", {"time": time_str}

        elif intent == "get_date":
            now = datetime.now()
            date_str = now.strftime("%A, %B %d, %Y")
            return True, f"Today is {date_str}.", {"date": date_str}

        # 7. Weather
        elif intent == "weather":
            city = entities.get("city", "local")
            success, speech, info = await weather_service.get_weather(city)
            return success, speech, info

        # 8. Reminders
        elif intent == "set_reminder":
            title = entities.get("title", "Important task")
            time_str = entities.get("time_str", "in 1 hour")
            success, msg, data = reminder_service.create_reminder(title, time_str)
            return success, msg, data

        elif intent == "list_reminders":
            items = reminder_service.get_reminders(include_completed=False)
            if items:
                count = len(items)
                first = items[0]["title"]
                speech = f"You have {count} active reminder{'s' if count > 1 else ''}. The next one is: {first}."
                return True, speech, {"reminders": items}
            else:
                return True, "You have no upcoming reminders scheduled.", {"reminders": []}

        # 9. Music Controls
        elif intent == "play_music" or intent == "pause_music":
            success, msg = music_service.play_pause()
            return success, msg, None

        elif intent == "next_track":
            success, msg = music_service.next_track()
            return success, msg, None

        elif intent == "previous_track":
            success, msg = music_service.previous_track()
            return success, msg, None

        # 10. Clipboard
        elif intent == "clipboard_read":
            success, spoken, raw = clipboard_service.read_clipboard()
            return success, spoken, {"content": raw}

        elif intent == "clipboard_write":
            text = entities.get("text", "")
            success, msg = clipboard_service.write_clipboard(text)
            return success, msg, None

        elif intent == "clipboard_clear":
            success, msg = clipboard_service.clear_clipboard()
            return success, msg, None

        # 11. Command History
        elif intent == "show_history":
            db = SessionLocal()
            try:
                recent = db.query(CommandHistory).order_by(CommandHistory.created_at.desc()).limit(3).all()
                if recent:
                    items_str = ", ".join([f"'{r.command_text}'" for r in recent])
                    speech = f"Your latest commands were: {items_str}."
                    return True, speech, None
                return True, "Your command history is currently empty.", None
            finally:
                db.close()

        # 12. Help
        elif intent == "help":
            help_text = (
                "You can say things like: 'Open Chrome', 'Search for Python tutorials', "
                "'Take a screenshot', 'Show CPU usage', 'What's the weather today?', or 'Set a reminder for 8 PM'."
            )
            return True, help_text, None

        # 13. Conversational Response
        elif intent == "conversation":
            resp = intent_res.response_text or "I am listening. How can I help you?"
            return True, resp, None

        return False, f"Command '{intent}' could not be processed.", None

    def _log_history(
        self,
        command_text: str,
        intent: str,
        entities: Dict[str, Any],
        status: str,
        risk_level: str,
        response_text: Optional[str],
        execution_time_ms: float
    ) -> Optional[int]:
        db = SessionLocal()
        try:
            record = CommandHistory(
                command_text=command_text,
                recognized_intent=intent,
                entities_json=json.dumps(entities),
                status=status,
                risk_level=risk_level,
                response_text=response_text,
                execution_time_ms=round(execution_time_ms, 2)
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return record.id
        except Exception as e:
            logger.error(f"Failed to log command history: {e}")
            db.rollback()
            return None
        finally:
            db.close()


command_service = CommandService()
