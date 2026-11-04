"""
WhatsApp Desktop & Web Message Automation Service.
Handles:
- Contact verification and resolution
- Ambiguity detection
- Explicit security confirmation before dispatching messages
- Windows WhatsApp protocol (`whatsapp:send?phone=...&text=...`)
- Web fallback (`https://web.whatsapp.com/send?phone=...&text=...`)
- Recent chats navigation
"""

from __future__ import annotations
import os
import urllib.parse
import webbrowser
import logging
from typing import Dict, Any, Optional, Tuple, List

from backend.services.contact_service import contact_service
from backend.services.desktop_window_manager import desktop_window_manager, IS_WINDOWS

logger = logging.getLogger(__name__)


class WhatsAppService:
    def __init__(self):
        pass

    def prepare_message(self, contact_query: str, message: str) -> Dict[str, Any]:
        """
        Validates contact and prepares the message sending operation.
        Returns metadata including confirmation prompt and ambiguity flags.
        """
        matched_contact, ambiguous_matches = contact_service.resolve_contact(contact_query)

        if ambiguous_matches and len(ambiguous_matches) > 1:
            # Multiple contacts matched! Ask user to clarify.
            names = [c["name"] for c in ambiguous_matches]
            names_str = " or ".join(names)
            return {
                "success": False,
                "status": "ambiguous_contact",
                "ambiguous": True,
                "contacts": ambiguous_matches,
                "prompt": f"I found {len(ambiguous_matches)} contacts named {contact_query}: {names_str}. Which one would you like to message?",
                "message": message
            }

        if not matched_contact:
            # No contact found
            return {
                "success": False,
                "status": "contact_not_found",
                "ambiguous": False,
                "contacts": [],
                "prompt": f"I couldn't find '{contact_query}' in your contact book. You can add them in Settings.",
                "message": message
            }

        # Exact contact found! Prepare for confirmation
        recipient_name = matched_contact["name"]
        phone = matched_contact["phone"]
        conf_prompt = f"You want to send '{message}' to {recipient_name} ({phone}). Shall I send it?"

        return {
            "success": True,
            "status": "ready_for_confirmation",
            "ambiguous": False,
            "contact": matched_contact,
            "recipient_name": recipient_name,
            "phone": phone,
            "message": message,
            "confirmation_prompt": conf_prompt
        }

    def dispatch_message(self, phone: str, message: str, recipient_name: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Dispatches the message via Windows native WhatsApp protocol or browser URL.
        Only executed AFTER user confirmation has been approved.
        """
        # Clean phone number (remove spaces, hyphens, ensure country code)
        clean_phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if clean_phone.startswith("+"):
            clean_phone = clean_phone[1:]
        elif len(clean_phone) == 10 and clean_phone.isdigit():
            clean_phone = "91" + clean_phone  # default to +91 if 10-digit Indian number

        encoded_text = urllib.parse.quote_plus(message.strip())
        protocol_url = f"whatsapp://send?phone={clean_phone}&text={encoded_text}"
        web_url = f"https://web.whatsapp.com/send?phone={clean_phone}&text={encoded_text}"

        logger.info(f"Dispatching confirmed message to {recipient_name} ({clean_phone})")

        opened = False
        method_used = "protocol"

        # 1. On Windows with native WhatsApp installed, launch via protocol
        if IS_WINDOWS and hasattr(os, "startfile"):
            try:
                os.startfile(protocol_url)
                opened = True
                method_used = "windows_native_protocol"
            except Exception as e:
                logger.warning(f"Native WhatsApp protocol failed, trying browser: {e}")

        # 2. Web browser fallback or non-Windows platform
        if not opened:
            try:
                webbrowser.open(web_url)
                opened = True
                method_used = "browser_web_fallback"
            except Exception as e2:
                logger.error(f"Could not open WhatsApp: {e2}")
                return False, f"Could not dispatch message to {recipient_name}: {e2}", {}

        confirmation_text = f"Your message '{message}' has been sent to {recipient_name}."
        meta = {
            "recipient_name": recipient_name,
            "phone": phone,
            "message": message,
            "method": method_used,
            "protocol_url": protocol_url,
            "web_url": web_url,
            "status": "Sent"
        }

        return True, confirmation_text, meta

    def open_recent_chats(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Navigates to WhatsApp and opens recent chats."""
        res = desktop_window_manager.launch_or_activate("whatsapp")
        msg = "Opened WhatsApp to view your recent chats." if res.success else "Could not open WhatsApp."
        return res.success, msg, res.to_dict()


whatsapp_service = WhatsAppService()
