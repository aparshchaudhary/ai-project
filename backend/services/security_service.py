"""
Security, Permission, and Confirmation Management Service.
Enforces the safety pipeline:
Intent -> Validator -> Permission Check -> Approved Function -> Execution.
Strictly disallows arbitrary shell execution and prevents directory traversal.
"""

import uuid
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from backend.config.settings import settings
from backend.models.schemas import IntentResult
from backend.security.permissions import permission_manager, PermissionScope

logger = logging.getLogger(__name__)


class PendingConfirmation:
    def __init__(self, confirmation_id: str, intent_result: IntentResult, expires_in_seconds: int = 300):
        self.confirmation_id = confirmation_id
        self.intent_result = intent_result
        self.created_at = time.time()
        self.expires_at = self.created_at + expires_in_seconds

    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class SecurityService:
    def __init__(self):
        self._pending_confirmations: Dict[str, PendingConfirmation] = {}

    def assess_risk(self, intent_result: IntentResult) -> Tuple[str, bool, Optional[str]]:
        """
        Determines risk level and whether confirmation is required.
        Checks persistent permissions in private DPAPI store to avoid repeated nagging prompts.
        Returns: (risk_level, requires_confirmation, confirmation_prompt)
        """
        intent = intent_result.intent
        entities = intent_result.entities

        # 1. High-risk operations (Always require confirmation unless explicitly disabled by admin)
        if intent in ["delete_file", "shutdown", "restart", "sleep_computer"]:
            prompt = intent_result.confirmation_prompt
            if not prompt:
                if intent == "delete_file":
                    fname = entities.get("file_name", "the selected file")
                    prompt = f"Are you sure you want to permanently delete '{fname}'?"
                elif intent == "shutdown":
                    prompt = "Are you sure you want to shut down your computer?"
                elif intent == "restart":
                    prompt = "Are you sure you want to restart your computer?"
                elif intent == "sleep_computer":
                    prompt = "Do you want to put your computer to sleep?"

            permission_manager.audit_log("SECURITY_CHECK_HIGH_RISK", intent, True, {"prompt": prompt})
            return "high", settings.require_confirmation_high_risk, prompt

        # 2. Application Launch - check persistent permission store
        if intent == "open_application":
            app_target = entities.get("application", "").lower().strip()
            # If user already granted permission, no confirmation prompt
            if permission_manager.is_permission_granted(PermissionScope.APP_LAUNCH, app_target):
                return "low", False, None

            # Standard approved desktop applications are automatically authorized persistently
            standard_safe_apps = [
                "chrome", "google chrome", "browser", "msedge", "edge", "firefox",
                "code", "vs code", "vscode", "notepad", "calculator", "calc",
                "explorer", "file explorer", "whatsapp", "whats app", "wa", "whatsapp desktop",
                "spotify", "discord", "taskmgr", "task manager", "settings"
            ]
            if any(s == app_target or s in app_target for s in standard_safe_apps):
                permission_manager.grant_permission(PermissionScope.APP_LAUNCH, app_target, duration_days=30)
                return "low", False, None

            # If it's an arbitrary unknown app and medium-risk confirmation is on
            if settings.require_confirmation_med_risk:
                return "medium", True, f"Do you grant permission to launch '{app_target}'?"
            return "low", False, None

        # 3. Medium-risk file system operations
        if intent in ["create_folder", "create_file", "rename_file", "move_file", "clipboard_clear"]:
            if settings.require_confirmation_med_risk and intent in ["rename_file", "move_file", "clipboard_clear"]:
                return "medium", True, f"Please confirm you want to proceed with {intent.replace('_', ' ')}."
            return "medium", False, None

        # 4. Low-risk operations (Execute automatically)
        return "low", False, None

    def create_confirmation_request(self, intent_result: IntentResult) -> str:
        confirmation_id = str(uuid.uuid4())
        self._clean_expired()
        self._pending_confirmations[confirmation_id] = PendingConfirmation(
            confirmation_id=confirmation_id,
            intent_result=intent_result
        )
        return confirmation_id

    def get_pending_confirmation(self, confirmation_id: str) -> Optional[PendingConfirmation]:
        self._clean_expired()
        return self._pending_confirmations.get(confirmation_id)

    def consume_confirmation(self, confirmation_id: str) -> Optional[IntentResult]:
        """
        Retrieves and removes approved action for execution, persisting approved scope.
        """
        self._clean_expired()
        pending = self._pending_confirmations.pop(confirmation_id, None)
        if pending and not pending.is_expired():
            # If this was an app launch or scoped action, persist permission to prevent repeating prompts
            intent = pending.intent_result.intent
            entities = pending.intent_result.entities
            if intent == "open_application":
                app_target = entities.get("application", "").lower().strip()
                permission_manager.grant_permission(PermissionScope.APP_LAUNCH, app_target)

            return pending.intent_result
        return None

    def cancel_confirmation(self, confirmation_id: str):
        self._pending_confirmations.pop(confirmation_id, None)

    def _clean_expired(self):
        now = time.time()
        expired = [cid for cid, p in self._pending_confirmations.items() if p.expires_at < now]
        for cid in expired:
            self._pending_confirmations.pop(cid, None)

    def is_safe_path(self, target_path: Path) -> bool:
        """
        Validates path safety against sandbox allowlist, preventing path traversal,
        symlink escapes, and Windows system directory tampering.
        """
        authorized, reason = permission_manager.is_path_authorized(target_path)
        if not authorized:
            logger.warning(f"Path safety violation: {target_path} - {reason}")
            permission_manager.audit_log("PATH_SECURITY_VIOLATION", "file_boundary", False, {
                "target": str(target_path),
                "reason": reason
            })
            return False
        return True


security_service = SecurityService()

