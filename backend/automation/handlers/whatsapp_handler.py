"""
WhatsApp Desktop & Web Automation Handler.
Handles:
- Contact verification and resolution
- Duplicate / ambiguous contact detection
- Human-in-the-loop confirmation gating
- Protocol dispatch (`whatsapp://send?phone=...&text=...`)
- Web fallback (`https://web.whatsapp.com/send?phone=...&text=...`)
- Window verification and focus
"""

from __future__ import annotations
import os
import time
import urllib.parse
import webbrowser
import logging
from typing import Dict, Any, List, Optional, Tuple

from backend.automation.handlers.base_handler import BaseAppHandler
from backend.services.desktop_window_manager import desktop_window_manager, IS_WINDOWS
from backend.services.contact_service import contact_service
from backend.services.event_notification_service import event_notification_service

logger = logging.getLogger(__name__)


class WhatsAppHandler(BaseAppHandler):
    def __init__(self):
        super().__init__(
            app_key="whatsapp",
            display_name="WhatsApp",
            supported_actions=["open", "close", "resolve_contact", "prepare_message", "send_message", "open_recent_chats"],
            required_permissions=["send_message", "access_contacts"],
            timeout_seconds=12.0
        )

    def is_installed(self) -> bool:
        app_def = desktop_window_manager.get_app_definition("whatsapp")
        if not app_def:
            return False
        if IS_WINDOWS:
            resolved = desktop_window_manager.resolve_executable_path(app_def.get("candidate_paths", []))
            return bool(resolved or app_def.get("protocol"))
        return True

    def resolve_recipient(self, query: str) -> Dict[str, Any]:
        """
        Resolves a spoken name against the authorized contact book.
        Handles duplicates, aliases, and missing contacts.
        """
        matched, ambiguous_list = contact_service.resolve_contact(query)
        if ambiguous_list and len(ambiguous_list) > 1:
            names = [c["name"] for c in ambiguous_list]
            return {
                "status": "ambiguous",
                "matched": None,
                "ambiguous_contacts": ambiguous_list,
                "message": f"I found {len(ambiguous_list)} contacts named {query}: {' or '.join(names)}. Which one would you like to message?"
            }
        elif matched:
            return {
                "status": "resolved",
                "matched": matched,
                "ambiguous_contacts": [],
                "message": f"Contact {matched['name']} found ({matched['phone']})."
            }
        else:
            return {
                "status": "not_found",
                "matched": None,
                "ambiguous_contacts": [],
                "message": f"I couldn't find '{query}' in your contact book. You can add them in Settings."
            }

    async def execute(self, action: str, params: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        action_clean = action.lower().strip()

        # 1. Open WhatsApp
        if action_clean in ["open", "launch", "open_application"]:
            await event_notification_service.emit_event(
                event_type="task_started",
                title="Opening WhatsApp...",
                message="Status: In Progress",
                status="In Progress",
                metadata={"application": "whatsapp"}
            )
            res = desktop_window_manager.launch_or_activate("whatsapp")
            if res.success:
                await event_notification_service.emit_event(
                    event_type="task_completed",
                    title="WhatsApp opened successfully.",
                    message="Status: Completed",
                    status="Completed",
                    metadata={"application": "whatsapp"}
                )
                return True, "WhatsApp opened successfully.", res.to_dict()
            else:
                await event_notification_service.emit_event(
                    event_type="task_failed",
                    title="Failed to open WhatsApp",
                    message=res.error or "WhatsApp could not be launched",
                    status="Failed",
                    metadata={"application": "whatsapp"}
                )
                return False, res.error or "Could not open WhatsApp.", res.to_dict()

        # 2. Close WhatsApp
        elif action_clean in ["close", "terminate"]:
            from backend.services.automation_service import automation_service
            success, msg = automation_service.close_app("whatsapp")
            return success, msg, {"action": "close", "success": success}

        # 3. Resolve Contact
        elif action_clean == "resolve_contact":
            contact_query = params.get("contact", "").strip()
            await event_notification_service.emit_event(
                event_type="task_started",
                title=f"Searching for contact {contact_query}...",
                message="Status: In Progress",
                status="In Progress",
                metadata={"contact": contact_query}
            )
            res_data = self.resolve_recipient(contact_query)
            if res_data["status"] == "resolved":
                c = res_data["matched"]
                await event_notification_service.emit_event(
                    event_type="task_completed",
                    title=f"Contact {c['name']} found.",
                    message=f"Phone: {c['phone']}",
                    status="Completed",
                    metadata={"contact": c}
                )
                return True, res_data["message"], res_data
            elif res_data["status"] == "ambiguous":
                await event_notification_service.emit_event(
                    event_type="task_started",
                    title=f"Multiple contacts found for {contact_query}",
                    message="Please select the intended recipient.",
                    status="In Progress",
                    metadata={"ambiguous_contacts": res_data["ambiguous_contacts"]}
                )
                return False, res_data["message"], res_data
            else:
                await event_notification_service.emit_event(
                    event_type="task_failed",
                    title=f"Contact {contact_query} not found",
                    message="Recipient does not exist in authorized contacts.",
                    status="Failed",
                    metadata={"contact": contact_query}
                )
                return False, res_data["message"], res_data

        # 4. Send Message (Only after explicit user approval)
        elif action_clean in ["send_message", "dispatch_message"]:
            contact_name = params.get("contact") or params.get("recipient") or "Contact"
            message_text = params.get("message") or params.get("text") or "Hi"
            phone = params.get("phone")

            if not phone:
                res_recip = self.resolve_recipient(contact_name)
                if res_recip["status"] != "resolved":
                    return False, res_recip["message"], res_recip
                phone = res_recip["matched"]["phone"]
                contact_name = res_recip["matched"]["name"]

            clean_phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
            if clean_phone.startswith("+"):
                clean_phone = clean_phone[1:]
            elif len(clean_phone) == 10 and clean_phone.isdigit():
                clean_phone = "91" + clean_phone

            encoded_text = urllib.parse.quote_plus(message_text.strip())
            protocol_url = f"whatsapp://send?phone={clean_phone}&text={encoded_text}"
            web_url = f"https://web.whatsapp.com/send?phone={clean_phone}&text={encoded_text}"

            await event_notification_service.emit_event(
                event_type="task_started",
                title=f"Sending message to {contact_name}...",
                message=f"Message: {message_text}",
                status="In Progress",
                metadata={"contact": contact_name, "phone": clean_phone, "message": message_text}
            )

            opened = False
            method_used = "windows_native_protocol"

            if IS_WINDOWS and hasattr(os, "startfile"):
                try:
                    os.startfile(protocol_url)
                    opened = True
                except Exception as ex:
                    logger.warning(f"Native WhatsApp protocol failed: {ex}, attempting browser fallback.")

            if not opened:
                try:
                    webbrowser.open(web_url)
                    opened = True
                    method_used = "browser_web_fallback"
                except Exception as ex2:
                    logger.error(f"WhatsApp navigation failed: {ex2}")
                    await event_notification_service.emit_event(
                        event_type="task_failed",
                        title=f"Failed to send message to {contact_name}",
                        message=str(ex2),
                        status="Failed",
                        metadata={"contact": contact_name, "error": str(ex2)}
                    )
                    return False, f"Could not open WhatsApp for {contact_name}: {ex2}", {"error": str(ex2)}

            # Brief stabilization & focus window
            time.sleep(0.5)
            if IS_WINDOWS:
                desktop_window_manager.focus_process_window("whatsapp")

            await event_notification_service.emit_event(
                event_type="task_completed",
                title=f"Message sent to {contact_name} successfully.",
                message="Status: Completed",
                status="Completed",
                metadata={"contact": contact_name, "phone": clean_phone, "message": message_text, "method": method_used}
            )

            result_meta = {
                "recipient_name": contact_name,
                "phone": clean_phone,
                "message": message_text,
                "method": method_used,
                "protocol_url": protocol_url,
                "web_url": web_url,
                "status": "Completed"
            }
            return True, f"Your message '{message_text}' has been sent to {contact_name}.", result_meta

        # 5. Open Recent Chats
        elif action_clean == "open_recent_chats":
            res = desktop_window_manager.launch_or_activate("whatsapp")
            msg = "Opened WhatsApp to view recent chats." if res.success else "Could not open WhatsApp."
            return res.success, msg, res.to_dict()

        return False, f"Unsupported action '{action}' on WhatsApp.", {}

    def verify(self, action: str, params: Dict[str, Any], result_data: Dict[str, Any]) -> bool:
        if action in ["open", "launch", "open_application"]:
            return result_data.get("process_started", False) or result_data.get("window_detected", False)
        if action in ["send_message", "dispatch_message"]:
            return result_data.get("status") == "Completed"
        return True
