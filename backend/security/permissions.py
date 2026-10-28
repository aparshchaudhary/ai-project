"""
Security Boundary, Sandboxing, and Persistent Permission Management.
Enforces real boundaries:
- Bounded file-system traversal checks (resolves symlinks and junctions).
- Persistent permission registry for approved applications (e.g. WhatsApp, Chrome) to stop repeated nagging prompts.
- Audit logging with automated credential redaction.
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta

from backend.security.credential_store import private_config, redact_secrets

logger = logging.getLogger(__name__)

# Sensitive system locations explicitly forbidden
FORBIDDEN_ROOTS = [
    Path("C:/Windows").resolve(),
    Path("C:/Program Files").resolve(),
    Path("C:/Program Files (x86)").resolve(),
    Path("C:/Recovery").resolve(),
    Path(os.environ.get("SystemRoot", "C:/Windows")).resolve(),
]


class PermissionScope:
    APP_LAUNCH = "app_launch"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    CLIPBOARD_ACCESS = "clipboard_access"
    SYSTEM_CONTROL = "system_control"
    SCREENSHOT = "screenshot"


class PermissionManager:
    def __init__(self):
        self._audit_logs: List[Dict[str, Any]] = []

    def get_granted_permissions(self) -> Dict[str, Dict[str, Any]]:
        perms = private_config.get("security", "persistent_permissions", {})
        # Filter expired
        now = time.time()
        active = {}
        for key, info in perms.items():
            if info.get("expires_at", 0) > now:
                active[key] = info
        return active

    def is_permission_granted(self, scope: str, target: str = "*") -> bool:
        key = f"{scope}:{target.lower().strip()}"
        active = self.get_granted_permissions()
        if key in active:
            return True
        # Check wildcard target grant
        wildcard_key = f"{scope}:*"
        return wildcard_key in active

    def grant_permission(self, scope: str, target: str = "*", duration_days: int = 30) -> Dict[str, Any]:
        key = f"{scope}:{target.lower().strip()}"
        expires_at = time.time() + (duration_days * 86400)
        perms = private_config.get("security", "persistent_permissions", {})
        record = {
            "scope": scope,
            "target": target,
            "granted_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires_at,
            "duration_days": duration_days
        }
        perms[key] = record
        private_config.set("security", "persistent_permissions", perms)
        self.audit_log("PERMISSION_GRANTED", scope, True, {"target": target, "duration_days": duration_days})
        return record

    def revoke_permission(self, scope: str, target: str = "*"):
        key = f"{scope}:{target.lower().strip()}"
        perms = private_config.get("security", "persistent_permissions", {})
        if key in perms:
            del perms[key]
            private_config.set("security", "persistent_permissions", perms)
            self.audit_log("PERMISSION_REVOKED", scope, True, {"target": target})

    def revoke_all(self):
        private_config.set("security", "persistent_permissions", {})
        self.audit_log("PERMISSION_REVOKE_ALL", "all", True, {})

    def is_path_authorized(self, target_path: Path) -> Tuple[bool, str]:
        """
        Validates that a path is strictly inside the user's authorized directory allowlist.
        Protects against directory traversal (..), absolute escapes, symlink traversal,
        and system directory interference.
        """
        try:
            resolved = target_path.resolve()

            # 1. Strictly forbid system directories
            for forb in FORBIDDEN_ROOTS:
                if forb in resolved.parents or resolved == forb:
                    return False, f"Access denied: Path '{resolved.name}' is within protected system directory."

            # 2. Check against authorized allowlist from private configuration
            authorized_dirs = private_config.get_authorized_dirs()
            for auth_dir in authorized_dirs:
                try:
                    auth_resolved = auth_dir.resolve()
                    if auth_resolved in resolved.parents or auth_resolved == resolved:
                        return True, "Authorized"
                except Exception:
                    continue

            # 3. Check App Scratch / Data directory
            from backend.config.settings import settings
            safe_extra = [settings.data_dir.resolve(), settings.screenshots_dir.resolve()]
            for s in safe_extra:
                if s in resolved.parents or s == resolved:
                    return True, "Authorized"

            return False, f"Access denied: '{resolved}' is outside authorized directory allowlist."
        except Exception as e:
            return False, f"Path validation error: {str(e)}"

    def audit_log(self, action: str, scope: str, success: bool, details: Dict[str, Any]):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "scope": scope,
            "success": success,
            "details": details
        }
        # Redact any sensitive info from details string
        clean_entry = json.loads(redact_secrets(json.dumps(entry)))
        self._audit_logs.append(clean_entry)
        if len(self._audit_logs) > 200:
            self._audit_logs.pop(0)
        logger.info(f"[AUDIT] {action} {scope} success={success}")

    def get_audit_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        return list(reversed(self._audit_logs[-limit:]))


permission_manager = PermissionManager()
