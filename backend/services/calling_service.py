"""
Calling Service & Telephony Integration Manager.
Supports:
- Contact resolution for voice/video calling
- Multi-provider support:
  1. WhatsApp Desktop Call (`whatsapp://call?phone=...`)
  2. Microsoft Phone Link / Windows Telephony (`tel:...`)
  3. Microsoft Teams (`msteams:/l/call/...`)
  4. Skype (`skype:...`)
- Strict security confirmation gating before placing any call
- Truthful status reporting (verifies call interface opened; does not pretend call was answered)
- Active call termination where permitted
"""

from __future__ import annotations
import os
import re
import urllib.parse
import webbrowser
import logging
from typing import Dict, Any, Optional, Tuple, List

from backend.services.contact_service import contact_service
from backend.services.desktop_window_manager import desktop_window_manager, IS_WINDOWS

logger = logging.getLogger(__name__)

CALLING_PROVIDERS = {
    "whatsapp": {
        "name": "WhatsApp",
        "protocol_template": "whatsapp://call?phone={phone}",
        "web_fallback": "https://web.whatsapp.com/send?phone={phone}",
        "process_names": ["WhatsApp.exe", "WhatsAppDesktop.exe"],
    },
    "phone_link": {
        "name": "Microsoft Phone Link",
        "protocol_template": "tel:{phone}",
        "process_names": ["PhoneExperienceHost.exe", "YourPhone.exe"],
    },
    "teams": {
        "name": "Microsoft Teams",
        "protocol_template": "msteams:/l/call/0/0?users={target}",
        "process_names": ["Teams.exe", "ms-teams.exe"],
    },
    "skype": {
        "name": "Skype",
        "protocol_template": "skype:{phone}?call",
        "process_names": ["Skype.exe"],
    }
}


