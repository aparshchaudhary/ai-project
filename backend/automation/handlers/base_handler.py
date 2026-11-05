"""
Base Application Handler Interface for Universal Desktop Automation.
Defines:
- Supported actions & capabilities
- Execution interface
- Result verification
- Timeout and error handling
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class BaseAppHandler(ABC):
    def __init__(
        self,
        app_key: str,
        display_name: str,
        supported_actions: List[str],
        required_permissions: Optional[List[str]] = None,
        timeout_seconds: float = 10.0
    ):
        self.app_key = app_key.lower().strip()
        self.display_name = display_name
        self.supported_actions = supported_actions
        self.required_permissions = required_permissions or []
        self.timeout_seconds = timeout_seconds

    @abstractmethod
    async def execute(self, action: str, params: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Executes a supported action on the application.
        Returns:
            (success, human_readable_message, execution_metadata)
        """
        pass

    @abstractmethod
    def verify(self, action: str, params: Dict[str, Any], result_data: Dict[str, Any]) -> bool:
        """Verifies that the action completed successfully on the desktop."""
        pass

    @abstractmethod
    def is_installed(self) -> bool:
        """Checks if the application is installed and accessible on this machine."""
        pass

    def supports_action(self, action: str) -> bool:
        return action.lower().strip() in [a.lower() for a in self.supported_actions]

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "app_key": self.app_key,
            "display_name": self.display_name,
            "installed": self.is_installed(),
            "supported_actions": self.supported_actions,
            "required_permissions": self.required_permissions,
            "timeout_seconds": self.timeout_seconds
        }
