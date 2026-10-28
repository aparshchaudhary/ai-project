"""
Application Control and Web Automation Service.
Handles launching/closing desktop applications via a configurable registry,
and opening web searches/URLs safely without arbitrary shell execution.
"""

import os
import sys
import json
import shutil
import urllib.parse
import webbrowser
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import psutil
from backend.database.database import SessionLocal
from backend.database.models import AppRegistry

logger = logging.getLogger(__name__)


# Default known applications with Windows paths / commands
DEFAULT_APPLICATIONS = [
    {
        "app_key": "chrome",
        "display_name": "Google Chrome",
        "aliases": ["chrome", "google chrome", "chrome browser", "browser"],
        "paths": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            "chrome"
        ],
        "process_name": "chrome.exe"
    },
    {
        "app_key": "msedge",
        "display_name": "Microsoft Edge",
        "aliases": ["edge", "microsoft edge", "msedge"],
        "paths": [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            "msedge"
        ],
        "process_name": "msedge.exe"
    },
    {
        "app_key": "firefox",
        "display_name": "Mozilla Firefox",
        "aliases": ["firefox", "mozilla"],
        "paths": [
            r"C:\Program Files\Mozilla Firefox\firefox.exe",
            "firefox"
        ],
        "process_name": "firefox.exe"
    },
    {
        "app_key": "code",
        "display_name": "Visual Studio Code",
        "aliases": ["vs code", "vscode", "code", "visual studio code"],
        "paths": [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
            r"C:\Program Files\Microsoft VS Code\Code.exe",
            "code"
        ],
        "process_name": "Code.exe"
    },
    {
        "app_key": "notepad",
        "display_name": "Notepad",
        "aliases": ["notepad", "notes", "text editor"],
        "paths": ["notepad.exe", "notepad"],
        "process_name": "notepad.exe"
    },
    {
        "app_key": "calculator",
        "display_name": "Calculator",
        "aliases": ["calculator", "calc", "hisaab"],
        "paths": ["calc.exe", "calc"],
        "process_name": "CalculatorApp.exe"
    },
    {
        "app_key": "explorer",
        "display_name": "File Explorer",
        "aliases": ["explorer", "file explorer", "files", "my computer"],
        "paths": ["explorer.exe", "explorer"],
        "process_name": "explorer.exe"
    },
    {
        "app_key": "terminal",
        "display_name": "Windows Terminal / Command Prompt",
        "aliases": ["terminal", "cmd", "command prompt", "powershell", "wt"],
        "paths": ["wt.exe", "cmd.exe", "powershell.exe"],
        "process_name": "WindowsTerminal.exe"
    },
    {
        "app_key": "spotify",
        "display_name": "Spotify",
        "aliases": ["spotify", "music app"],
        "paths": [
            os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
            "spotify"
        ],
        "process_name": "Spotify.exe"
    },
    {
        "app_key": "discord",
        "display_name": "Discord",
        "aliases": ["discord"],
        "paths": [
            os.path.expandvars(r"%LOCALAPPDATA%\Discord\Update.exe --processStart Discord.exe"),
            "discord"
        ],
        "process_name": "Discord.exe"
    },
    {
        "app_key": "taskmgr",
        "display_name": "Task Manager",
        "aliases": ["task manager", "taskmgr", "activity monitor"],
        "paths": ["taskmgr.exe"],
        "process_name": "Taskmgr.exe"
    },
    {
        "app_key": "settings",
        "display_name": "Windows Settings",
        "aliases": ["settings", "system settings", "windows settings"],
        "paths": ["start ms-settings:"],
        "process_name": "SystemSettings.exe"
    },
    {
        "app_key": "whatsapp",
        "display_name": "WhatsApp",
        "aliases": ["whatsapp", "whats app", "wa", "whatsapp desktop"],
        "paths": [
            "start whatsapp:",
            os.path.expandvars(r"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\WhatsApp\WhatsApp.exe"),
            "https://web.whatsapp.com"
        ],
        "process_name": "WhatsApp.exe"
    }
]


