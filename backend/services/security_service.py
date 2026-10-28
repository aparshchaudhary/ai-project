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
        Returns: (risk_level, requires_confirmation, confirmation_prompt)
        """
        intent = intent_result.intent

        # High-risk operations (Always require confirmation unless explicitly disabled by admin)
        if intent in ["delete_file", "shutdown", "restart", "sleep_computer"]:
            prompt = intent_result.confirmation_prompt
            if not prompt:
                if intent == "delete_file":
                    fname = intent_result.entities.get("file_name", "the selected file")
                    prompt = f"Are you sure you want to permanently delete '{fname}'?"
                elif intent == "shutdown":
                    prompt = "Are you sure you want to shut down your computer?"
                elif intent == "restart":
                    prompt = "Are you sure you want to restart your computer?"
                elif intent == "sleep_computer":
                    prompt = "Do you want to put your computer to sleep?"

            return "high", settings.require_confirmation_high_risk, prompt

        # Medium-risk operations
        if intent in ["create_folder", "create_file", "rename_file", "move_file", "clipboard_clear"]:
            if settings.require_confirmation_med_risk and intent in ["rename_file", "move_file", "clipboard_clear"]:
                return "medium", True, f"Please confirm you want to proceed with {intent.replace('_', ' ')}."
            return "medium", False, None

        # Low-risk operations (Execute automatically)
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
        Retrieves and removes approved action for execution.
        """
        self._clean_expired()
        pending = self._pending_confirmations.pop(confirmation_id, None)
        if pending and not pending.is_expired():
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
        Validates that a path is within the allowed user directories
        and not inside system critical directories (Windows, Program Files, system32).
        """
        try:
            resolved = target_path.resolve()
            # Forbid sensitive paths
            forbidden_roots = [
                Path("C:/Windows").resolve(),
                Path("C:/Program Files").resolve(),
                Path("C:/Program Files (x86)").resolve(),
            ]
            for f in forbidden_roots:
                if f in resolved.parents or resolved == f:
                    logger.warning(f"Access denied to system directory: {resolved}")
                    return False

            # Check if within user home or safe directories
            for safe_dir in settings.safe_dirs:
                try:
                    safe_res = safe_dir.resolve()
                    if safe_res in resolved.parents or resolved == safe_res:
                        return True
                except Exception:
                    continue

            # Also allow anything directly under user home directory
            user_home = Path.home().resolve()
            if user_home in resolved.parents:
                return True

            return False
        except Exception as e:
            logger.error(f"Error checking path safety: {e}")
            return False


security_service = SecurityService()
