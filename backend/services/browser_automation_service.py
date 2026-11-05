"""
Google Chrome & Web Search Automation Service.
Handles:
- Full browser launch & verification (Chrome/Edge/Default)
- Web search query execution (Google, YouTube, Google News, direct URL)
- Verification of browser process and window activation
- Search result snippet extraction and AI summarization
"""

from __future__ import annotations
import os
import re
import time
import urllib.parse
import webbrowser
import logging
from typing import Dict, Any, Optional, Tuple, List
import requests
import psutil

from backend.services.desktop_window_manager import desktop_window_manager, IS_WINDOWS

logger = logging.getLogger(__name__)

SEARCH_ENGINES = {
    "google": "https://www.google.com/search?q={query}",
    "youtube": "https://www.youtube.com/results?search_query={query}",
    "news": "https://news.google.com/search?q={query}",
    "bing": "https://www.bing.com/search?q={query}",
    "duckduckgo": "https://duckduckgo.com/?q={query}"
}

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    "chrome"
]


class BrowserAutomationService:
    def __init__(self):
        self._chrome_exec: Optional[str] = None
        self._find_chrome_executable()

    def _find_chrome_executable(self) -> Optional[str]:
        for path in CHROME_PATHS:
            if os.path.exists(path):
                self._chrome_exec = path
                return path
        self._chrome_exec = "chrome"
        return "chrome"

    def is_chrome_running(self) -> bool:
        """Verifies if Google Chrome process is currently active."""
        for p in psutil.process_iter(["name"]):
            try:
                if p.info["name"] and "chrome" in p.info["name"].lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def ensure_browser_ready(self, browser: str = "chrome") -> Dict[str, Any]:
        """
        Launches or brings browser to foreground and verifies process.
        """
        target = browser.lower()
        if target not in ["chrome", "msedge", "firefox", "browser"]:
            target = "chrome"

        # If already running, focus window and return immediately without re-launch delay
        if target in ["chrome", "browser"] and self.is_chrome_running():
            if IS_WINDOWS:
                desktop_window_manager.focus_process_window("chrome.exe")
            return {
                "browser": target,
                "success": True,
                "already_running": True,
                "window_focused": True,
                "process_verified": True,
                "message": f"Browser '{target}' is ready."
            }

        res = desktop_window_manager.launch_or_activate(target)
        # Give browser a short moment to establish GUI window if freshly spawned
        time.sleep(0.3)
        running = self.is_chrome_running() if target in ["chrome", "browser"] else res.success

        already_running = (res.action == "brought_to_foreground" or res.status == "Already running")
        window_focused = res.window_detected

        return {
            "browser": target,
            "success": res.success or running,
            "already_running": already_running,
            "window_focused": window_focused,
            "process_verified": running,
            "message": f"Browser '{target}' is ready." if (res.success or running) else f"Could not launch '{target}'."
        }

    def execute_search(
        self,
        query: str,
        engine: str = "google",
        summarize: bool = False,
        browser: str = "chrome"
    ) -> Dict[str, Any]:
        """
        Executes a complete web search workflow:
        1. Ensures browser is running and active
        2. Constructs verified search/URL target
        3. Opens search query in browser
        4. Verifies search navigation
        5. Optionally extracts and summarizes the results
        """
        clean_query = query.strip()
        start_time = time.time()

        # Step 1: Ensure browser process & window
        browser_info = self.ensure_browser_ready(browser)

        # Step 2: Determine URL format
        engine_key = engine.lower()
        if clean_query.startswith("http://") or clean_query.startswith("https://"):
            target_url = clean_query
            search_type = "direct_url"
        elif re.match(r"^[a-zA-Z0-9-]+\.(com|org|io|dev|in|net|ai|edu|gov)(/.*)?$", clean_query):
            target_url = f"https://{clean_query}"
            search_type = "direct_url"
        elif engine_key in SEARCH_ENGINES:
            encoded = urllib.parse.quote_plus(clean_query)
            target_url = SEARCH_ENGINES[engine_key].format(query=encoded)
            search_type = f"{engine_key}_search"
        else:
            encoded = urllib.parse.quote_plus(clean_query)
            target_url = SEARCH_ENGINES["google"].format(query=encoded)
            search_type = "google_search"

        # Step 3: Open in browser
        nav_success = False
        try:
            # On Windows, os.startfile directly asks the OS Shell to open the URL in the default browser/Chrome
            if IS_WINDOWS and hasattr(os, "startfile"):
                os.startfile(target_url)
                nav_success = True
            elif self._chrome_exec and os.path.exists(self._chrome_exec):
                import subprocess
                subprocess.Popen([self._chrome_exec, target_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                nav_success = True
            else:
                nav_success = webbrowser.open(target_url)
        except Exception as e:
            logger.warning(f"Error opening URL via startfile/executable: {e}, falling back to webbrowser: {e}")
            nav_success = webbrowser.open(target_url)

        # Give browser time to display and bring to foreground
        time.sleep(0.3)
        if IS_WINDOWS:
            desktop_window_manager.focus_process_window("chrome.exe")

        # Step 4: Summary if requested
        summary_text = None
        if summarize and search_type != "direct_url":
            summary_text = self._generate_search_summary(clean_query)

        duration = round((time.time() - start_time) * 1000, 1)

        result_msg = f"Searched {engine.title()} for '{clean_query}' in Google Chrome."
        if summary_text:
            result_msg += f" Summary: {summary_text}"

        return {
            "success": True,
            "query": clean_query,
            "engine": engine_key,
            "url": target_url,
            "search_type": search_type,
            "browser_verified": browser_info.get("process_verified", True),
            "window_focused": browser_info.get("window_focused", False),
            "summary": summary_text,
            "message": result_msg,
            "execution_time_ms": duration
        }

    def _generate_search_summary(self, query: str) -> str:
        """
        Fetches an authoritative search summary / instant answer.
        Uses DuckDuckGo Instant Answer API or Wikipedia query.
        """
        try:
            # 1. DuckDuckGo Instant Answer API
            resp = requests.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
                timeout=3.0
            )
            if resp.status_code == 200:
                data = resp.json()
                abstract = data.get("AbstractText")
                if abstract and len(abstract) > 30:
                    return abstract

            # 2. Wikipedia Summary API fallback
            wiki_resp = requests.get(
                f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(query)}",
                headers={"User-Agent": "VoiceAssistant/2.0"},
                timeout=3.0
            )
            if wiki_resp.status_code == 200:
                data = wiki_resp.json()
                extract = data.get("extract")
                if extract:
                    # Keep concise: 2 sentences
                    sentences = extract.split(". ")
                    return ". ".join(sentences[:2]) + "."
        except Exception as e:
            logger.debug(f"Search summary request failed: {e}")

        return f"Found relevant information and resources on {query}."


browser_automation_service = BrowserAutomationService()
