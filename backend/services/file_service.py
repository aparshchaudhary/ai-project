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

    def rename_file(self, target: str, new_name: str) -> Tuple[bool, str, Optional[str]]:
        matches = self.search_files(query=target, max_results=1)
        target_path = Path(matches[0]["path"]) if matches else Path(target)
        if not target_path.exists():
            return False, f"Could not find '{target}' to rename.", None

        if not security_service.is_safe_path(target_path):
            return False, "Access restricted: Cannot rename system files.", None

        clean_new = new_name.strip(" /\\\"'")
        new_path = target_path.parent / clean_new
        if not security_service.is_safe_path(new_path):
            return False, "Access restricted: Invalid target path.", None

        try:
            target_path.rename(new_path)
            return True, f"Renamed '{target_path.name}' to '{clean_new}'.", str(new_path.resolve())
        except Exception as e:
            return False, f"Failed to rename file: {e}", None

    def copy_file(self, target: str, destination_folder: str) -> Tuple[bool, str, Optional[str]]:
        import shutil
        matches = self.search_files(query=target, max_results=1)
        src_path = Path(matches[0]["path"]) if matches else Path(target)
        if not src_path.exists():
            return False, f"Could not find source '{target}'.", None

        parent_map = {
            "documents": Path.home() / "Documents",
            "desktop": Path.home() / "Desktop",
            "downloads": Path.home() / "Downloads",
            "pictures": Path.home() / "Pictures",
        }
        dest_base = parent_map.get(destination_folder.lower(), Path(destination_folder))
        if not dest_base.exists():
            dest_base.mkdir(parents=True, exist_ok=True)

        dest_path = dest_base / src_path.name
        if not security_service.is_safe_path(src_path) or not security_service.is_safe_path(dest_path):
            return False, "Access denied: Restrictive filesystem boundary.", None

        try:
            if src_path.is_dir():
                shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
            else:
                shutil.copy2(src_path, dest_path)
            return True, f"Copied '{src_path.name}' to {dest_base.name}.", str(dest_path.resolve())
        except Exception as e:
            return False, f"Failed to copy '{src_path.name}': {e}", None

    def move_file(self, target: str, destination_folder: str) -> Tuple[bool, str, Optional[str]]:
        import shutil
        matches = self.search_files(query=target, max_results=1)
        src_path = Path(matches[0]["path"]) if matches else Path(target)
        if not src_path.exists():
            return False, f"Could not find source '{target}'.", None

        parent_map = {
            "documents": Path.home() / "Documents",
            "desktop": Path.home() / "Desktop",
            "downloads": Path.home() / "Downloads",
            "pictures": Path.home() / "Pictures",
        }
        dest_base = parent_map.get(destination_folder.lower(), Path(destination_folder))
        if not dest_base.exists():
            dest_base.mkdir(parents=True, exist_ok=True)

        dest_path = dest_base / src_path.name
        if not security_service.is_safe_path(src_path) or not security_service.is_safe_path(dest_path):
            return False, "Access denied: Target path outside authorized safe directories.", None

        try:
            shutil.move(src_path, dest_path)
            return True, f"Moved '{src_path.name}' to {dest_base.name}.", str(dest_path.resolve())
        except Exception as e:
            return False, f"Failed to move '{src_path.name}': {e}", None

    def get_file_metadata(self, target: str) -> Tuple[bool, str, Dict[str, Any]]:
        import time
        matches = self.search_files(query=target, max_results=1)
        p = Path(matches[0]["path"]) if matches else Path(target)
        if not p.exists():
            return False, f"File or folder '{target}' not found.", {}

        stat = p.stat()
        meta = {
            "name": p.name,
            "path": str(p.resolve()),
            "is_directory": p.is_dir(),
            "size_bytes": stat.st_size,
            "size_formatted": f"{stat.st_size / 1024:.1f} KB" if stat.st_size < 1024 * 1024 else f"{stat.st_size / (1024 * 1024):.2f} MB",
            "extension": p.suffix,
            "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
            "created": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_ctime)),
        }
        summary = f"'{p.name}' is {meta['size_formatted']}, last modified on {meta['modified']}."
        return True, summary, meta

    def find_duplicate_files(self, folder: str = "Downloads") -> List[Dict[str, Any]]:
        import hashlib
        parent_map = {
            "downloads": Path.home() / "Downloads",
            "documents": Path.home() / "Documents",
            "desktop": Path.home() / "Desktop",
        }
        target_dir = parent_map.get(folder.lower(), Path(folder))
        if not target_dir.exists():
            return []

        hash_map: Dict[str, List[Path]] = {}
        for path in target_dir.glob("*"):
            if path.is_file() and path.stat().st_size > 0:
                try:
                    hasher = hashlib.md5()
                    with open(path, "rb") as f:
                        for chunk in iter(lambda: f.read(65536), b""):
                            hasher.update(chunk)
                    h = hasher.hexdigest()
                    hash_map.setdefault(h, []).append(path)
                except Exception:
                    continue

        duplicates = []
        for h, paths in hash_map.items():
            if len(paths) > 1:
                duplicates.append({
                    "hash": h,
                    "count": len(paths),
                    "files": [str(p.name) for p in paths]
                })
        return duplicates



file_service = FileService()
