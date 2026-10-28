"""
Natural Language Understanding (NLU) Service.
Performs Intent Classification, Entity Extraction, Confidence Scoring,
Context Awareness, Multilingual (English + Hindi) understanding,
and AI Conversational routing.
"""

import re
import json
import logging
from typing import Dict, Any, Optional, Tuple, List
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
        lower = text.lower()

        # Clean punctuation
        clean_text = re.sub(r"[^\w\s\.:\-\/]", "", lower).strip()

        # 1. Contextual resolution (e.g., Follow-up: "In Downloads", "Open it")
        contextual_intent = self._check_contextual_followup(clean_text, context)
        if contextual_intent:
            return contextual_intent

        # 2. Check for Conversational / Educational questions first if clearly conversational
        if self._is_open_ended_conversation(clean_text):
            response = self._generate_conversational_response(text)
            return IntentResult(
                intent="conversation",
                entities={"query": text},
                confidence=0.95,
                requires_confirmation=False,
                risk_level="low",
                response_text=response,
                original_text=text,
                is_conversation=True
            )

        # 3. High Risk System Commands (Shutdown, Restart, Lock, Sleep)
        if any(w in clean_text for w in ["shutdown", "turn off the computer", "power off", "computer band karo", "band kar do"]):
            return IntentResult(
                intent="shutdown",
                entities={},
                confidence=0.98,
                requires_confirmation=True,
                risk_level="high",
                confirmation_prompt="Are you sure you want to shut down your computer?",
                original_text=text
            )

        if any(w in clean_text for w in ["restart the computer", "reboot computer", "restart my pc", "reboot", "computer restart karo"]):
            return IntentResult(
                intent="restart",
                entities={},
                confidence=0.98,
                requires_confirmation=True,
                risk_level="high",
                confirmation_prompt="Are you sure you want to restart your computer?",
                original_text=text
            )

        if any(w in clean_text for w in ["lock the computer", "lock screen", "lock my pc", "lock computer", "screen lock karo"]):
            return IntentResult(
                intent="lock_screen",
                entities={},
                confidence=0.95,
                requires_confirmation=False,
                risk_level="medium",
                original_text=text
            )

        if any(w in clean_text for w in ["sleep computer", "put computer to sleep", "sleep mode"]):
            return IntentResult(
                intent="sleep_computer",
                entities={},
                confidence=0.95,
                requires_confirmation=True,
                risk_level="high",
                confirmation_prompt="Do you want to put your computer into sleep mode?",
                original_text=text
            )

        # 4. Screenshot
        if any(w in clean_text for w in ["take a screenshot", "screenshot", "capture my screen", "screen capture", "screenshot lo", "screen shot"]):
            return IntentResult(
                intent="take_screenshot",
                entities={},
                confidence=0.99,
                requires_confirmation=False,
                risk_level="low",
                original_text=text
            )

        # 5. Application Launch & Close
        # Close Application
        close_match = re.search(r"\b(close|exit|terminate|kill|band karo)\b\s+(.*)", clean_text)
        if close_match and not ("tab" in clean_text or "window" in clean_text and len(clean_text.split()) == 2):
            app_target = close_match.group(2).strip()
            # Normalize app name
            app_clean = self._extract_app_name(app_target)
            return IntentResult(
                intent="close_application",
                entities={"application": app_clean, "raw_target": app_target},
                confidence=0.96,
                requires_confirmation=False,
                risk_level="low",
                original_text=text
            )

        # Open Application (English & Hindi)
        # Patterns: "open chrome", "launch vs code", "start my browser", "chrome kholo", "open application notepad"
        open_match = re.search(r"\b(open|launch|start|run|kholo|chalu karo)\b\s+(.*)", clean_text)
        hindi_kholo_match = re.search(r"(.*)\s+(kholo|chalu karo)\b", clean_text)

        target_app_phrase = None
        if open_match:
            target_app_phrase = open_match.group(2).strip()
        elif hindi_kholo_match:
            target_app_phrase = hindi_kholo_match.group(1).strip()

        if target_app_phrase:
            # Check if it's a website or folder instead of app
            if any(target_app_phrase.startswith(p) for p in ["my downloads", "downloads folder", "my documents", "desktop"]):
                folder = "downloads" if "download" in target_app_phrase else ("documents" if "document" in target_app_phrase else "desktop")
                return IntentResult(
                    intent="open_file",
                    entities={"file_path": folder, "is_folder": True},
                    confidence=0.94,
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
            else:
                app_name = self._extract_app_name(target_app_phrase)
                return IntentResult(
                    intent="open_application",
                    entities={"application": app_name, "raw_app": target_app_phrase},
                    confidence=0.97,
                    requires_confirmation=False,
                    risk_level="low",
                    original_text=text
                )

        # 6. Web Search & Websites
        # "search google for python", "search for python tutorials", "search youtube for music", "open youtube"
        if clean_text.startswith("search ") or "search for " in clean_text or "google " in clean_text:
            query, engine = self._extract_search_entities(clean_text)
            return IntentResult(
                intent="search_web",
                entities={"query": query, "engine": engine},
                confidence=0.96,
                requires_confirmation=False,
                risk_level="low",
                original_text=text
            )

        # Open specific popular websites
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

        # 7. Reminders
        if any(w in clean_text for w in ["remind me", "set a reminder", "create reminder", "reminder set karo"]):
            title, due_time_str = self._extract_reminder_entities(clean_text)
            return IntentResult(
                intent="set_reminder",
                entities={"title": title, "time_str": due_time_str},
                confidence=0.94,
                requires_confirmation=False,
                risk_level="low",
                original_text=text
            )

        if any(w in clean_text for w in ["show reminders", "list reminders", "what are my reminders", "get reminders", "reminders dikhao"]):
            return IntentResult(
                intent="list_reminders",
                entities={},
                confidence=0.98,
                risk_level="low",
                original_text=text
            )

        # 8. File & Folder Operations
        # Delete file (High Risk)
        if any(clean_text.startswith(w) for w in ["delete ", "remove ", "delete file ", "delete permanently ", "hatao "]):
            file_name = clean_text.replace("delete file", "").replace("delete", "").replace("remove", "").replace("hatao", "").strip(" '\"")
            return IntentResult(
                intent="delete_file",
                entities={"file_name": file_name},
                confidence=0.93,
                requires_confirmation=True,
                risk_level="high",
                confirmation_prompt=f"Are you sure you want to permanently delete '{file_name}'?",
                original_text=text
            )

        # Create Folder
        create_folder_match = re.search(r"\b(create|make|banao)\b.*?\bfolder\b.*?\b(?:called|named|name)?\s*(.*)", clean_text)
        if create_folder_match:
            raw_name = create_folder_match.group(2).strip()
            raw_name = re.sub(r"^(called|named|name)\s+", "", raw_name, flags=re.IGNORECASE).strip()
            folder_name = raw_name if raw_name else "New Folder"
            return IntentResult(
                intent="create_folder",
                entities={"folder_name": folder_name.title(), "parent_folder": "Documents"},
                confidence=0.95,
                requires_confirmation=False,
                risk_level="medium",
                original_text=text
            )

        # Create File
        create_file_match = re.search(r"\b(create|make|write)\b.*?\bfile\b.*?\b(?:called|named|name)?\s*(.*)", clean_text)
        if create_file_match:
            raw_name = create_file_match.group(2).strip()
            raw_name = re.sub(r"^(called|named|name)\s+", "", raw_name, flags=re.IGNORECASE).strip()
            file_name = raw_name if raw_name else "notes.txt"
            return IntentResult(
                intent="create_file",
                entities={"file_name": file_name, "content": ""},
                confidence=0.93,
                requires_confirmation=False,
                risk_level="medium",
                original_text=text
            )

        # Search Files
        if any(w in clean_text for w in ["find my", "search my computer", "search for pdf", "where is my", "find file", "file search"]):
            query, ext = self._extract_file_search_entities(clean_text)
            return IntentResult(
                intent="file_search",
                entities={"query": query, "extension": ext},
                confidence=0.92,
                requires_confirmation=False,
                risk_level="low",
                original_text=text
            )

        # 9. System Information & Health
        if any(w in clean_text for w in [
            "system information", "system info", "cpu usage", "ram usage", "memory usage",
            "disk usage", "battery percentage", "battery status", "how much ram", "os info",
            "system status", "computer status"
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

        # 10. Time & Date
        if any(w in clean_text for w in ["what time is it", "current time", "tell me the time", "what is the time", "kitne baje", "samay kya hai", "what time", "the time"]):
            if "date" not in clean_text:
                return IntentResult(
                    intent="get_time",
                    entities={},
                    confidence=0.99,
                    risk_level="low",
                    original_text=text
                )

        if any(w in clean_text for w in [
            "what's today's date", "what is today's date", "tell me today's date", "tell me todays date",
            "what date is it", "aaj ki tarikh", "today's date", "todays date", "today date", "tell me the date", "what is the date"
        ]):
            return IntentResult(
                intent="get_date",
                entities={},
                confidence=0.99,
                risk_level="low",
                original_text=text
            )

        # 11. Weather
        if any(w in clean_text for w in ["weather", "temperature", "forecast", "mausam"]):
            city = None
            city_match = re.search(r"\b(in|for|at)\b\s+([a-zA-Z\s]+)", clean_text)
            if city_match:
                city = city_match.group(2).replace("today", "").strip()
            return IntentResult(
                intent="weather",
                entities={"city": city or "local"},
                confidence=0.96,
                risk_level="low",
                original_text=text
            )

        # 12. Music & Audio Control
        if any(w in clean_text for w in ["play music", "play some music", "gaana sunao", "play a song", "play songs"]):
            return IntentResult(
                intent="play_music",
                entities={},
                confidence=0.95,
                risk_level="low",
                original_text=text
            )

        if any(w in clean_text for w in ["pause music", "stop music", "pause", "resume music"]):
            return IntentResult(
                intent="pause_music",
                entities={},
                confidence=0.95,
                risk_level="low",
                original_text=text
            )

        if any(w in clean_text for w in ["next song", "next track", "skip song", "next"]):
            return IntentResult(
                intent="next_track",
                entities={},
                confidence=0.95,
                risk_level="low",
                original_text=text
            )

        if any(w in clean_text for w in ["previous song", "previous track"]):
            return IntentResult(
                intent="previous_track",
                entities={},
                confidence=0.95,
                risk_level="low",
                original_text=text
            )

        # Volume control
        if "volume" in clean_text or "mute" in clean_text or "unmute" in clean_text or "awaz" in clean_text:
            action = "up"
            if any(w in clean_text for w in ["down", "lower", "decrease", "kam"]):
                action = "down"
            elif any(w in clean_text for w in ["mute", "silent"]):
                action = "mute"
            elif any(w in clean_text for w in ["unmute"]):
                action = "unmute"
            return IntentResult(
                intent="volume_control",
                entities={"action": action},
                confidence=0.97,
                risk_level="low",
                original_text=text
            )

        # 13. Clipboard
        if "clipboard" in clean_text:
            if any(w in clean_text for w in ["read", "what is on", "check"]):
                return IntentResult(
                    intent="clipboard_read",
                    entities={},
                    confidence=0.98,
                    risk_level="low",
                    original_text=text
                )
            elif any(w in clean_text for w in ["clear", "empty"]):
                return IntentResult(
                    intent="clipboard_clear",
                    entities={},
                    confidence=0.98,
                    risk_level="medium",
                    original_text=text
                )
            elif any(w in clean_text for w in ["copy", "write"]):
                text_to_copy = clean_text.replace("copy to clipboard", "").replace("copy this text", "").strip()
                return IntentResult(
                    intent="clipboard_write",
                    entities={"text": text_to_copy},
                    confidence=0.95,
                    risk_level="medium",
                    original_text=text
                )

        # 14. Command History queries
        if any(w in clean_text for w in ["what commands did i use", "show history", "command history", "my past commands", "recent commands"]):
            return IntentResult(
                intent="show_history",
                entities={},
                confidence=0.96,
                risk_level="low",
                original_text=text
            )

        # 15. Help & Guide
        if any(w in clean_text for w in ["help", "what can you do", "commands list", "madad", "help me"]):
            return IntentResult(
                intent="help",
                entities={},
                confidence=0.98,
                risk_level="low",
                original_text=text
            )

        # Default fallback: check if AI conversation fits or return friendly conversation
        ai_resp = self._generate_conversational_response(text)
        return IntentResult(
            intent="conversation",
            entities={"query": text},
            confidence=0.85,
            requires_confirmation=False,
            risk_level="low",
            response_text=ai_resp,
            original_text=text,
            is_conversation=True
        )

    def _check_contextual_followup(self, clean_text: str, context: ConversationContext) -> Optional[IntentResult]:
        """
        Resolves follow-up commands like:
        "Where should I create it?" -> "In Downloads"
        "Search YouTube" -> relative to browser
        "Open it" -> open last created target
        """
        # Follow-up parent directory for folder/file creation
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

        # Pronoun "open it"
        if clean_text in ["open it", "open that", "isse kholo"] and context.last_target_name:
            return IntentResult(
                intent="open_file",
                entities={"file_path": context.last_target_name},
                confidence=0.94,
                risk_level="low",
                original_text=clean_text
            )

        # Browser search context e.g. "search youtube" after opening browser
        if clean_text.startswith("search youtube"):
            query = clean_text.replace("search youtube", "").replace("for", "").strip()
            return IntentResult(
                intent="search_web",
                entities={"query": query, "engine": "youtube"},
                confidence=0.95,
                risk_level="low",
                original_text=clean_text
            )

        return None

    def _extract_app_name(self, phrase: str) -> str:
        clean = phrase.lower().replace("application", "").replace("app", "").replace("the", "").replace("google", "").strip()
        # Common aliases mapping
        mapping = {
            "chrome": "chrome",
            "browser": "chrome",
            "edge": "msedge",
            "microsoft edge": "msedge",
            "firefox": "firefox",
            "vscode": "code",
            "vs code": "code",
            "visual studio code": "code",
            "notepad": "notepad",
            "calc": "calculator",
            "calculator": "calculator",
            "explorer": "explorer",
            "file explorer": "explorer",
            "my files": "explorer",
            "terminal": "wt",
            "cmd": "cmd",
            "command prompt": "cmd",
            "powershell": "powershell",
            "spotify": "spotify",
            "discord": "discord",
            "settings": "settings",
            "task manager": "taskmgr",
        }
        return mapping.get(clean, clean)

    def _extract_search_entities(self, text: str) -> Tuple[str, str]:
        engine = "google"
        if "youtube" in text:
            engine = "youtube"
        elif "wikipedia" in text:
            engine = "wikipedia"
        elif "bing" in text:
            engine = "bing"
        elif "github" in text:
            engine = "github"

        # Remove prefix words
        clean = text
        for prefix in ["search google for", "search for", "search youtube for", "search wikipedia for", "search on google", "search", "google"]:
            if clean.startswith(prefix):
                clean = clean[len(prefix):].strip()
                break

        clean = clean.replace("youtube", "").replace("wikipedia", "").replace("google", "").strip()
        return (clean if clean else "trending news", engine)

    def _extract_reminder_entities(self, text: str) -> Tuple[str, str]:
        # Examples: "remind me to study at 8 PM", "remind me tomorrow at 10 AM to submit assignment"
        title = "Important task"
        time_str = "in 1 hour"

        # Regex for 'at ...'
        at_match = re.search(r"\b(at|in|on)\b\s+([0-9]+(?::[0-9]+)?\s*(?:am|pm|hours?|minutes?|mins?)?|\b[a-zA-Z0-9\s]+)", text)
        if at_match:
            time_str = at_match.group(2).strip()

        # Extract task title
        to_match = re.search(r"\bto\s+(.*?)(?:\s+at|\s+in|\s+tomorrow|$)", text)
        if to_match:
            title = to_match.group(1).strip()
        else:
            # Fallback title
            words = text.replace("remind me", "").replace("set a reminder", "").replace(f"at {time_str}", "").strip()
            if words:
                title = words

        return (title.capitalize(), time_str)

    def _extract_file_search_entities(self, text: str) -> Tuple[str, Optional[str]]:
        ext = None
        if "pdf" in text:
            ext = ".pdf"
        elif "python" in text or "py files" in text:
            ext = ".py"
        elif "word" in text or "doc" in text:
            ext = ".docx"
        elif "excel" in text or "sheet" in text:
            ext = ".xlsx"
        elif "image" in text or "picture" in text or "photo" in text:
            ext = ".png"

        query = text.replace("find my", "").replace("find all", "").replace("search my computer for a", "") \
            .replace("search my computer for", "").replace("where is my", "").replace("find", "").strip()
        return (query, ext)

    def _is_open_ended_conversation(self, text: str) -> bool:
        conversational_starts = [
            "explain ", "what is ", "what are ", "who is ", "who was ",
            "tell me about ", "tell me a joke", "how to ", "how do i ",
            "help me prepare ", "why is ", "can you write ", "summarize ",
            "kya hota hai", "samjhao"
        ]
        # Ignore if it's "what is the time" or "what is today's date"
        if any(w in text for w in ["time", "date", "weather", "clipboard", "cpu", "ram"]):
            return False
        return any(text.startswith(start) for start in conversational_starts)

    def _generate_conversational_response(self, text: str) -> str:
        # If OpenAI API Key is provided, use OpenAI LLM for rich answer
        if settings.openai_api_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=settings.openai_api_key)
                completion = client.chat.completions.create(
                    model=settings.openai_model,
                    messages=[
                        {"role": "system", "content": "You are Aura, an intelligent and friendly AI desktop voice assistant. Keep answers concise, clear, and direct (2-3 sentences max for spoken voice output)."},
                        {"role": "user", "content": text}
                    ],
                    max_tokens=150
                )
                return completion.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"OpenAI completion error: {e}")

        # Intelligent offline conversational knowledge engine
        lower = text.lower()
        if "machine learning" in lower:
            return "Machine learning is a subset of artificial intelligence where algorithms learn patterns from data to make predictions or decisions without being explicitly programmed."
        elif "python" in lower:
            return "Python is a high-level, interpreted programming language known for its clear syntax, vast ecosystem, and popularity in AI, data science, and web development."
        elif "interview" in lower:
            return "To prepare for your interview, review core technical concepts, practice standard behavioral questions using the STAR method, and research the company's recent projects."
        elif "joke" in lower:
            return "Why do programmers prefer dark mode? Because light attracts bugs!"
        elif "who are you" in lower or "your name" in lower:
            return f"I am {settings.app_name}, your AI-powered voice assistant designed to help automate desktop tasks, search information, and boost your productivity."
        else:
            return f"I understand you asked about '{text}'. As an assistant, I can help you search the web for more details, or control your applications and desktop."


nlp_service = NLPService()
