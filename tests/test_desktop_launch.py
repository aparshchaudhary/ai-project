"""
Test Suite for Desktop Window Manager and Real Application Launching Lifecycle.
Tests:
- Application definition discovery and executable resolution
- Process detection & window enumeration
- Real application launching & foreground window activation
- Separation between 'Process started' and 'Window detected'
- Already-running application window foreground restoration
- Non-installed application graceful error handling
- Rapid duplicate command protection
- Full natural conversational acknowledgment and confirmation pipeline
"""

import os
import sys
import time
import pytest
import psutil

from backend.services.desktop_window_manager import desktop_window_manager, DesktopLaunchResult
from backend.services.automation_service import automation_service
from backend.services.command_service import command_service


class TestDesktopWindowManager:
    """Unit and integration tests for DesktopWindowManager."""

    def test_app_definitions_exist(self):
        """Verifies core default apps are defined in registry."""
        for app in ["chrome", "whatsapp", "calculator", "notepad", "code", "explorer"]:
            defn = desktop_window_manager.get_app_definition(app)
            assert defn is not None, f"App definition for {app} missing"
            assert "display_name" in defn
            assert "process_names" in defn
            assert "window_keywords" in defn

    def test_alias_resolution(self):
        """Verifies aliases resolve to canonical app definitions."""
        assert desktop_window_manager.get_app_definition("google chrome")["display_name"] == "Google Chrome"
        assert desktop_window_manager.get_app_definition("vs code")["display_name"] == "Visual Studio Code"
        assert desktop_window_manager.get_app_definition("calc")["display_name"] == "Calculator"
        assert desktop_window_manager.get_app_definition("hisaab")["display_name"] == "Calculator"
        assert desktop_window_manager.get_app_definition("whats app")["display_name"] == "WhatsApp"

    def test_unknown_app_graceful_handling(self):
        """Verifies searching or launching a non-existent app returns clean failure."""
        res = desktop_window_manager.launch_or_activate("non_existent_fake_app_xyz_99")
        assert res.success is False
        assert res.status == "Launch failed"
        assert res.window_detected is False
        assert res.process_started is False
        assert "could not launch" in res.final_speech_confirmation.lower() or "not found" in res.final_speech_confirmation.lower()

    def test_window_enumeration_structure(self):
        """Verifies desktop window enumeration returns valid tuples (hwnd, pid, title)."""
        windows = desktop_window_manager.enumerate_desktop_windows()
        assert isinstance(windows, list)
        for w in windows:
            assert len(w) == 3
            hwnd, pid, title = w
            assert isinstance(hwnd, int)
            assert isinstance(pid, int)
            assert isinstance(title, str)

    def test_running_process_detection(self):
        """Verifies psutil scanning can detect host processes like explorer or python."""
        proc = desktop_window_manager.find_running_process(["explorer.exe", "python.exe"])
        assert proc is not None
        assert proc.pid > 0

    def test_real_calculator_launch_and_window_detection(self):
        """
        End-to-end test of real Calculator application execution.
        Verifies:
        1. Clean fresh launch.
        2. Window detection and process detection.
        3. Subsequent call detects already running window and brings to foreground.
        """
        # Close any previous instances first
        automation_service.close_app("calculator")
        time.sleep(0.5)

        # 1. Fresh launch
        res1 = desktop_window_manager.launch_or_activate("calculator")
        assert res1.success is True
        assert res1.process_started is True
        assert res1.app_name == "Calculator"
        assert "calculator" in res1.final_speech_confirmation.lower()

        # 2. Second call while running -> brings to foreground
        time.sleep(1.0)
        res2 = desktop_window_manager.launch_or_activate("calculator")
        assert res2.success is True
        assert res2.process_started is True
        if res2.window_detected:
            assert res2.action == "brought_to_foreground"
            assert "foreground" in res2.final_speech_confirmation.lower()

        # Cleanup
        automation_service.close_app("calculator")

    def test_automation_service_integration(self):
        """Verifies automation_service.launch_app returns (success, speech, data)."""
        success, msg, data = automation_service.launch_app("calculator")
        assert isinstance(success, bool)
        assert isinstance(msg, str)
        assert isinstance(data, dict)
        assert "status" in data
        assert "action" in data
        assert "window_detected" in data
        assert "process_started" in data

        # Cleanup
        automation_service.close_app("calculator")


class TestCommandServiceLifecycle:
    """Verifies end-to-end command orchestration and deduplication."""

    @pytest.mark.asyncio
    async def test_duplicate_command_dropped(self):
        """Verifies rapid duplicate voice commands within 2 seconds are dropped."""
        cmd = "what time is it right now"
        # First call processes normally
        res1 = await command_service.process_command(cmd)
        assert res1.intent != "duplicate_ignored"

        # Immediate repeat should be ignored as duplicate
        res2 = await command_service.process_command(cmd)
        assert res2.intent == "duplicate_ignored"
        assert "already processed" in res2.response_text.lower()

    @pytest.mark.asyncio
    async def test_open_app_lifecycle_metadata(self):
        """Verifies open_application returns desktop activity telemetry."""
        # Wait to clear any duplicate window
        time.sleep(2.2)
        res = await command_service.process_command("open calculator")
        assert res.success is True
        assert res.intent == "open_application"
        assert res.data is not None
        assert "status" in res.data
        assert "action" in res.data
        assert "execution_time_ms" in res.data

        # Cleanup
        automation_service.close_app("calculator")