class CallingService:
    def __init__(self):
        self._active_call_session: Optional[Dict[str, Any]] = None

    def resolve_recipient(self, query: str) -> Dict[str, Any]:
        """
        Resolves target contact or raw phone number.
        """
        clean_query = query.strip()
        # Direct phone number check
        digits_only = re.sub(r"[^\d+]", "", clean_query)
        if len(digits_only) >= 7 and any(c.isdigit() for c in clean_query):
            return {
                "status": "resolved",
                "matched": {
                    "name": clean_query,
                    "phone": digits_only,
                    "relationship": "Direct Number"
                },
                "ambiguous_contacts": []
            }

        matched, ambiguous = contact_service.resolve_contact(clean_query)
        if ambiguous and len(ambiguous) > 1:
            return {
                "status": "ambiguous",
                "matched": None,
                "ambiguous_contacts": ambiguous,
                "message": f"Multiple contacts found for '{clean_query}'. Please select the recipient to call."
            }
        elif matched:
            return {
                "status": "resolved",
                "matched": matched,
                "ambiguous_contacts": []
            }
        else:
            return {
                "status": "not_found",
                "matched": None,
                "ambiguous_contacts": [],
                "message": f"Could not find '{clean_query}' in your contact book. You can add them in Settings or provide a phone number."
            }

    def prepare_call(
        self,
        target_query: str,
        provider: str = "phone_link",
        call_type: str = "voice"
    ) -> Dict[str, Any]:
        """
        Validates target recipient and prepares call plan requiring confirmation.
        """
        recip_data = self.resolve_recipient(target_query)
        if recip_data["status"] == "ambiguous":
            names = [c["name"] for c in recip_data["ambiguous_contacts"]]
            return {
                "success": False,
                "status": "ambiguous_contact",
                "ambiguous": True,
                "contacts": recip_data["ambiguous_contacts"],
                "prompt": f"I found {len(names)} contacts named {target_query}: {' or '.join(names)}. Which one would you like to call?",
                "recipient": target_query
            }

        if recip_data["status"] == "not_found":
            return {
                "success": False,
                "status": "contact_not_found",
                "ambiguous": False,
                "contacts": [],
                "prompt": recip_data["message"],
                "recipient": target_query
            }

        contact = recip_data["matched"]
        chosen_provider = provider.lower() if provider.lower() in CALLING_PROVIDERS else "phone_link"
        provider_name = CALLING_PROVIDERS[chosen_provider]["name"]

        prompt = (
            f"Please confirm you want to place a {call_type} call to "
            f"{contact['name']} ({contact['phone']}) using {provider_name}."
        )

        return {
            "success": True,
            "status": "ready_for_confirmation",
            "ambiguous": False,
            "contact": contact,
            "recipient_name": contact["name"],
            "phone": contact["phone"],
            "provider": chosen_provider,
            "provider_name": provider_name,
            "call_type": call_type,
            "confirmation_prompt": prompt
        }

    def initiate_call(
        self,
        phone: str,
        recipient_name: str,
        provider: str = "phone_link",
        call_type: str = "voice"
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Initiates outgoing call via supported Windows telephony / messaging integration.
        ONLY executed after explicit user confirmation has been approved.
        """
        clean_phone = re.sub(r"[^\d+]", "", phone)
        if clean_phone.startswith("+"):
            formatted_phone = clean_phone
        elif len(clean_phone) == 10:
            formatted_phone = "+91" + clean_phone
        else:
            formatted_phone = clean_phone

        chosen_provider = provider.lower() if provider.lower() in CALLING_PROVIDERS else "phone_link"
        prov_info = CALLING_PROVIDERS[chosen_provider]

        # Construct target protocol URI
        if chosen_provider == "teams":
            target_uri = prov_info["protocol_template"].format(target=formatted_phone)
        elif chosen_provider == "whatsapp":
            target_clean = formatted_phone.replace("+", "")
            target_uri = prov_info["protocol_template"].format(phone=target_clean)
        else:
            target_uri = prov_info["protocol_template"].format(phone=formatted_phone)

        logger.info(f"Initiating call to {recipient_name} ({formatted_phone}) via {prov_info['name']}: {target_uri}")

        opened = False
        method_used = "native_protocol"
        error_msg = None

        if IS_WINDOWS and hasattr(os, "startfile"):
            try:
                os.startfile(target_uri)
                opened = True
            except Exception as e:
                logger.warning(f"Protocol launch failed for {target_uri}: {e}")
                error_msg = str(e)

        # Fallback to general tel: or browser web fallback if WhatsApp
        if not opened and chosen_provider == "whatsapp":
            target_clean = formatted_phone.replace("+", "")
            web_fallback = f"https://web.whatsapp.com/send?phone={target_clean}"
            try:
                webbrowser.open(web_fallback)
                opened = True
                method_used = "browser_web_fallback"
            except Exception as e2:
                error_msg = str(e2)

        if not opened and chosen_provider != "phone_link":
            # Attempt Phone Link / tel: fallback
            try:
                tel_uri = f"tel:{formatted_phone}"
                if hasattr(os, "startfile"):
                    os.startfile(tel_uri)
                    opened = True
                    method_used = "phone_link_fallback"
            except Exception as e3:
                error_msg = str(e3)

        if not opened:
            msg = (
                f"Could not open calling interface for {recipient_name}. "
                f"Please ensure {prov_info['name']} or Microsoft Phone Link is configured on your laptop."
            )
            return False, msg, {"error": error_msg, "provider": chosen_provider}

        self._active_call_session = {
            "recipient_name": recipient_name,
            "phone": formatted_phone,
            "provider": chosen_provider,
            "provider_name": prov_info["name"],
            "call_type": call_type,
            "method": method_used,
            "uri": target_uri,
            "status": "Initiated"
        }

        # Accurate status: call interface opened (never claim answer without carrier verification)
        speech_confirmation = (
            f"Calling {recipient_name} via {prov_info['name']}. "
            f"The calling interface has been opened on your desktop."
        )

        return True, speech_confirmation, self._active_call_session

    def end_call(self) -> Tuple[bool, str]:
        """
        Closes active call interface or terminates telephony process if supported.
        """
        if not self._active_call_session:
            return False, "No active call session found to end."

        session = self._active_call_session
        prov_key = session.get("provider", "phone_link")
        prov_info = CALLING_PROVIDERS.get(prov_key, {})
        proc_names = prov_info.get("process_names", [])

        from backend.services.automation_service import automation_service
        closed = False
        for p in proc_names:
            success, _ = automation_service.close_app(p)
            if success:
                closed = True

        self._active_call_session = None
        if closed:
            return True, f"Call interface with {session.get('recipient_name', 'contact')} closed."
        return True, f"Ended call session with {session.get('recipient_name', 'contact')}."

    def get_supported_providers(self) -> List[Dict[str, Any]]:
        """Returns diagnostic and capability info for available calling integrations."""
        results = []
        for key, info in CALLING_PROVIDERS.items():
            installed = False
            if key == "whatsapp":
                app_def = desktop_window_manager.get_app_definition("whatsapp")
                installed = bool(app_def)
            elif key == "teams":
                app_def = desktop_window_manager.get_app_definition("teams")
                installed = bool(app_def)
            elif key == "phone_link":
                # Built into Windows 10 & 11
                installed = IS_WINDOWS
            elif key == "skype":
                installed = bool(desktop_window_manager.get_app_definition("skype"))

            results.append({
                "provider_id": key,
                "name": info["name"],
                "protocol": info["protocol_template"],
                "is_available": installed,
                "call_types": ["voice", "video"] if key in ["whatsapp", "teams", "skype"] else ["voice"]
            })
        return results


calling_service = CallingService()
