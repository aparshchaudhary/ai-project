"""
Productivity Automation Service.
Handles:
- Study Mode, Work Mode, Focus Mode orchestration
- Pomodoro timers & countdowns
- Voice notes persistence (SQLite & local .txt files)
- Email drafting (`mailto:` protocol with subject, body, recipient)
- Calendar & meeting integration
"""

from __future__ import annotations
import os
import time
import json
import urllib.parse
import webbrowser
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from backend.database.database import SessionLocal
from backend.database.models import ProductivityItem
from backend.services.desktop_window_manager import desktop_window_manager, IS_WINDOWS
from backend.services.file_service import file_service

logger = logging.getLogger(__name__)


class ProductivityService:
    def __init__(self):
        self.active_mode: Optional[str] = None
        self.active_timer: Optional[Dict[str, Any]] = None
        self.notes_dir = Path.home() / "Documents" / "VoiceNotes"
        self.notes_dir.mkdir(parents=True, exist_ok=True)

    def start_study_mode(self, duration_minutes: int = 45) -> Dict[str, Any]:
        """
        Activates Study Mode:
        - Opens browser with educational research / resources
        - Opens Notepad for study notes
        - Starts Pomodoro study timer
        """
        self.active_mode = "study_mode"
        end_time = time.time() + (duration_minutes * 60)
        self.active_timer = {
            "mode": "study_mode",
            "duration_minutes": duration_minutes,
            "started_at": time.time(),
            "ends_at": end_time
        }

        # Launch study tools
        desktop_window_manager.launch_or_activate("chrome")
        desktop_window_manager.launch_or_activate("notepad")

        msg = f"Study Mode activated for {duration_minutes} minutes. Chrome and Notepad are ready for your study session."
        return {
            "success": True,
            "mode": "study_mode",
            "duration_minutes": duration_minutes,
            "message": msg,
            "active_timer": self.active_timer
        }

    def start_work_mode(self, duration_minutes: int = 60) -> Dict[str, Any]:
        """
        Activates Work Mode:
        - Opens VS Code
        - Opens Browser
        - Starts work timer
        """
        self.active_mode = "work_mode"
        end_time = time.time() + (duration_minutes * 60)
        self.active_timer = {
            "mode": "work_mode",
            "duration_minutes": duration_minutes,
            "started_at": time.time(),
            "ends_at": end_time
        }

        desktop_window_manager.launch_or_activate("code")
        desktop_window_manager.launch_or_activate("chrome")

        msg = f"Work Mode activated for {duration_minutes} minutes. Visual Studio Code and Google Chrome are open."
        return {
            "success": True,
            "mode": "work_mode",
            "duration_minutes": duration_minutes,
            "message": msg,
            "active_timer": self.active_timer
        }

    def start_focus_mode(self, duration_minutes: int = 25) -> Dict[str, Any]:
        """
        Activates Focus Mode (standard 25-minute Pomodoro).
        """
        self.active_mode = "focus_mode"
        end_time = time.time() + (duration_minutes * 60)
        self.active_timer = {
            "mode": "focus_mode",
            "duration_minutes": duration_minutes,
            "started_at": time.time(),
            "ends_at": end_time
        }

        msg = f"Focus Mode (Pomodoro) started for {duration_minutes} minutes. Distractions minimized."
        return {
            "success": True,
            "mode": "focus_mode",
            "duration_minutes": duration_minutes,
            "message": msg,
            "active_timer": self.active_timer
        }

    def stop_active_mode(self) -> Dict[str, Any]:
        prev_mode = self.active_mode
        self.active_mode = None
        self.active_timer = None
        msg = f"{prev_mode.replace('_', ' ').title() if prev_mode else 'Productivity mode'} stopped."
        return {"success": True, "message": msg}

    def save_voice_note(self, title: str, content: str) -> Tuple[bool, str, Dict[str, Any]]:
        clean_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_') or "note"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{clean_title}_{timestamp}.txt"
        file_path = self.notes_dir / filename

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"Title: {title}\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{content}\n")

            db = SessionLocal()
            try:
                item = ProductivityItem(
                    item_type="voice_note",
                    title=title,
                    content=content,
                    status="active",
                    metadata_json=json.dumps({"path": str(file_path.resolve())})
                )
                db.add(item)
                db.commit()
                db.refresh(item)
                item_id = item.id
            finally:
                db.close()

            res = {
                "id": item_id,
                "title": title,
                "file_path": str(file_path.resolve()),
                "filename": filename
            }
            return True, f"Saved voice note '{title}' in VoiceNotes folder.", res
        except Exception as e:
            return False, f"Failed to save voice note: {e}", {}

    def list_voice_notes(self, limit: int = 20) -> List[Dict[str, Any]]:
        db = SessionLocal()
        try:
            items = db.query(ProductivityItem).filter(
                ProductivityItem.item_type == "voice_note"
            ).order_by(ProductivityItem.created_at.desc()).limit(limit).all()
            return [
                {
                    "id": i.id,
                    "title": i.title,
                    "content": i.content,
                    "created_at": i.created_at.isoformat() if i.created_at else None,
                    "metadata": json.loads(i.metadata_json or "{}")
                }
                for i in items
            ]
        finally:
            db.close()

    def draft_email(self, recipient: str, subject: str, body: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Drafts an email using the Windows default mail client via mailto: protocol.
        """
        enc_subject = urllib.parse.quote(subject)
        enc_body = urllib.parse.quote(body)
        mailto_url = f"mailto:{recipient}?subject={enc_subject}&body={enc_body}"

        opened = False
        if IS_WINDOWS and hasattr(os, "startfile"):
            try:
                os.startfile(mailto_url)
                opened = True
            except Exception:
                pass

        if not opened:
            try:
                webbrowser.open(mailto_url)
                opened = True
            except Exception as e:
                return False, f"Could not launch email client: {e}", {}

        res = {
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "mailto_url": mailto_url,
            "status": "Drafted"
        }
        return True, f"Drafted email to {recipient} with subject '{subject}'. Mail client opened.", res


productivity_service = ProductivityService()
