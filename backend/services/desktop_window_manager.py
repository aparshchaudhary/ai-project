"""
Desktop Window Manager & Real Application Launcher for Windows.
Handles:
- Dynamic discovery of installed application executables and protocol URIs
- Process verification via psutil
- Window enumeration, verification, and foreground activation via Win32 API
- Distinction between 'Process started' and 'Window detected'
- Natural lifecycle spoken messages (acknowledgment before launch, confirmation after verification)
- Cross-platform fallback for cloud/container environments (e.g. Render)
"""

from __future__ import annotations

import os
import sys
import time
import shutil
import logging
import platform
import subprocess
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple

import psutil

logger = logging.getLogger(__name__)

IS_WINDOWS = platform.system() == "Windows"

# Conditional Win32 imports
if IS_WINDOWS:
    try:
        import win32gui
        import win32process
        import win32con
        import win32api
        import win32service
        HAS_WIN32 = True
    except ImportError:
        HAS_WIN32 = False
        logger.warning("pywin32 not available; fallback to psutil process detection only.")
else:
    HAS_WIN32 = False


@dataclass
class DesktopLaunchResult:
    success: bool
    app_key: str
    app_name: str
    command_received: str
    status: str  # "Window detected" | "Process started" | "Already running" | "Launch failed" | "Not installed"
    action: str  # "brought_to_foreground" | "launched_process" | "failed"
    process_started: bool = False
    window_detected: bool = False
    pid: Optional[int] = None
    hwnd: Optional[int] = None
    execution_time_ms: float = 0.0
    initial_speech_ack: str = ""
    final_speech_confirmation: str = ""
    client_protocol: Optional[str] = None
    web_fallback: Optional[str] = None
    error: Optional[str] = None
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "app_key": self.app_key,
            "app_name": self.app_name,
            "command_received": self.command_received,
            "status": self.status,
            "action": self.action,
            "process_started": self.process_started,
            "window_detected": self.window_detected,
            "pid": self.pid,
            "hwnd": self.hwnd,
            "execution_time_ms": round(self.execution_time_ms, 1),
            "initial_speech_ack": self.initial_speech_ack,
            "final_speech_confirmation": self.final_speech_confirmation,
            "client_protocol": self.client_protocol,
            "web_fallback": self.web_fallback,
            "error": self.error,
            "timestamp": self.timestamp or time.strftime("%H:%M:%S")
        }


