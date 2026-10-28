"""
Clipboard Assistant Service.
Provides reading, copying, and clearing the system clipboard with privacy guards.
"""

from typing import Tuple, Optional
import pyperclip
from backend.config.settings import settings


class ClipboardService:
    def read_clipboard(self) -> Tuple[bool, str, Optional[str]]:
        if not settings.clipboard_permission_enabled:
            return False, "Clipboard access is disabled in Settings for your privacy.", None

        try:
            content = pyperclip.paste()
            if not content or not content.strip():
                return True, "Your clipboard is currently empty.", ""

            preview = content.strip()
            # If long, truncate spoken preview
            if len(preview) > 100:
                spoken = f"Your clipboard contains {len(preview)} characters starting with: {preview[:80]}..."
            else:
                spoken = f"Your clipboard contains: {preview}"
            return True, spoken, content
        except Exception as e:
            return False, f"Could not read clipboard: {str(e)}", None

    def write_clipboard(self, text: str) -> Tuple[bool, str]:
        if not settings.clipboard_permission_enabled:
            return False, "Clipboard access is disabled in Settings."

        try:
            pyperclip.copy(text)
            return True, f"Copied '{text}' to clipboard."
        except Exception as e:
            return False, f"Could not copy text: {str(e)}"

    def clear_clipboard(self) -> Tuple[bool, str]:
        if not settings.clipboard_permission_enabled:
            return False, "Clipboard access is disabled in Settings."

        try:
            pyperclip.copy("")
            return True, "Clipboard cleared."
        except Exception as e:
            return False, f"Could not clear clipboard: {str(e)}"


clipboard_service = ClipboardService()
