"""
Calling Automation Handler for Universal Desktop Automation.
Handles:
- Contact resolution & verification for voice and video calling
- Human-in-the-loop explicit confirmation gating
- Provider dispatch: WhatsApp Call, Microsoft Phone Link (tel:), Teams, Skype
- Verification of call interface execution
- Call termination
"""

from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional, Tuple

from backend.automation.handlers.base_handler import BaseAppHandler
from backend.services.calling_service import calling_service
from backend.services.event_notification_service import event_notification_service

logger = logging.getLogger(__name__)


class CallingHandler(BaseAppHandler):
    def __init__(self):
        super().__init__(
            app_key="calling",
            display_name="Desktop Calling & Telephony",
            supported_actions=["prepare_call", "make_call", "end_call", "list_providers"],
            required_permissions=["make_calls", "access_contacts"],
            timeout_seconds=15.0
        )

    def is_installed(self) -> bool:
        providers = calling_service.get_supported_providers()
        return any(p["is_available"] for p in providers)

    async def execute(self, action: str, params: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        action_clean = action.lower().strip()

        # 1. Prepare Call (Resolves contact & generates confirmation prompt)
        if action_clean in ["prepare_call", "resolve_and_prepare"]:
            target = params.get("contact") or params.get("target") or params.get("recipient") or ""
            provider = params.get("provider", "phone_link")
            call_type = params.get("call_type", "voice")

            await event_notification_service.emit_event(
                event_type="task_started",
                title=f"Resolving contact for call: {target}...",
                message="Status: In Progress",
                status="In Progress",
                metadata={"contact": target, "provider": provider}
            )

            prep = calling_service.prepare_call(target, provider=provider, call_type=call_type)
            if prep["status"] == "ready_for_confirmation":
                await event_notification_service.emit_event(
                    event_type="task_completed",
                    title=f"Ready to call {prep['recipient_name']}",
                    message="Waiting for user confirmation",
                    status="Completed",
                    metadata=prep
                )
                return True, prep["confirmation_prompt"], prep
            elif prep["status"] == "ambiguous_contact":
                await event_notification_service.emit_event(
                    event_type="task_started",
                    title=f"Multiple contacts found for {target}",
                    message="Please select recipient to call",
                    status="In Progress",
                    metadata=prep
                )
                return False, prep["prompt"], prep
            else:
                await event_notification_service.emit_event(
                    event_type="task_failed",
                    title=f"Contact {target} not found for call",
                    message="Recipient does not exist",
                    status="Failed",
                    metadata=prep
                )
                return False, prep["prompt"], prep

        # 2. Make Call (Only executed after user confirmation)
        elif action_clean in ["make_call", "start_call", "dial"]:
            phone = params.get("phone")
            recipient_name = params.get("contact") or params.get("recipient_name") or "Contact"
            provider = params.get("provider", "phone_link")
            call_type = params.get("call_type", "voice")

            if not phone:
                res = calling_service.resolve_recipient(recipient_name)
                if res["status"] != "resolved":
                    return False, res.get("message", "Contact could not be resolved."), res
                phone = res["matched"]["phone"]
                recipient_name = res["matched"]["name"]

            await event_notification_service.emit_event(
                event_type="task_started",
                title=f"Placing call to {recipient_name}...",
                message=f"Provider: {provider}",
                status="In Progress",
                metadata={"contact": recipient_name, "phone": phone, "provider": provider}
            )

            success, msg, data = calling_service.initiate_call(
                phone=phone,
                recipient_name=recipient_name,
                provider=provider,
                call_type=call_type
            )

            if success:
                await event_notification_service.emit_event(
                    event_type="task_completed",
                    title=f"Call initiated with {recipient_name}",
                    message=f"Interface opened via {data.get('provider_name')}",
                    status="Completed",
                    metadata=data
                )
                return True, msg, data
            else:
                await event_notification_service.emit_event(
                    event_type="task_failed",
                    title=f"Could not initiate call to {recipient_name}",
                    message=msg,
                    status="Failed",
                    metadata=data
                )
                return False, msg, data

        # 3. End Call
        elif action_clean in ["end_call", "hang_up", "terminate_call"]:
            await event_notification_service.emit_event(
                event_type="task_started",
                title="Ending active call...",
                message="Status: In Progress",
                status="In Progress"
            )
            success, msg = calling_service.end_call()
            await event_notification_service.emit_event(
                event_type="task_completed" if success else "task_failed",
                title=msg,
                message="Completed" if success else "Failed",
                status="Completed" if success else "Failed"
            )
            return success, msg, {"action": "end_call", "success": success}

        # 4. List Providers
        elif action_clean == "list_providers":
            providers = calling_service.get_supported_providers()
            return True, f"Found {len(providers)} calling integrations.", {"providers": providers}

        return False, f"Unsupported action '{action}' on Calling handler.", {}

    def verify(self, action: str, params: Dict[str, Any], result_data: Dict[str, Any]) -> bool:
        if action in ["make_call", "start_call"]:
            return result_data.get("status") == "Initiated"
        return True
