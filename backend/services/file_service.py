"""
File and Folder Management Service.
Handles safe searching, creating, opening, and deleting files/directories
strictly within bounded user directories with security checks.
"""

import os
import glob
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from backend.config.settings import settings
from backend.services.security_service import security_service

logger = logging.getLogger(__name__)


class FileService:
    def __init__(self):
        self.default_root = Path.home() / "Documents"
        self.default_root.mkdir(parents=True, exist_ok=True)

    def search_files(self, query: str, extension: Optional[str] = None, max_results: int = 15) -> List[Dict[str, Any]]:
        results = []
        search_dirs = [
            Path.home() / "Desktop",
            Path.home() / "Documents",
            Path.home() / "Downloads",
            settings.data_dir,
            settings.screenshots_dir,
        ]

        query_clean = query.lower().strip() if query else ""

        for root_dir in search_dirs:
            if not root_dir.exists():
                continue

            try:
                # Limit traversal to depth 2 for speed and responsiveness
                for path in root_dir.rglob("*"):
                    if len(results) >= max_results:
                        break

                    try:
                        # Exclude hidden files or node_modules / venv
                        parts = path.parts
                        if any(p.startswith(".") or p in ["node_modules", "venv", "__pycache__", "AppData"] for p in parts):
                            continue

                        name_lower = path.name.lower()
                        match = False

                        if extension:
                            if path.suffix.lower() == extension.lower():
                                match = not query_clean or query_clean in name_lower
                        elif query_clean:
                            match = query_clean in name_lower

                        if match:
                            results.append({
                                "name": path.name,
                                "path": str(path.resolve()),
                                "is_directory": path.is_dir(),
                                "size_bytes": path.stat().st_size if path.is_file() else 0,
                                "extension": path.suffix,
                            })
                    except (PermissionError, FileNotFoundError):
                        continue
            except Exception as e:
                logger.debug(f"Search skipped dir {root_dir}: {e}")

        return results

    def create_folder(self, folder_name: str, parent_folder: Optional[str] = "Documents") -> Tuple[bool, str, Optional[str]]:
        clean_name = folder_name.strip(" /\\\"'")
        if not clean_name:
            clean_name = "New Folder"

        parent_map = {
            "documents": Path.home() / "Documents",
            "desktop": Path.home() / "Desktop",
            "downloads": Path.home() / "Downloads",
            "music": Path.home() / "Music",
            "videos": Path.home() / "Videos",
        }

        parent_key = (parent_folder or "documents").lower()
        base_dir = parent_map.get(parent_key, Path.home() / "Documents")

        target_path = base_dir / clean_name
        if not security_service.is_safe_path(target_path):
            return False, "Permission denied: Cannot create directory outside user space.", None

        try:
            target_path.mkdir(parents=True, exist_ok=True)
            return True, f"Created folder '{clean_name}' in {base_dir.name}.", str(target_path.resolve())
        except Exception as e:
            return False, f"Failed to create folder: {str(e)}", None

    def create_file(self, file_name: str, content: str = "", parent_folder: Optional[str] = "Documents") -> Tuple[bool, str, Optional[str]]:
        clean_name = file_name.strip(" /\\\"'")
        if not clean_name:
            clean_name = "notes.txt"

        parent_map = {
            "documents": Path.home() / "Documents",
            "desktop": Path.home() / "Desktop",
            "downloads": Path.home() / "Downloads",
        }
        parent_key = (parent_folder or "documents").lower()
        base_dir = parent_map.get(parent_key, Path.home() / "Documents")

        target_path = base_dir / clean_name
        if not security_service.is_safe_path(target_path):
            return False, "Permission denied: Target path is restricted.", None

        try:
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True, f"Created file '{clean_name}' in {base_dir.name}.", str(target_path.resolve())
        except Exception as e:
            return False, f"Failed to create file: {str(e)}", None

    def open_path(self, target: str, is_folder: bool = False) -> Tuple[bool, str]:
        # Check standard folder keywords
        target_lower = target.lower().strip()
        common_folders = {
            "downloads": Path.home() / "Downloads",
            "download": Path.home() / "Downloads",
            "documents": Path.home() / "Documents",
            "document": Path.home() / "Documents",
            "desktop": Path.home() / "Desktop",
            "music": Path.home() / "Music",
            "pictures": Path.home() / "Pictures",
            "screenshots": settings.screenshots_dir,
        }

        resolved_path = None
        for k, v in common_folders.items():
            if k in target_lower:
                resolved_path = v
                break

        if not resolved_path:
            # Check if it's an existing file or path directly
            p = Path(target)
            if p.exists():
                resolved_path = p
            else:
                # Search for matching file
                matches = self.search_files(query=target, max_results=1)
                if matches:
                    resolved_path = Path(matches[0]["path"])

        if not resolved_path or not resolved_path.exists():
            return False, f"Could not find '{target}' on your computer."

        if not security_service.is_safe_path(resolved_path):
            return False, "Access to this system directory is restricted for safety."

        try:
            os.startfile(str(resolved_path.resolve()))
            return True, f"Opening '{resolved_path.name}'."
        except Exception as e:
            return False, f"Could not open path: {str(e)}"

    def delete_file(self, target: str) -> Tuple[bool, str]:
        # Search file to delete
        matches = self.search_files(query=target, max_results=1)
        if not matches:
            # Check if direct path
            p = Path(target)
            if not p.exists():
                return False, f"Could not find '{target}' to delete."
            target_path = p
        else:
            target_path = Path(matches[0]["path"])

        if not security_service.is_safe_path(target_path):
            return False, "Safety restriction: Cannot delete system or non-user files."

        try:
            if target_path.is_dir():
                os.rmdir(target_path)
            else:
                os.remove(target_path)
            return True, f"Successfully deleted '{target_path.name}'."
        except Exception as e:
            return False, f"Error deleting '{target_path.name}': {str(e)}"


file_service = FileService()
