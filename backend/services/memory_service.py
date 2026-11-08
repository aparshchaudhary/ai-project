"""
Personal Memory Service.
Controlled user memory system tracking:
- Preferred browser & media applications
- Custom contact aliases (e.g. "Mom" -> "Anita Sharma")
- Frequently used project folders
- Preferred language
- Repeated custom workflows
Safeguards:
- Explicit rejection of sensitive data (passwords, PINs, tokens, card numbers)
- Full user inspectability, editing, deletion, and toggle controls
"""

from __future__ import annotations
import re
import logging
from typing import Dict, Any, List, Optional, Tuple

from backend.database.database import SessionLocal
from backend.database.models import UserMemory

logger = logging.getLogger(__name__)

SENSITIVE_PATTERNS = [
    re.compile(r"\b(password|passwd|pwd|secret|api[_-]?key|token|auth)\b", re.IGNORECASE),
    re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b"),  # credit cards
    re.compile(r"\b(cvv|cvc|pin|otp)\b", re.IGNORECASE),
]


class MemoryService:
    def __init__(self):
        self._seed_default_memories_if_needed()

    def _seed_default_memories_if_needed(self):
        db = SessionLocal()
        try:
            count = db.query(UserMemory).count()
            if count == 0:
                defaults = [
                    ("preference", "preferred_browser", "Google Chrome"),
                    ("preference", "preferred_language", "English"),
                    ("project_folder", "ai_projects", "~/Documents/AI Projects"),
                    ("alias", "Mom", "Anita Sharma"),
                ]
                for cat, key, val in defaults:
                    mem = UserMemory(category=cat, key=key, value=val, is_enabled=True)
                    db.add(mem)
                db.commit()
        except Exception as e:
            db.rollback()
            logger.debug(f"Memory seeding skipped: {e}")
        finally:
            db.close()

    def is_sensitive(self, text: str) -> bool:
        """Blocks sensitive or confidential data from entering personal memory."""
        for pattern in SENSITIVE_PATTERNS:
            if pattern.search(text):
                return True
        return False

    def get_all_memories(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        db = SessionLocal()
        try:
            q = db.query(UserMemory)
            if category:
                q = q.filter(UserMemory.category == category.lower().strip())
            mems = q.order_by(UserMemory.updated_at.desc()).all()
            return [
                {
                    "id": m.id,
                    "category": m.category,
                    "key": m.key,
                    "value": m.value,
                    "is_enabled": m.is_enabled,
                    "updated_at": m.updated_at.isoformat() if m.updated_at else None
                }
                for m in mems
            ]
        finally:
            db.close()

    def get_memory(self, category: str, key: str) -> Optional[str]:
        db = SessionLocal()
        try:
            mem = db.query(UserMemory).filter(
                UserMemory.category == category.lower().strip(),
                UserMemory.key == key.lower().strip(),
                UserMemory.is_enabled == True
            ).first()
            return mem.value if mem else None
        finally:
            db.close()

    def set_memory(self, category: str, key: str, value: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        if self.is_sensitive(key) or self.is_sensitive(value):
            return False, "Security safeguard: Passwords, tokens, and confidential financial info cannot be saved.", None

        db = SessionLocal()
        try:
            cat_clean = category.lower().strip()
            key_clean = key.strip()
            val_clean = value.strip()

            mem = db.query(UserMemory).filter(
                UserMemory.category == cat_clean,
                UserMemory.key == key_clean
            ).first()

            if mem:
                mem.value = val_clean
                mem.is_enabled = True
            else:
                mem = UserMemory(category=cat_clean, key=key_clean, value=val_clean, is_enabled=True)
                db.add(mem)

            db.commit()
            db.refresh(mem)
            res = {
                "id": mem.id,
                "category": mem.category,
                "key": mem.key,
                "value": mem.value,
                "is_enabled": mem.is_enabled
            }
            return True, f"Remembered {key_clean} as '{val_clean}'.", res
        except Exception as e:
            db.rollback()
            return False, f"Failed to save memory: {e}", None
        finally:
            db.close()

    def delete_memory(self, memory_id: int) -> Tuple[bool, str]:
        db = SessionLocal()
        try:
            mem = db.query(UserMemory).filter(UserMemory.id == memory_id).first()
            if not mem:
                return False, "Memory item not found."
            db.delete(mem)
            db.commit()
            return True, f"Deleted memory '{mem.key}'."
        except Exception as e:
            db.rollback()
            return False, f"Failed to delete memory: {e}"
        finally:
            db.close()

    def toggle_memory(self, memory_id: int, is_enabled: bool) -> Tuple[bool, str]:
        db = SessionLocal()
        try:
            mem = db.query(UserMemory).filter(UserMemory.id == memory_id).first()
            if not mem:
                return False, "Memory item not found."
            mem.is_enabled = is_enabled
            db.commit()
            status_str = "enabled" if is_enabled else "disabled"
            return True, f"Memory '{mem.key}' is now {status_str}."
        except Exception as e:
            db.rollback()
            return False, f"Failed to update memory status: {e}"
        finally:
            db.close()


memory_service = MemoryService()