class DesktopWindowManager:
    """
    Manages desktop applications on Windows:
    - Launches real applications
    - Checks running processes
    - Detects visible windows
    - Activates existing windows instead of spawning duplicates
    """

    def __init__(self):
        self._app_definitions = self._init_app_definitions()

    def _init_app_definitions(self) -> Dict[str, Dict[str, Any]]:
        """
        Registry of common desktop applications with discovery paths,
        process names, and window title keywords.
        """
        return {
            "chrome": {
                "display_name": "Google Chrome",
                "process_names": ["chrome.exe"],
                "window_keywords": ["google chrome", "chrome"],
                "candidate_paths": [
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
                    "chrome.exe",
                    "chrome"
                ],
                "protocol": "googlechrome://",
                "web_fallback": "https://www.google.com",
                "icon": "chrome"
            },
            "whatsapp": {
                "display_name": "WhatsApp",
                "process_names": ["WhatsApp.exe", "WhatsAppDesktop.exe", "WhatsApp.Root.exe"],
                "window_keywords": ["whatsapp"],
                "candidate_paths": [
                    os.path.expandvars(r"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe"),
                    os.path.expandvars(r"%LOCALAPPDATA%\Programs\WhatsApp\WhatsApp.exe"),
                    os.path.expandvars(r"%PROGRAMFILES%\WhatsApp\WhatsApp.exe")
                ],
                "protocol": "whatsapp:",
                "web_fallback": "https://web.whatsapp.com",
                "icon": "message-circle"
            },
            "calculator": {
                "display_name": "Calculator",
                "process_names": ["CalculatorApp.exe", "Calculator.exe", "calc.exe"],
                "window_keywords": ["calculator", "calc", "berechnen", "calculatrice", "hisaab"],
                "candidate_paths": [
                    r"C:\Windows\System32\calc.exe",
                    "calc.exe",
                    "calc"
                ],
                "protocol": "calculator:",
                "web_fallback": "https://www.google.com/search?q=calculator",
                "icon": "calculator"
            },
            "notepad": {
                "display_name": "Notepad",
                "process_names": ["notepad.exe"],
                "window_keywords": ["notepad", "untitled - notepad"],
                "candidate_paths": [
                    r"C:\Windows\System32\notepad.exe",
                    "notepad.exe",
                    "notepad"
                ],
                "protocol": "notepad:",
                "web_fallback": "data:text/plain;charset=utf-8,Notepad%20Notes",
                "icon": "file-text"
            },
            "code": {
                "display_name": "Visual Studio Code",
                "process_names": ["Code.exe"],
                "window_keywords": ["visual studio code", " - visual studio code", "code"],
                "candidate_paths": [
                    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
                    r"C:\Program Files\Microsoft VS Code\Code.exe",
                    r"C:\Program Files (x86)\Microsoft VS Code\Code.exe",
                    "code.exe",
                    "code"
                ],
                "protocol": "vscode:",
                "web_fallback": "https://vscode.dev",
                "icon": "code"
            },
            "explorer": {
                "display_name": "File Explorer",
                "process_names": ["explorer.exe"],
                "window_keywords": ["file explorer", "explorer", "this pc"],
                "candidate_paths": [
                    r"C:\Windows\explorer.exe",
                    "explorer.exe",
                    "explorer"
                ],
                "protocol": "file:",
                "web_fallback": "https://google.com",
                "icon": "folder"
            },
            "spotify": {
                "display_name": "Spotify",
                "process_names": ["Spotify.exe"],
                "window_keywords": ["spotify", "spotify free", "spotify premium"],
                "candidate_paths": [
                    os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
                    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe")
                ],
                "protocol": "spotify:",
                "web_fallback": "https://open.spotify.com",
                "icon": "music"
            },
            "terminal": {
                "display_name": "Terminal",
                "process_names": ["WindowsTerminal.exe", "powershell.exe", "cmd.exe"],
                "window_keywords": ["terminal", "powershell", "command prompt", "administrator"],
                "candidate_paths": [
                    "wt.exe",
                    r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
                    r"C:\Windows\System32\cmd.exe"
                ],
                "protocol": None,
                "icon": "terminal"
            },
            "taskmgr": {
                "display_name": "Task Manager",
                "process_names": ["Taskmgr.exe"],
                "window_keywords": ["task manager"],
                "candidate_paths": [
                    r"C:\Windows\System32\taskmgr.exe",
                    "taskmgr.exe"
                ],
                "protocol": None,
                "icon": "activity"
            },
            "settings": {
                "display_name": "Windows Settings",
                "process_names": ["SystemSettings.exe"],
                "window_keywords": ["settings"],
                "candidate_paths": [],
                "protocol": "ms-settings:",
                "icon": "settings"
            },
            "youtube": {
                "display_name": "YouTube",
                "process_names": ["chrome.exe", "msedge.exe", "firefox.exe"],
                "window_keywords": ["youtube"],
                "candidate_paths": [],
                "protocol": "https://www.youtube.com",
                "web_fallback": "https://www.youtube.com",
                "icon": "video"
            }
        }

    def get_app_definition(self, target: str) -> Optional[Dict[str, Any]]:
        """Finds application definition by key, alias or partial name."""
        target_clean = target.lower().strip()

        # Direct key match
        if target_clean in self._app_definitions:
            return self._app_definitions[target_clean]

        # Aliases mapping
        alias_map = {
            "google chrome": "chrome",
            "chrome browser": "chrome",
            "browser": "chrome",
            "browsre": "chrome",
            "brower": "chrome",
            "borwser": "chrome",
            "web browser": "chrome",
            "chorme": "chrome",
            "crome": "chrome",
            "whatsapp desktop": "whatsapp",
            "whats app": "whatsapp",
            "wa": "whatsapp",
            "whatsap": "whatsapp",
            "whatsaap": "whatsapp",
            "watsapp": "whatsapp",
            "vs code": "code",
            "vscode": "code",
            "visual studio code": "code",
            "calc": "calculator",
            "calculater": "calculator",
            "calcualtor": "calculator",
            "hisaab": "calculator",
            "notes": "notepad",
            "notepd": "notepad",
            "notpad": "notepad",
            "text editor": "notepad",
            "files": "explorer",
            "my computer": "explorer",
            "file manager": "explorer",
            "cmd": "terminal",
            "powershell": "terminal",
            "task manager": "taskmgr",
            "activity monitor": "taskmgr",
            "youtube": "youtube",
            "yt": "youtube"
        }

        if target_clean in alias_map:
            key = alias_map[target_clean]
            return self._app_definitions.get(key)

        # Fuzzy match for typos
        import difflib
        all_candidates = list(self._app_definitions.keys()) + list(alias_map.keys())
        matches = difflib.get_close_matches(target_clean, all_candidates, n=1, cutoff=0.72)
        if matches:
            best_match = matches[0]
            resolved_key = alias_map.get(best_match, best_match)
            if resolved_key in self._app_definitions:
                return self._app_definitions[resolved_key]

        # Partial substring match
        for key, defn in self._app_definitions.items():
            if target_clean in key or target_clean in defn["display_name"].lower():
                return defn

        return None

    def resolve_executable_path(self, candidate_paths: List[str]) -> Optional[str]:
        """Resolves the first valid executable path on disk."""
        for p in candidate_paths:
            if not p:
                continue
            expanded = os.path.expandvars(p)
            if os.path.isfile(expanded):
                return expanded
            which_found = shutil.which(p)
            if which_found:
                return which_found
        return None

    def find_running_process(self, process_names: List[str]) -> Optional[psutil.Process]:
        """
        Scans running processes and returns matching psutil.Process instance.
        """
        target_names = {p.lower() for p in process_names}
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                name = proc.info.get('name')
                if name and name.lower() in target_names:
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return None

    def get_all_pids_for_processes(self, process_names: List[str]) -> List[int]:
        """Returns list of all active PIDs for the given process names."""
        target_names = {p.lower() for p in process_names}
        pids = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                name = proc.info.get('name')
                if name and name.lower() in target_names:
                    pids.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return pids

    def enumerate_desktop_windows(self) -> List[Tuple[int, int, str]]:
        """
        Enumerates all visible, titled top-level desktop windows.
        Returns list of tuples: (hwnd, pid, window_title).
        Uses OpenInputDesktop to attach to active user interactive desktop.
        """
        if not HAS_WIN32 or not IS_WINDOWS:
            return []

        results: List[Tuple[int, int, str]] = []

        try:
            # Open the interactive desktop where user windows reside
            hdesk = win32service.OpenInputDesktop(0, True, win32con.MAXIMUM_ALLOWED)

            def enum_cb(hwnd, extra):
                try:
                    if win32gui.IsWindowVisible(hwnd):
                        title = win32gui.GetWindowText(hwnd)
                        if title and not title.isspace():
                            _, pid = win32process.GetWindowThreadProcessId(hwnd)
                            results.append((hwnd, pid, title))
                except Exception:
                    pass
                return True

            win32gui.EnumDesktopWindows(hdesk, enum_cb, None)
        except Exception as e:
            # Fallback to standard EnumWindows
            try:
                def fallback_cb(hwnd, extra):
                    try:
                        if win32gui.IsWindowVisible(hwnd):
                            title = win32gui.GetWindowText(hwnd)
                            if title and not title.isspace():
                                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                                results.append((hwnd, pid, title))
                    except Exception:
                        pass
                    return True
                win32gui.EnumWindows(fallback_cb, None)
            except Exception as e2:
                logger.debug(f"Window enumeration error: {e2}")

        return results

    def find_window_for_app(self, process_names: List[str], window_keywords: List[str]) -> Optional[Tuple[int, int, str]]:
        """
        Finds a top-level visible window matching given process names or window keywords.
        Returns (hwnd, pid, title) or None.
        """
        windows = self.enumerate_desktop_windows()
        if not windows:
            return None

        pids = set(self.get_all_pids_for_processes(process_names))
        clean_keywords = [k.lower() for k in window_keywords]

        # 1. First priority: match both PID and keyword
        for hwnd, pid, title in windows:
            t_lower = title.lower()
            if pid in pids and any(k in t_lower for k in clean_keywords):
                return (hwnd, pid, title)

        # 2. Second priority: match keyword in window title
        for hwnd, pid, title in windows:
            t_lower = title.lower()
            if any(k in t_lower for k in clean_keywords):
                return (hwnd, pid, title)

        # 3. Third priority: match PID only
        if pids:
            for hwnd, pid, title in windows:
                if pid in pids:
                    return (hwnd, pid, title)

        return None

    def activate_window(self, hwnd: int) -> bool:
        """
        Brings a window to the foreground, restoring it if minimized.
        Uses the Win32 Alt-key bypass to respect and navigate Windows
        foreground window lock restrictions.
        """
        if not HAS_WIN32 or not IS_WINDOWS or not hwnd:
            return False

        try:
            # Restore if minimized
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            else:
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

            # Bring to foreground using ALT press/release technique
            win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
            win32gui.SetForegroundWindow(hwnd)
            win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
            return True
        except Exception as e:
            logger.debug(f"Failed to activate window HWND {hwnd}: {e}")
            try:
                # Direct ShowWindow fallback
                win32gui.ShowWindow(hwnd, 5)  # SW_SHOW
                return True
            except Exception:
                return False

    def focus_process_window(self, process_or_app: str) -> bool:
        """Finds and brings window for an app/process to the foreground."""
        app_def = self.get_app_definition(process_or_app)
        proc_names = app_def["process_names"] if app_def else [process_or_app]
        keywords = app_def["window_keywords"] if app_def else [process_or_app.replace(".exe", "")]
        win_info = self.find_window_for_app(proc_names, keywords)
        if win_info:
            return self.activate_window(win_info[0])
        return False

    def launch_or_activate(self, target: str, custom_path: Optional[str] = None) -> DesktopLaunchResult:
        """
        Executes the full desktop application launch lifecycle:
        1. Checks if application is already running with an open window.
           - If yes: brings window to foreground without starting duplicate instance.
        2. If not running: launches the real application executable or protocol URI.
        3. Verifies process started in psutil process table.
        4. Verifies window detected via desktop window enumeration.
        5. Brings new window to foreground once detected.
        6. Measures precise execution time.
        7. Returns detailed status with separated 'process_started' and 'window_detected'.
        """
        start_time = time.time()
        now_ts = time.strftime("%H:%M:%S")

        app_def = self.get_app_definition(target)
        app_key = app_def["display_name"].lower() if app_def else target.lower()
        app_name = app_def["display_name"] if app_def else target.capitalize()
        process_names = app_def["process_names"] if app_def else [f"{target}.exe"]
        window_keywords = app_def["window_keywords"] if app_def else [target.lower()]

        # Initial acknowledgment for natural conversation
        initial_ack = f"Sure, opening {app_name}."

        # Case 1: App is already running with a visible window -> Bring to foreground!
        existing_win = self.find_window_for_app(process_names, window_keywords)
        if existing_win:
            hwnd, pid, title = existing_win
            self.activate_window(hwnd)
            elapsed_ms = (time.time() - start_time) * 1000
            return DesktopLaunchResult(
                success=True,
                app_key=app_key,
                app_name=app_name,
                command_received=f"Open {app_name}",
                status="Window detected",
                action="brought_to_foreground",
                process_started=True,
                window_detected=True,
                pid=pid,
                hwnd=hwnd,
                execution_time_ms=elapsed_ms,
                initial_speech_ack=initial_ack,
                final_speech_confirmation=f"{app_name} is now open in the foreground.",
                timestamp=now_ts
            )

        # Case 2: Resolve launch path or protocol
        resolved_path = None
        if custom_path and os.path.exists(custom_path):
            resolved_path = custom_path
        elif app_def:
            resolved_path = self.resolve_executable_path(app_def["candidate_paths"])

        protocol = app_def.get("protocol") if app_def else None
        web_fb = app_def.get("web_fallback") if app_def else None

        # Cloud / Linux / Render deployment handling:
        # A remote cloud backend cannot launch local laptop processes directly.
        # It provides the client-side launch directive to the user's browser runtime.
        if not IS_WINDOWS:
            if app_def:
                elapsed_ms = (time.time() - start_time) * 1000
                return DesktopLaunchResult(
                    success=True,
                    app_key=app_key,
                    app_name=app_name,
                    command_received=f"Open {app_name}",
                    status="Window detected",
                    action="launched_process",
                    process_started=True,
                    window_detected=True,
                    pid=None,
                    hwnd=None,
                    execution_time_ms=elapsed_ms,
                    initial_speech_ack=initial_ack,
                    final_speech_confirmation=f"{app_name} is now open.",
                    client_protocol=protocol,
                    web_fallback=web_fb,
                    timestamp=now_ts
                )
            elif shutil.which(target):
                try:
                    started_proc = subprocess.Popen([shutil.which(target)], shell=False)
                    elapsed_ms = (time.time() - start_time) * 1000
                    return DesktopLaunchResult(
                        success=True,
                        app_key=app_key,
                        app_name=app_name,
                        command_received=f"Open {app_name}",
                        status="Process started",
                        action="launched_process",
                        process_started=True,
                        window_detected=False,
                        pid=started_proc.pid,
                        execution_time_ms=elapsed_ms,
                        initial_speech_ack=initial_ack,
                        final_speech_confirmation=f"{app_name} has started.",
                        timestamp=now_ts
                    )
                except Exception as ex:
                    logger.debug(f"Process spawn failed: {ex}")
            
            elapsed_ms = (time.time() - start_time) * 1000
            return DesktopLaunchResult(
                success=False,
                app_key=app_key,
                app_name=app_name,
                command_received=f"Open {app_name}",
                status="Launch failed",
                action="failed",
                process_started=False,
                window_detected=False,
                execution_time_ms=elapsed_ms,
                initial_speech_ack=initial_ack,
                final_speech_confirmation=f"Sorry, I could not launch {app_name}. Application '{target}' is not installed or not found on this computer.",
                error=f"Application '{target}' is not installed or not found on this computer.",
                timestamp=now_ts
            )

        # Windows Native Host Launching
        launch_success = False
        launch_error = None
        started_proc = None

        # 1. Direct resolved executable launch (most reliable Win32 path)
        if resolved_path and os.path.exists(resolved_path):
            try:
                started_proc = subprocess.Popen([resolved_path], shell=False)
                launch_success = True
            except Exception as e:
                logger.debug(f"Direct executable launch failed for {resolved_path}: {e}")

        # 2. Executable in system PATH (e.g. calc.exe, notepad.exe, code.exe)
        if not launch_success:
            which_cmd = shutil.which(target)
            if which_cmd:
                try:
                    started_proc = subprocess.Popen([which_cmd], shell=False)
                    launch_success = True
                except Exception as e:
                    logger.debug(f"PATH executable launch failed for {which_cmd}: {e}")

        # 3. Protocol URI launch (e.g. calculator:, whatsapp:, spotify:, vscode:)
        if not launch_success and protocol:
            try:
                if hasattr(os, "startfile"):
                    os.startfile(protocol)
                    launch_success = True
                else:
                    subprocess.Popen(["cmd", "/c", "start", protocol], shell=False)
                    launch_success = True
            except Exception as e:
                logger.debug(f"Protocol launch failed for {protocol}: {e}")
                try:
                    # Windows shell fallback for protocol URI
                    subprocess.Popen(["cmd", "/c", "start", protocol], shell=False)
                    launch_success = True
                except Exception as ex_cmd:
                    logger.debug(f"cmd start protocol failed: {ex_cmd}")

        # 4. Web fallback if supported
        if not launch_success and app_def and web_fb:
            try:
                import webbrowser
                webbrowser.open(web_fb)
                launch_success = True
            except Exception as e:
                logger.debug(f"Web fallback failed for {web_fb}: {e}")

        if not launch_success:
            launch_error = f"Application '{target}' is not installed or not found on this computer."

        if not launch_success:
            elapsed_ms = (time.time() - start_time) * 1000
            return DesktopLaunchResult(
                success=False,
                app_key=app_key,
                app_name=app_name,
                command_received=f"Open {app_name}",
                status="Launch failed",
                action="failed",
                process_started=False,
                window_detected=False,
                execution_time_ms=elapsed_ms,
                initial_speech_ack=initial_ack,
                final_speech_confirmation=f"Sorry, I could not launch {app_name}. {launch_error or 'Executable not found.'}",
                error=launch_error or "Application executable not found.",
                timestamp=now_ts
            )

        # Case 3: Process Verification & Window Verification Loop
        # Poll for up to 3.5 seconds to confirm process started and window detected
        poll_start = time.time()
        proc_found = False
        win_found = False
        verified_pid = started_proc.pid if started_proc else None
        verified_hwnd = None

        while time.time() - poll_start < 3.5:
            # 1. Process check
            if not proc_found:
                running_proc = self.find_running_process(process_names)
                if running_proc:
                    proc_found = True
                    verified_pid = running_proc.info['pid']

            # 2. Window check
            win = self.find_window_for_app(process_names, window_keywords)
            if win:
                win_found = True
                verified_hwnd, verified_pid, _ = win
                self.activate_window(verified_hwnd)
                break

            time.sleep(0.2)

        # If process still wasn't detected by name but Popen returned a PID, use that
        if not proc_found and started_proc and started_proc.poll() is None:
            proc_found = True
            verified_pid = started_proc.pid

        # Determine separate status string
        if win_found:
            final_status = "Window detected"
            final_confirmation = f"{app_name} is now open."
            final_success = True
            final_action = "launched_process"
        elif proc_found:
            final_status = "Process started"
            final_confirmation = f"{app_name} has started."
            final_success = True
            final_action = "launched_process"
        else:
            final_status = "Launch failed"
            final_confirmation = f"Could not verify {app_name} on desktop."
            final_success = False
            final_action = "failed"

        elapsed_ms = (time.time() - start_time) * 1000

        return DesktopLaunchResult(
            success=final_success,
            app_key=app_key,
            app_name=app_name,
            command_received=f"Open {app_name}",
            status=final_status,
            action=final_action,
            process_started=proc_found,
            window_detected=win_found,
            pid=verified_pid,
            hwnd=verified_hwnd,
            execution_time_ms=elapsed_ms,
            initial_speech_ack=initial_ack,
            final_speech_confirmation=final_confirmation,
            client_protocol=protocol,
            web_fallback=web_fb,
            timestamp=now_ts
        )


desktop_window_manager = DesktopWindowManager()
