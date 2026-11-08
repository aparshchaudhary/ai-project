"""
Computer Vision Mode Service.
Handles on-demand desktop screen analysis, error detection, element location,
and visual understanding with local privacy preservation.
"""

from __future__ import annotations
import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

from backend.services.screenshot_service import screenshot_service
from backend.services.desktop_window_manager import desktop_window_manager, IS_WINDOWS

logger = logging.getLogger(__name__)


class VisionService:
    def __init__(self):
        self.is_vision_mode_active: bool = False

    def get_foreground_context(self) -> Dict[str, Any]:
        """Gathers active window title and process information."""
        context = {
            "title": "Unknown Window",
            "process": "unknown",
            "rect": None
        }
        if IS_WINDOWS:
            try:
                import win32gui
                import win32process
                import psutil
                hwnd = win32gui.GetForegroundWindow()
                if hwnd:
                    title = win32gui.GetWindowText(hwnd)
                    rect = win32gui.GetWindowRect(hwnd)
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    proc_name = "unknown"
                    try:
                        p = psutil.Process(pid)
                        proc_name = p.name()
                    except Exception:
                        pass
                    context = {
                        "hwnd": hwnd,
                        "title": title,
                        "process": proc_name,
                        "rect": rect
                    }
            except Exception as e:
                logger.debug(f"Foreground context inspection failed: {e}")
        return context

    def inspect_visible_elements(self) -> List[Dict[str, Any]]:
        """Inspects interactive elements (buttons, inputs) in the active foreground window."""
        elements = []
        if IS_WINDOWS:
            try:
                import pywinauto
                from pywinauto import Desktop
                fg = self.get_foreground_context()
                hwnd = fg.get("hwnd")
                if hwnd:
                    app = pywinauto.Application(backend="uia").connect(handle=hwnd, timeout=1.0)
                    top_win = app.top_window()
                    for ctrl in top_win.descendants():
                        try:
                            ctrl_type = ctrl.friendly_class_name()
                            txt = ctrl.window_text()
                            if txt and len(txt.strip()) > 0 and len(elements) < 30:
                                elements.append({
                                    "type": ctrl_type,
                                    "text": txt.strip(),
                                    "is_visible": ctrl.is_visible()
                                })
                        except Exception:
                            continue
            except Exception as e:
                logger.debug(f"UI element inspection skipped: {e}")
        return elements

    def analyze_screen(self, query: str = "Analyze my screen") -> Dict[str, Any]:
        """
        Executes on-demand screen capture and vision analysis.
        Strictly initiated on request; never continuous background surveillance.
        """
        success, msg, img_info = screenshot_service.take_screenshot()
        if not success or not img_info:
            return {
                "success": False,
                "error": f"Could not capture screen: {msg}",
                "summary": "Screen capture was not successful."
            }

        fg_info = self.get_foreground_context()
        active_title = fg_info.get("title", "Desktop")
        active_proc = fg_info.get("process", "System")
        elements = self.inspect_visible_elements()

        query_lower = query.lower()

        # 1. Error Detection & Explanation
        if any(w in query_lower for w in ["error", "explain this error", "issue", "bug"]):
            error_keywords = ["error", "exception", "failed", "warning", "denied", "traceback", "cannot", "invalid"]
            detected_errors = []
            for el in elements:
                t = el.get("text", "").lower()
                if any(k in t for k in error_keywords):
                    detected_errors.append(el.get("text"))

            if detected_errors:
                explanation = f"Detected error in '{active_title}': {detected_errors[0]}."
            elif any(k in active_title.lower() for k in error_keywords):
                explanation = f"Active window '{active_title}' reports an error or alert status."
            else:
                explanation = f"Inspected active window '{active_title}'. No critical blocking crash alerts detected in current foreground view."

            return {
                "success": True,
                "query": query,
                "analysis_type": "error_explanation",
                "active_window": active_title,
                "process": active_proc,
                "screenshot": img_info,
                "detected_errors": detected_errors,
                "summary": explanation,
                "interactive_elements_count": len(elements)
            }

        # 2. Button / Element Locator
        if any(w in query_lower for w in ["find the", "button", "locate", "where is"]):
            target_el = re.sub(r"\b(find the|find|locate|button|where is|on screen)\b", "", query_lower).strip()
            matches = [el for el in elements if target_el and target_el in el.get("text", "").lower()]
            if matches:
                summary = f"Located '{matches[0]['text']}' element in '{active_title}'."
            else:
                summary = f"Could not pinpoint exact element matching '{target_el}' in foreground window '{active_title}'."

            return {
                "success": True,
                "query": query,
                "analysis_type": "element_locator",
                "active_window": active_title,
                "target_searched": target_el,
                "matching_elements": matches,
                "screenshot": img_info,
                "summary": summary
            }

        # 3. General Screen Understanding
        el_texts = [e["text"] for e in elements[:10] if len(e.get("text", "")) > 2]
        elements_preview = ", ".join(el_texts[:5]) if el_texts else "general window controls"
        summary = (
            f"Currently focused on '{active_title}' ({active_proc}). "
            f"Identified {len(elements)} interactive interface elements including {elements_preview}."
        )

        return {
            "success": True,
            "query": query,
            "analysis_type": "screen_understanding",
            "active_window": active_title,
            "process": active_proc,
            "screenshot": img_info,
            "elements_sample": el_texts[:10],
            "summary": summary
        }


vision_service = VisionService()
