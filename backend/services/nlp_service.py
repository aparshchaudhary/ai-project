"""
Natural Language Understanding (NLU) Service & Conversational Brain.
Performs Intent Classification, Entity Extraction, Confidence Scoring,
Context Awareness, Multilingual (English + Hindi/Hinglish) understanding,
and AI Conversational routing.
"""

from __future__ import annotations
import re
import json
import logging
from typing import Dict, Any, Optional, Tuple, List, Set
from datetime import datetime

from backend.config.settings import settings
from backend.models.schemas import IntentResult

logger = logging.getLogger(__name__)


class ConversationContext:
    def __init__(self):
        self.last_intent: Optional[str] = None
        self.last_entities: Dict[str, Any] = {}
        self.last_app: Optional[str] = None
        self.last_target_name: Optional[str] = None  # e.g. folder or file name
        self.last_action_type: Optional[str] = None
        self.pending_confirmation_id: Optional[str] = None
        self.recent_turns: List[Dict[str, str]] = []

    def update(self, intent: str, entities: Dict[str, Any], user_text: str, response_text: str):
        self.last_intent = intent
        self.last_entities = entities
        if "application" in entities:
            self.last_app = entities["application"]
        if "folder_name" in entities:
            self.last_target_name = entities["folder_name"]
            self.last_action_type = "folder"
        elif "file_name" in entities:
            self.last_target_name = entities["file_name"]
            self.last_action_type = "file"

        self.recent_turns.append({"user": user_text, "assistant": response_text})
        if len(self.recent_turns) > 10:
            self.recent_turns.pop(0)


