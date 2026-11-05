"""
Universal Automation Registry.
Tracks:
- Registered application automation handlers
- Available desktop applications and executable paths
- Supported actions and capability matrices
- Permission requirements
- Dynamic custom application registration
"""

from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional

from backend.automation.handlers.base_handler import BaseAppHandler
from backend.automation.handlers.whatsapp_handler import WhatsAppHandler
from backend.automation.handlers.chrome_handler import ChromeHandler
from backend.automation.handlers.notepad_handler import NotepadHandler
from backend.automation.handlers.vscode_handler import VSCodeHandler
from backend.automation.handlers.explorer_handler import ExplorerHandler
from backend.automation.handlers.calculator_handler import CalculatorHandler
from backend.automation.handlers.spotify_handler import SpotifyHandler
from backend.services.desktop_window_manager import desktop_window_manager

logger = logging.getLogger(__name__)


class AutomationRegistry:
    def __init__(self):
        self._handlers: Dict[str, BaseAppHandler] = {}
        self._register_default_handlers()

    def _register_default_handlers(self):
        defaults = [
            WhatsAppHandler(),
            ChromeHandler(),
            NotepadHandler(),
            VSCodeHandler(),
            ExplorerHandler(),
            CalculatorHandler(),
            SpotifyHandler()
        ]
        for handler in defaults:
            self.register_handler(handler)

    def register_handler(self, handler: BaseAppHandler):
        """Registers an application automation handler."""
        self._handlers[handler.app_key] = handler
        logger.info(f"Registered automation handler: '{handler.app_key}' ({handler.display_name})")

    def get_handler(self, app_key: str) -> Optional[BaseAppHandler]:
        """Resolves handler by application key or alias."""
        clean = app_key.lower().strip()
        if clean in self._handlers:
            return self._handlers[clean]

        alias_map = {
            "google chrome": "chrome",
            "browser": "chrome",
            "browsre": "chrome",
            "whats app": "whatsapp",
            "wa": "whatsapp",
            "vs code": "code",
            "visual studio code": "code",
            "calc": "calculator",
            "file explorer": "explorer",
            "files": "explorer",
            "notes": "notepad",
            "text editor": "notepad"
        }
        if clean in alias_map and alias_map[clean] in self._handlers:
            return self._handlers[alias_map[clean]]

        for key, h in self._handlers.items():
            if clean in key or clean in h.display_name.lower():
                return h

        return None

    def list_handlers(self) -> List[Dict[str, Any]]:
        """Returns metadata and status for all registered handlers."""
        return [h.get_capabilities() for h in self._handlers.values()]

    def is_action_supported(self, app_key: str, action: str) -> Tuple[bool, str]:
        """Checks if an application supports a requested action."""
        handler = self.get_handler(app_key)
        if not handler:
            return False, f"Application '{app_key}' does not have a registered automation handler."
        if not handler.supports_action(action):
            actions_str = ", ".join(handler.supported_actions)
            return False, f"Application '{handler.display_name}' does not support action '{action}'. Supported actions: {actions_str}."
        return True, ""


automation_registry = AutomationRegistry()
