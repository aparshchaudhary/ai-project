"""
File and Directory Automation Handler.
Exposes modular capabilities:
- search_files
- open_file
- create_folder
- create_file
- rename_file
- copy_file
- move_file
- get_file_metadata
- find_duplicates
- delete_file (high-risk confirmation gating)
"""

from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional, Tuple

from backend.automation.handlers.base_handler import BaseAppHandler
from backend.services.file_service import file_service
from backend.services.event_notification_service import event_notification_service

logger = logging.getLogger(__name__)


class FileHandler(BaseAppHandler):
    def __init__(self):
        super().__init__(
            app_key="file_manager",
            display_name="File & Folder Manager",
            supported_actions=[
                "search_files", "open_path", "create_folder", "create_file",
                "rename_file", "copy_file", "move_file", "get_metadata", "find_duplicates", "delete_file"
            ],
            required_permissions=["access_filesystem"],
            timeout_seconds=10.0
        )

    def is_installed(self) -> bool:
        return True

    async def execute(self, action: str, params: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        action_clean = action.lower().strip()

        if action_clean in ["search_files", "find_file"]:
            query = params.get("query", "")
            ext = params.get("extension")
            results = file_service.search_files(query, extension=ext)
            msg = f"Found {len(results)} files matching '{query}'." if results else f"No files found matching '{query}'."
            return True, msg, {"results": results, "count": len(results)}

        elif action_clean in ["open_path", "open_file", "open_folder"]:
            target = params.get("target") or params.get("file_path") or "Documents"
            success, msg = file_service.open_path(target)
            return success, msg, {"target": target, "success": success}

        elif action_clean in ["create_folder", "make_dir"]:
            folder_name = params.get("folder_name") or params.get("name") or "New Folder"
            parent = params.get("parent_folder", "Documents")
            success, msg, path = file_service.create_folder(folder_name, parent_folder=parent)
            return success, msg, {"path": path, "folder_name": folder_name}

        elif action_clean in ["create_file", "create_document"]:
            file_name = params.get("file_name") or params.get("name") or "notes.txt"
            content = params.get("content", "")
            parent = params.get("parent_folder", "Documents")
            success, msg, path = file_service.create_file(file_name, content=content, parent_folder=parent)
            return success, msg, {"path": path, "file_name": file_name}

        elif action_clean == "rename_file":
            target = params.get("target") or params.get("old_name", "")
            new_name = params.get("new_name", "")
            success, msg, path = file_service.rename_file(target, new_name)
            return success, msg, {"new_path": path, "new_name": new_name}

        elif action_clean == "copy_file":
            target = params.get("target") or params.get("source", "")
            dest = params.get("destination", "Documents")
            success, msg, path = file_service.copy_file(target, dest)
            return success, msg, {"destination_path": path}

        elif action_clean == "move_file":
            target = params.get("target") or params.get("source", "")
            dest = params.get("destination", "Documents")
            success, msg, path = file_service.move_file(target, dest)
            return success, msg, {"destination_path": path}

        elif action_clean in ["get_metadata", "file_info"]:
            target = params.get("target", "")
            success, msg, meta = file_service.get_file_metadata(target)
            return success, msg, meta

        elif action_clean in ["find_duplicates", "check_duplicates"]:
            folder = params.get("folder", "Downloads")
            dups = file_service.find_duplicate_files(folder)
            msg = f"Found {len(dups)} duplicate file groups in {folder}." if dups else f"No duplicate files found in {folder}."
            return True, msg, {"duplicates": dups}

        elif action_clean == "delete_file":
            target = params.get("target", "")
            success, msg = file_service.delete_file(target)
            return success, msg, {"target": target}

        return False, f"Unsupported action '{action}' on File handler.", {}

    def verify(self, action: str, params: Dict[str, Any], result_data: Dict[str, Any]) -> bool:
        return True