class NLPService:
    def __init__(self):
        self.contexts: Dict[str, ConversationContext] = {}

    def get_context(self, session_id: str = "default") -> ConversationContext:
        if session_id not in self.contexts:
            self.contexts[session_id] = ConversationContext()
        return self.contexts[session_id]

    def _clean_text(self, raw_text: str) -> str:
        text = raw_text.strip().lower()
        text = text.replace("'", "").replace("’", "")
        clean = re.sub(r"[^\w\s\.:\-\/]", " ", text)
        return re.sub(r"\s+", " ", clean).strip()

    def parse_intent(self, raw_text: str, session_id: str = "default") -> IntentResult:
        if not raw_text or not raw_text.strip():
            return IntentResult(
                intent="help",
                confidence=0.5,
                response_text="I didn't catch that. How can I help you?",
                original_text=""
            )

        text = raw_text.strip()
        context = self.get_context(session_id)
        clean_text = self._clean_text(text)

        # 1. Contextual resolution (Follow-ups: "In Downloads", "Open it")
        contextual_intent = self._check_contextual_followup(clean_text, context)
        if contextual_intent:
            return contextual_intent

        # 2. Direct Social Greetings & Chit-Chat Check (English & Hindi)
        if self._is_greeting_or_social(clean_text):
            response = self._generate_conversational_response(text)
            return IntentResult(
                intent="conversation",
                entities={"query": text},
                confidence=0.98,
                requires_confirmation=False,
                risk_level="low",
                response_text=response,
                original_text=text,
                is_conversation=True
            )

        # 3. High Risk System Commands (Shutdown, Restart, Lock, Sleep)
        if any(w in clean_text for w in [
            "shutdown", "turn off the computer", "power off", "computer band karo",
            "band kar do pc", "pc band karo", "laptop band karo", "band kar do computer"
        ]):
            return IntentResult(
                intent="shutdown",
                entities={},
                confidence=0.98,
                requires_confirmation=True,
                risk_level="high",
                confirmation_prompt="Are you sure you want to shut down your computer?",
                original_text=text
            )

        if any(w in clean_text for w in [
            "restart the computer", "reboot computer", "restart my pc", "reboot",
            "computer restart karo", "pc restart karo", "system restart karo"
        ]):
            return IntentResult(
                intent="restart",
                entities={},
                confidence=0.98,
                requires_confirmation=True,
                risk_level="high",
                confirmation_prompt="Are you sure you want to restart your computer?",
                original_text=text
            )

        if any(w in clean_text for w in [
            "lock the computer", "lock screen", "lock my pc", "lock computer",
            "screen lock karo", "pc lock karo", "computer lock karo"
        ]):
            return IntentResult(
                intent="lock_screen",
                entities={},
                confidence=0.95,
                requires_confirmation=False,
                risk_level="medium",
                original_text=text
            )

        if any(w in clean_text for w in [
            "sleep computer", "put computer to sleep", "sleep mode",
            "pc sleep karo", "computer sleep karo"
        ]):
            return IntentResult(
                intent="sleep_computer",
                entities={},
                confidence=0.95,
                requires_confirmation=True,
                risk_level="high",
                confirmation_prompt="Do you want to put your computer into sleep mode?",
                original_text=text
            )

        # 4. Screenshot Capture
        if any(w in clean_text for w in [
            "take a screenshot", "screenshot", "capture my screen", "screen capture",
            "screenshot lo", "screenshot le lo", "ek screenshot lo", "screen shot",
            "screen ka photo lo", "screen capture karo"
        ]):
            return IntentResult(
                intent="take_screenshot",
                entities={},
                confidence=0.99,
                requires_confirmation=False,
                risk_level="low",
                original_text=text
            )

        # 5. Application Close (Prefix & Suffix in English & Hindi)
        close_suffix_m = re.search(r"^(.*?)\s+\b(band karo|band kar do|band kardo|close karo|close kardo|close kar do|hata do|hatao)\b", clean_text)
        close_prefix_m = re.search(r"\b(close|exit|terminate|kill|quit|band karo|band kardo)\b\s+(.*)", clean_text)

        if (close_suffix_m or close_prefix_m) and not any(w in clean_text for w in ["computer", "pc", "laptop", "music", "gaana", "tab", "window"]):
            raw_target = close_suffix_m.group(1).strip() if close_suffix_m else close_prefix_m.group(2).strip()
            app_clean = self._extract_app_name(raw_target)
            if app_clean and app_clean not in ["computer", "pc", "laptop"]:
                return IntentResult(
                    intent="close_application",
                    entities={"application": app_clean, "raw_target": raw_target},
                    confidence=0.97,
                    requires_confirmation=False,
                    risk_level="low",
                    original_text=text
                )

        # 6. Application Open & Launch (Prefix & Suffix in English & Hindi)
        open_suffix_m = re.search(r"^(.*?)\s+\b(open karo|open kardo|open kar do|kholo|chalu karo|chalu kardo|start karo|launch karo)\b", clean_text)
        open_prefix_m = re.search(r"\b(open|launch|start|run|kholo|chalu karo)\b\s+(.*)", clean_text)

        target_app_phrase = None
        if open_suffix_m:
            target_app_phrase = open_suffix_m.group(1).strip()
        elif open_prefix_m:
            target_app_phrase = open_prefix_m.group(2).strip()

        if target_app_phrase and not any(w in target_app_phrase for w in ["file called", "folder called", "screenshot", "weather", "music", "gaana"]):
            # Folder check
            if any(p in target_app_phrase for p in ["downloads", "documents", "desktop", "my files", "explorer"]):
                folder = "downloads" if "download" in target_app_phrase else ("documents" if "document" in target_app_phrase else "desktop")
                return IntentResult(
                    intent="open_file",
                    entities={"file_path": folder, "is_folder": True},
                    confidence=0.95,
                    risk_level="low",
                    original_text=text
                )
            elif "folder" in target_app_phrase:
                f_name = target_app_phrase.replace("folder", "").replace("the", "").replace("my", "").strip()
                return IntentResult(
                    intent="open_file",
                    entities={"file_path": f_name, "is_folder": True},
                    confidence=0.92,
                    risk_level="low",
                    original_text=text
                )
            # Website check
            elif any(s in target_app_phrase for s in ["youtube", "gmail", "github", "wikipedia", "reddit", "twitter", "linkedin"]):
                site = re.findall(r"(youtube|gmail|github|wikipedia|reddit|twitter|linkedin)", target_app_phrase)[0]
                return IntentResult(
                    intent="open_website",
                    entities={"site_name": site, "url": f"https://www.{site}.com"},
                    confidence=0.97,
                    requires_confirmation=False,
                    risk_level="low",
                    original_text=text
                )
            else:
                app_name = self._extract_app_name(target_app_phrase)
                if app_name:
                    return IntentResult(
                        intent="open_application",
                        entities={"application": app_name, "raw_app": target_app_phrase},
                        confidence=0.97,
                        requires_confirmation=False,
                        risk_level="low",
                        original_text=text
                    )

        # 7. Popular Website Direct Opening
        website_match = re.search(r"\b(open|visit|go to)\b\s+(youtube|gmail|google|github|wikipedia|reddit|twitter|linkedin)\b", clean_text)
        if website_match:
            site = website_match.group(2)
            return IntentResult(
                intent="open_website",
                entities={"site_name": site, "url": f"https://www.{site}.com"},
                confidence=0.97,
                requires_confirmation=False,
                risk_level="low",
                original_text=text
            )

        # 8. Web Search (Google, YouTube, Wikipedia in English & Hindi)
        is_search_intent = False
        if any(w in clean_text for w in ["search", "dhoondo", "khojo"]):
            is_search_intent = True
        elif any(clean_text.startswith(w) for w in ["google ", "youtube ", "wikipedia "]):
            is_search_intent = True

        if is_search_intent:
            search_query, search_engine = self._extract_search_entities(clean_text)
            if search_query:
                return IntentResult(
                    intent="search_web",
                    entities={"query": search_query, "engine": search_engine},
                    confidence=0.96,
                    requires_confirmation=False,
                    risk_level="low",
                    original_text=text
                )

        # 9. Time, Date, and Day Queries (English & Hindi)
        time_triggers = [
            "what time is it", "what is the time", "tell me the time", "current time",
            "what's the time", "time right now", "time kya hai", "time batao",
            "samay kya hai", "samay batao", "kitne baje", "kya samay hua",
            "kya time hua", "waqt kya hua", "kitna time ho gaya", "the time"
        ]
        if any(w in clean_text for w in time_triggers) and not any(w in clean_text for w in ["date", "tarikh", "din"]):
            return IntentResult(
                intent="get_time",
                entities={},
                confidence=0.99,
                risk_level="low",
                original_text=text
            )

        date_triggers = [
            "what is todays date", "whats todays date", "what is the date", "tell me the date",
            "tell me todays date", "todays date", "today date", "what date is it", "tarikh kya hai", "tarikh batao",
            "aaj ki tarikh", "aaj kya tarikh hai", "date batao", "aaj konsi date hai", "date kya hai",
            "date", "tarikh"
        ]
        if any(w in clean_text for w in date_triggers) and not any(w in clean_text for w in ["update", "candidate", "validate"]):
            return IntentResult(
                intent="get_date",
                entities={},
                confidence=0.99,
                risk_level="low",
                original_text=text
            )

        day_triggers = [
            "what day is today", "what day is it", "which day is today", "aaj kya din hai",
            "aaj konsa din hai", "aaj ka din", "din batao", "aaj kon sa din hai"
        ]
        if any(w in clean_text for w in day_triggers):
            return IntentResult(
                intent="get_date",
                entities={"query_day": True},
                confidence=0.99,
                risk_level="low",
                original_text=text
            )

        # 10. Weather & Temperature (English & Hindi)
        if any(w in clean_text for w in ["weather", "temperature", "forecast", "mausam"]):
            city = None
            city_match = re.search(r"\b(in|for|at|me|ka)\b\s+([a-zA-Z\s]+)", clean_text)
            if city_match:
                city = city_match.group(2).replace("today", "").replace("mausam", "").replace("kaisa hai", "").strip()
            return IntentResult(
                intent="weather",
                entities={"city": city or "local"},
                confidence=0.96,
                risk_level="low",
                original_text=text
            )

        # 11. Music & Audio Playback (English & Hindi)
        if any(w in clean_text for w in [
            "play music", "play some music", "play a song", "play songs", "play track",
            "gaana bajao", "gaana chalao", "gaana sunao", "music bajao", "music chalao",
            "song bajao", "song chalao", "gaana play karo", "music play karo", "kuch gaana bajao"
        ]):
            return IntentResult(
                intent="play_music",
                entities={},
                confidence=0.97,
                risk_level="low",
                original_text=text
            )

        if any(w in clean_text for w in [
            "pause music", "stop music", "pause song", "stop song", "resume music",
            "gaana roko", "gaana band karo", "music band karo", "music roko",
            "gaana pause karo", "music pause karo"
        ]):
            return IntentResult(
                intent="pause_music",
                entities={},
                confidence=0.97,
                risk_level="low",
                original_text=text
            )

        if any(w in clean_text for w in ["next song", "next track", "skip song", "agla gaana", "next"]):
            return IntentResult(
                intent="next_track",
                entities={},
                confidence=0.96,
                risk_level="low",
                original_text=text
            )

        if any(w in clean_text for w in ["previous song", "previous track", "pichla gaana"]):
            return IntentResult(
                intent="previous_track",
                entities={},
                confidence=0.96,
                risk_level="low",
                original_text=text
            )

        if any(w in clean_text for w in ["volume", "awaz", "mute", "unmute", "silent"]):
            action = "up"
            if any(w in clean_text for w in ["down", "lower", "decrease", "kam"]):
                action = "down"
            elif any(w in clean_text for w in ["mute", "silent", "band"]):
                action = "mute"
            elif any(w in clean_text for w in ["unmute", "chalu"]):
                action = "unmute"
            elif any(w in clean_text for w in ["up", "higher", "increase", "badhao", "tez"]):
                action = "up"
            return IntentResult(
                intent="volume_control",
                entities={"action": action},
                confidence=0.97,
                risk_level="low",
                original_text=text
            )

        # 12. Reminders (English & Hindi)
        if any(w in clean_text for w in [
            "show reminders", "list reminders", "what are my reminders", "get reminders",
            "reminders dikhao", "mere reminders", "reminders batao"
        ]):
            return IntentResult(
                intent="list_reminders",
                entities={},
                confidence=0.98,
                risk_level="low",
                original_text=text
            )

        if any(w in clean_text for w in [
            "remind me", "set a reminder", "create reminder", "reminder lagao",
            "reminder set karo", "yaad dilana"
        ]):
            title, due_time_str = self._extract_reminder_entities(clean_text)
            return IntentResult(
                intent="set_reminder",
                entities={"title": title, "time_str": due_time_str},
                confidence=0.94,
                requires_confirmation=False,
                risk_level="low",
                original_text=text
            )

        # 13. File & Folder Operations (English & Hindi)
        if any(clean_text.startswith(w) for w in ["delete ", "remove ", "delete file ", "delete permanently ", "hatao "]) or "file delete karo" in clean_text:
            file_name = clean_text.replace("delete file", "").replace("delete", "").replace("remove", "").replace("hatao", "").replace("file delete karo", "").strip(" '\"")
            return IntentResult(
                intent="delete_file",
                entities={"file_name": file_name},
                confidence=0.93,
                requires_confirmation=True,
                risk_level="high",
                confirmation_prompt=f"Are you sure you want to permanently delete '{file_name}'?",
                original_text=text
            )

        if any(w in clean_text for w in ["create a folder", "make a folder", "create folder", "folder banao", "ek folder banao"]):
            raw_name = clean_text
            for prefix in ["create a folder called", "create a folder named", "create folder called", "create folder named", "create folder", "make a folder called", "folder banao", "ek folder banao"]:
                if prefix in raw_name:
                    raw_name = raw_name.split(prefix)[-1].strip()
                    break
            raw_name = re.sub(r"\b(naam se|naam ka|called|named)\b", "", raw_name).strip()
            folder_name = raw_name.title() if raw_name else "New Folder"
            return IntentResult(
                intent="create_folder",
                entities={"folder_name": folder_name, "parent_folder": "Documents"},
                confidence=0.95,
                requires_confirmation=False,
                risk_level="medium",
                original_text=text
            )

        if any(w in clean_text for w in ["create a file", "make a file", "create file", "file banao", "ek file banao"]):
            raw_name = clean_text
            for prefix in ["create a file called", "create a file named", "create file called", "create file named", "create file", "file banao", "ek file banao"]:
                if prefix in raw_name:
                    raw_name = raw_name.split(prefix)[-1].strip()
                    break
            raw_name = re.sub(r"\b(naam se|naam ki|called|named)\b", "", raw_name).strip()
            file_name = raw_name if raw_name else "notes.txt"
            if not "." in file_name:
                file_name += ".txt"
            return IntentResult(
                intent="create_file",
                entities={"file_name": file_name, "content": ""},
                confidence=0.94,
                requires_confirmation=False,
                risk_level="medium",
                original_text=text
            )

        if any(w in clean_text for w in ["find my", "search my computer", "search for pdf", "where is my", "find file", "file search", "dhoondo", "khojo"]):
            query, ext = self._extract_file_search_entities(clean_text)
            return IntentResult(
                intent="file_search",
                entities={"query": query, "extension": ext},
                confidence=0.93,
                requires_confirmation=False,
                risk_level="low",
                original_text=text
            )

        # 14. System Telemetry & Hardware Health
        if any(w in clean_text for w in [
            "system information", "system info", "cpu usage", "ram usage", "memory usage",
            "disk usage", "battery percentage", "battery status", "how much ram", "os info",
            "system status", "computer status", "cpu kitna", "battery kitni", "status batao"
        ]):
            metric = "all"
            if "cpu" in clean_text:
                metric = "cpu"
            elif "ram" in clean_text or "memory" in clean_text:
                metric = "memory"
            elif "disk" in clean_text:
                metric = "disk"
            elif "battery" in clean_text:
                metric = "battery"

            return IntentResult(
                intent="system_information",
                entities={"metric": metric},
                confidence=0.97,
                requires_confirmation=False,
                risk_level="low",
                original_text=text
            )

        # 15. Clipboard Operations
        if "clipboard" in clean_text:
            if any(w in clean_text for w in ["read", "what is on", "check", "padho"]):
                return IntentResult(
                    intent="clipboard_read",
                    entities={},
                    confidence=0.98,
                    risk_level="low",
                    original_text=text
                )
            elif any(w in clean_text for w in ["clear", "empty", "saaf"]):
                return IntentResult(
                    intent="clipboard_clear",
                    entities={},
                    confidence=0.98,
                    risk_level="medium",
                    original_text=text
                )
            elif any(w in clean_text for w in ["copy", "write", "likho"]):
                text_to_copy = clean_text.replace("copy to clipboard", "").replace("copy this text", "").strip()
                return IntentResult(
                    intent="clipboard_write",
                    entities={"text": text_to_copy},
                    confidence=0.95,
                    risk_level="medium",
                    original_text=text
                )

        # 16. Command History
        if any(w in clean_text for w in [
            "what commands did i use", "show history", "command history",
            "my past commands", "recent commands", "history dikhao"
        ]):
            return IntentResult(
                intent="show_history",
                entities={},
                confidence=0.96,
                risk_level="low",
                original_text=text
            )

        # 17. Help & Capabilities Guide
        if any(w in clean_text for w in ["help", "what can you do", "commands list", "madad", "help me", "tum kya kar sakte ho", "features kya hain"]):
            return IntentResult(
                intent="help",
                entities={},
                confidence=0.98,
                risk_level="low",
                original_text=text
            )

        # 18. Default Fallback -> Intelligent Conversational Brain
        ai_resp = self._generate_conversational_response(text)
        return IntentResult(
            intent="conversation",
            entities={"query": text},
            confidence=0.90,
            requires_confirmation=False,
            risk_level="low",
            response_text=ai_resp,
            original_text=text,
            is_conversation=True
        )

    def _is_greeting_or_social(self, text: str) -> bool:
        greetings = [
            "hello", "hi", "hey", "hey assistant", "hello aura", "namaste", "pranam",
            "sat sri akal", "adaab", "ram ram", "how are you", "kaise ho", "kya haal hai",
            "kya chal raha hai", "how are you doing", "sab theek", "sab badhiya",
            "good morning", "good afternoon", "good evening", "good night", "shubh prabhat",
            "thank you", "thanks", "dhanyawad", "shukriya", "bye", "goodbye", "alvida",
            "who are you", "what is your name", "tum kaun ho", "tumhara naam kya hai",
            "who created you", "who made you", "tumhe kisne banaya", "tell me a joke",
            "joke sunao", "chutkula sunao"
        ]
        return any(text == g or text.startswith(g + " ") for g in greetings)

    def _check_contextual_followup(self, clean_text: str, context: ConversationContext) -> Optional[IntentResult]:
        """Resolves follow-up commands based on previous conversation turn."""
        if clean_text.startswith("in ") or clean_text.startswith("inside "):
            loc = clean_text.replace("in ", "").replace("inside ", "").strip()
            if context.last_intent in ["create_folder", "create_file"] and context.last_target_name:
                parent = "Downloads" if "download" in loc else ("Documents" if "document" in loc else ("Desktop" if "desktop" in loc else loc))
                if context.last_action_type == "folder":
                    return IntentResult(
                        intent="create_folder",
                        entities={"folder_name": context.last_target_name, "parent_folder": parent},
                        confidence=0.96,
                        risk_level="medium",
                        original_text=clean_text
                    )
                else:
                    return IntentResult(
                        intent="create_file",
                        entities={"file_name": context.last_target_name, "parent_folder": parent, "content": ""},
                        confidence=0.96,
                        risk_level="medium",
                        original_text=clean_text
                    )

        if clean_text in ["open it", "open that", "isse kholo"] and context.last_target_name:
            return IntentResult(
                intent="open_file",
                entities={"file_path": context.last_target_name},
                confidence=0.94,
                risk_level="low",
                original_text=clean_text
            )

        return None

    def _extract_app_name(self, phrase: str) -> str:
        clean = re.sub(
            r"\b(open|kholo|chalu|start|launch|run|close|band|karo|kar|do|kardo|the|application|app|please|can|you|zara)\b",
            "",
            phrase.lower(),
            flags=re.IGNORECASE
        ).strip()

        # If candidate contains conjunctions or action words (e.g. "search", "what is"), don't treat the entire phrase as an application
        if any(w in clean for w in ["search", "dhoondo", "dhoondho", "khojo", "what is", "send", "message", "bhejo"]):
            app_sub = re.match(
                r"^([a-zA-Z0-9\s]+?)\s*(?:\b(?:and\s+then|then|after\s+that|and|an|&|aur|phir)\b|,|\s)\s*(?:search|what|send|message|dhoondo|dhoondho|khojo)\b",
                clean
            )
            if app_sub:
                clean = app_sub.group(1).strip()
            else:
                for k in ["chrome", "whatsapp", "notepad", "calculator", "explorer", "spotify", "code"]:
                    if k in clean:
                        return k
                return ""

        mapping = {
            "whatsapp": "whatsapp",
            "whats app": "whatsapp",
            "wa": "whatsapp",
            "chrome": "chrome",
            "google chrome": "chrome",
            "browser": "chrome",
            "edge": "msedge",
            "microsoft edge": "msedge",
            "msedge": "msedge",
            "firefox": "firefox",
            "mozilla firefox": "firefox",
            "vscode": "code",
            "vs code": "code",
            "visual studio code": "code",
            "code": "code",
            "notepad": "notepad",
            "calc": "calculator",
            "calculator": "calculator",
            "explorer": "explorer",
            "file explorer": "explorer",
            "my files": "explorer",
            "files": "explorer",
            "terminal": "wt",
            "cmd": "cmd",
            "command prompt": "cmd",
            "powershell": "powershell",
            "spotify": "spotify",
            "discord": "discord",
            "settings": "settings",
            "task manager": "taskmgr",
            "taskmgr": "taskmgr",
            "word": "winword",
            "ms word": "winword",
            "excel": "excel",
            "ms excel": "excel",
            "powerpoint": "powerpnt",
            "paint": "mspaint",
        }
        return mapping.get(clean, clean)

    def _extract_search_entities(self, text: str) -> Tuple[str, str]:
        engine = "google"
        clean = text.lower()
        if "youtube" in clean:
            engine = "youtube"
        elif "wikipedia" in clean:
            engine = "wikipedia"
        elif "bing" in clean:
            engine = "bing"
        elif "github" in clean:
            engine = "github"

        clean = re.sub(
            r"\b(search\s+for|search\s+on|search|google\s+par|google\s+pe|youtube\s+par|youtube\s+pe|wikipedia\s+par|google|youtube|wikipedia|on|for|par|pe|dhoondo|khojo|search\s+karo|karo)\b",
            " ",
            clean
        )
        query = re.sub(r"\s+", " ", clean).strip()
        return (query if query else "latest updates", engine)

    def _extract_reminder_entities(self, text: str) -> Tuple[str, str]:
        title = "Important task"
        time_str = "in 1 hour"

        at_match = re.search(r"\b(at|in|on)\b\s+([0-9]+(?::[0-9]+)?\s*(?:am|pm|hours?|minutes?|mins?)?|\b[a-zA-Z0-9\s]+)", text)
        if at_match:
            time_str = at_match.group(2).strip()

        to_match = re.search(r"\bto\s+(.*?)(?:\s+at|\s+in|\s+tomorrow|$)", text)
        if to_match:
            title = to_match.group(1).strip()
        else:
            words = text.replace("remind me", "").replace("set a reminder", "").replace(f"at {time_str}", "").strip()
            if words:
                title = words

        return (title.capitalize(), time_str)

    def _extract_file_search_entities(self, text: str) -> Tuple[str, Optional[str]]:
        ext = None
        if "pdf" in text:
            ext = ".pdf"
        elif "python" in text or "py files" in text or ".py" in text:
            ext = ".py"
        elif "word" in text or "doc" in text or ".docx" in text:
            ext = ".docx"
        elif "excel" in text or "sheet" in text or ".xlsx" in text:
            ext = ".xlsx"
        elif "image" in text or "picture" in text or "photo" in text or ".png" in text or ".jpg" in text:
            ext = ".png"

        query = re.sub(
            r"\b(find\s+my|find\s+all|search\s+my\s+computer\s+for|search\s+for|where\s+is\s+my|find\s+file|find|dhoondo|khojo|files?)\b",
            " ",
            text
        )
        query = re.sub(r"\s+", " ", query).strip()
        return (query, ext)

    def _generate_conversational_response(self, text: str) -> str:
        """Intelligent offline brain with multilingual greetings and knowledge, plus OpenAI LLM routing."""
        lower = text.lower().strip()

        # 1. Check OpenAI API if configured
        if settings.openai_api_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=settings.openai_api_key)
                completion = client.chat.completions.create(
                    model=settings.openai_model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are Aura, an intelligent, helpful, and privacy-conscious AI desktop voice assistant. "
                                "Keep your replies concise, warm, natural, and direct (2-3 sentences max for spoken output). "
                                "You understand and can respond fluently in English, Hindi, and Hinglish."
                            )
                        },
                        {"role": "user", "content": text}
                    ],
                    max_tokens=150
                )
                return completion.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"OpenAI completion error: {e}")

        # 2. Comprehensive Built-in Offline Conversational Brain
        # A. Greetings
        if any(lower == g or lower.startswith(g + " ") for g in ["namaste", "pranam", "sat sri akal", "adaab", "ram ram"]):
            return "Namaste! Main Aura hoon, aapka desktop voice assistant. Aaj main aapki kya madad kar sakta hoon?"
        elif any(lower == g or lower.startswith(g + " ") for g in ["hello", "hi", "hey", "hey assistant", "hello aura", "hie"]):
            return "Hello! I am Aura, your AI desktop assistant. Ready to help you with apps, searches, or questions!"
        elif "good morning" in lower or "shubh prabhat" in lower:
            return "Good morning! Wishing you a very productive and energetic day ahead. How can I help you get started?"
        elif "good afternoon" in lower:
            return "Good afternoon! Hope your day is going well. What task can I assist you with?"
        elif "good evening" in lower:
            return "Good evening! How can I assist you tonight?"
        elif "good night" in lower or "shubh ratri" in lower:
            return "Good night! Rest well, and let me know whenever you need my assistance tomorrow."

        # B. Well-being & Social
        elif any(w in lower for w in ["how are you", "kaise ho", "kya haal hai", "how are you doing", "kya chal raha hai"]):
            return "Main bilkul badhiya aur active hoon! I'm doing great and all systems are running smoothly. What can I do for you?"
        elif any(w in lower for w in ["sab theek", "sab badhiya", "all good"]):
            return "Haan bilkul, sab first-class hai! Aap bataiye, kya kaam shuru karein?"

        # C. Gratitude & Courtesy
        elif any(w in lower for w in ["thank you", "thanks", "dhanyawad", "shukriya", "bahut shukriya"]):
            return "You're most welcome! Glad I could help. Aapka swagat hai!"
        elif any(w in lower for w in ["bye", "goodbye", "alvida", "see you", "phir milenge", "tata"]):
            return "Goodbye! Have a great time ahead, and feel free to call me anytime you need assistance."

        # D. Identity & Creator
        elif any(w in lower for w in ["who are you", "tum kaun ho", "what is your name", "tumhara naam kya hai", "apna parichay"]):
            return f"I am {settings.app_name}, an advanced AI-powered desktop voice assistant designed to help automate tasks, manage apps, search information, and boost your daily workflow."
        elif any(w in lower for w in ["who made you", "who created you", "tumhe kisne banaya", "kiska project"]):
            return "I was created as an intelligent, secure, privacy-first desktop voice assistant powered by Python, FastAPI, and React."
        elif any(w in lower for w in ["what can you do", "tum kya kar sakte ho", "features kya hain"]):
            return "I can launch and close applications, search Google and YouTube, capture screenshots, check system telemetry and weather, manage reminders, and chat in both English and Hindi."

        # E. Fun & Entertainment
        elif "joke" in lower or "chutkula" in lower or "hasi" in lower:
            jokes = [
                "Why do programmers prefer dark mode? Because light attracts bugs!",
                "Ek programmer doosre se bola: Meri life loop mein phas gayi hai, break condition mil hi nahi rahi!",
                "There are 10 types of people in the world: those who understand binary, and those who don't."
            ]
            import random
            return random.choice(jokes)
        elif "motivation" in lower or "quote" in lower:
            return "Success is not final, failure is not fatal: it is the courage to continue that counts. Keep pushing forward!"

        # F. Core Technical & AI Concepts
        elif "machine learning" in lower:
            return "Machine Learning is a subset of AI where systems learn patterns from past data to make accurate predictions or decisions without being explicitly programmed."
        elif "deep learning" in lower:
            return "Deep Learning uses multi-layered artificial neural networks inspired by the human brain to process complex patterns such as images, voice, and text."
        elif "artificial intelligence" in lower or lower == "what is ai" or "ai kya hai" in lower:
            return "Artificial Intelligence refers to computer systems engineered to simulate human intelligence, including learning, reasoning, natural speech perception, and problem-solving."
        elif "generative ai" in lower or "llm" in lower or "chatgpt" in lower:
            return "Generative AI and Large Language Models are advanced deep learning models trained on vast text corpora to generate human-like conversations, code, and creative content."
        elif "python" in lower:
            return "Python is a high-level, interpreted programming language celebrated for its readable syntax, vast libraries, and dominance in artificial intelligence, backend systems, and data science."
        elif "react" in lower:
            return "React is a popular open-source JavaScript library developed by Meta for building responsive, component-based user interfaces."
        elif "cloud computing" in lower:
            return "Cloud Computing delivers on-demand computing services—including servers, storage, databases, networking, and software—over the internet with pay-as-you-go pricing."
        elif "cyber security" in lower:
            return "Cyber Security is the practice of defending computers, servers, mobile devices, electronic systems, networks, and sensitive data from malicious digital attacks."
        elif "quantum computing" in lower:
            return "Quantum Computing harnesses the principles of quantum mechanics, like superposition and entanglement, to solve complex mathematical problems exponentially faster than classical computers."
        elif "interview" in lower:
            return "To prepare for your interview: practice fundamental technical concepts, use the STAR technique (Situation, Task, Action, Result) for behavioral questions, and review your past projects thoroughly."

        # G. General Facts
        elif "capital of india" in lower or "bharat ki rajdhani" in lower:
            return "The capital of India is New Delhi."
        elif "prime minister of india" in lower or "bharat ke pradhan mantri" in lower:
            return "The Prime Minister of India is Narendra Modi."
        elif "capital of france" in lower:
            return "The capital of France is Paris."

        # H. Intelligent Conversational Fallback with Search Recommendation
        else:
            return f"That's an interesting question about '{text}'. You can ask me to search Google or YouTube for in-depth details, or let me know what else you'd like to explore!"


nlp_service = NLPService()