class AutomationService:
    def __init__(self):
        self._seed_default_apps()

    def _seed_default_apps(self):
        """Seeds standard applications in DB and ensures newly added defaults exist."""
        db = SessionLocal()
        try:
            existing_keys = {item.app_key for item in db.query(AppRegistry.app_key).all()}
            for app in DEFAULT_APPLICATIONS:
                if app["app_key"] not in existing_keys:
                    resolved_exec = self._resolve_executable(app["paths"])
                    item = AppRegistry(
                        app_key=app["app_key"],
                        display_name=app["display_name"],
                        aliases_json=json.dumps(app["aliases"]),
                        exec_path=resolved_exec or app["paths"][0],
                        is_custom=False,
                        is_available=True
                    )
                    db.add(item)
            db.commit()
        except Exception as e:
            logger.error(f"Error seeding app registry: {e}")
            db.rollback()
        finally:
            db.close()

    def _resolve_executable(self, paths: List[str]) -> Optional[str]:
        for p in paths:
            if p.startswith("start "):
                return p
            if os.path.exists(p):
                return p
            found = shutil.which(p)
            if found:
                return found
        return None

    def get_registered_apps(self) -> List[Dict[str, Any]]:
        db = SessionLocal()
        try:
            items = db.query(AppRegistry).all()
            return [
                {
                    "id": item.id,
                    "app_key": item.app_key,
                    "display_name": item.display_name,
                    "aliases": json.loads(item.aliases_json or "[]"),
                    "exec_path": item.exec_path,
                    "is_custom": item.is_custom,
                    "is_available": item.is_available
                }
                for item in items
            ]
        finally:
            db.close()

    def add_custom_app(self, app_key: str, display_name: str, aliases: List[str], exec_path: str) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            existing = db.query(AppRegistry).filter(AppRegistry.app_key == app_key.lower()).first()
            if existing:
                existing.display_name = display_name
                existing.aliases_json = json.dumps(aliases)
                existing.exec_path = exec_path
                existing.is_available = os.path.exists(exec_path) or bool(shutil.which(exec_path))
            else:
                existing = AppRegistry(
                    app_key=app_key.lower(),
                    display_name=display_name,
                    aliases_json=json.dumps(aliases),
                    exec_path=exec_path,
                    is_custom=True,
                    is_available=os.path.exists(exec_path) or bool(shutil.which(exec_path))
                )
                db.add(existing)
            db.commit()
            db.refresh(existing)
            return {
                "id": existing.id,
                "app_key": existing.app_key,
                "display_name": existing.display_name,
                "aliases": json.loads(existing.aliases_json),
                "exec_path": existing.exec_path,
                "is_custom": existing.is_custom,
                "is_available": existing.is_available
            }
        finally:
            db.close()

    def find_app(self, target: str) -> Optional[AppRegistry]:
        db = SessionLocal()
        try:
            target_clean = target.lower().strip()
            apps = db.query(AppRegistry).all()
            # 1. Exact match by key
            for a in apps:
                if a.app_key == target_clean:
                    return a
            # 2. Check aliases
            for a in apps:
                aliases = json.loads(a.aliases_json or "[]")
                if target_clean in [alias.lower() for alias in aliases]:
                    return a
            # 3. Substring match
            for a in apps:
                if target_clean in a.app_key or target_clean in a.display_name.lower():
                    return a
                aliases = json.loads(a.aliases_json or "[]")
                if any(target_clean in al.lower() for al in aliases):
                    return a
            return None
        finally:
            db.close()

    def launch_app(self, target: str) -> Tuple[bool, str]:
        app = self.find_app(target)
        if not app:
            # Try fallback generic executable or start command
            cleaned = target.replace(" ", "")
            which_res = shutil.which(cleaned)
            if which_res:
                try:
                    subprocess.Popen([which_res], shell=False)
                    return True, f"Launching {target}."
                except Exception as e:
                    return False, f"Could not launch {target}: {str(e)}"
            return False, f"I couldn't find '{target}' on this computer. You can add it in Settings."

        exec_path = app.exec_path
        try:
            if exec_path.startswith("start "):
                os.system(exec_path)
                return True, f"Opening {app.display_name}."

            resolved = self._resolve_executable([exec_path])
            if resolved:
                subprocess.Popen([resolved], shell=False)
                return True, f"Opening {app.display_name}."
            else:
                # Try direct run
                subprocess.Popen(exec_path, shell=True)
                return True, f"Launching {app.display_name}."
        except Exception as e:
            logger.error(f"Error launching {app.display_name}: {e}")
            return False, f"Failed to open {app.display_name}: {str(e)}"

    def close_app(self, target: str) -> Tuple[bool, str]:
        app = self.find_app(target)
        search_name = app.app_key if app else target.lower()

        killed = 0
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                pname = proc.info['name'].lower()
                if search_name in pname:
                    proc.terminate()
                    killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if killed > 0:
            name = app.display_name if app else target
            return True, f"Closed {name} ({killed} process{'es' if killed > 1 else ''})."
        else:
            return False, f"No running instance of '{target}' was found."

    def search_web(self, query: str, engine: str = "google") -> Tuple[bool, str]:
        if not query or not query.strip():
            query = "technology news"

        encoded = urllib.parse.quote_plus(query.strip())
        engines = {
            "google": f"https://www.google.com/search?q={encoded}",
            "youtube": f"https://www.youtube.com/results?search_query={encoded}",
            "wikipedia": f"https://en.wikipedia.org/wiki/Special:Search?search={encoded}",
            "github": f"https://github.com/search?q={encoded}",
            "bing": f"https://www.bing.com/search?q={encoded}"
        }

        url = engines.get(engine.lower(), engines["google"])
        try:
            webbrowser.open(url)
            engine_name = engine.capitalize() if engine != "google" else "Google"
            return True, f"Searching {engine_name} for '{query}'."
        except Exception as e:
            return False, f"Failed to open browser: {str(e)}"

    def open_website(self, url: str) -> Tuple[bool, str]:
        clean_url = url.strip()
        if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
            clean_url = "https://" + clean_url

        try:
            webbrowser.open(clean_url)
            return True, f"Opening {clean_url} in your browser."
        except Exception as e:
            return False, f"Could not open website: {str(e)}"


automation_service = AutomationService()
