"""
Intelligent Task Planner & Multi-Intent Recognition Engine.
Handles:
- Multi-intent classification and clause segmentation (English, Hindi, Hinglish)
- Strict entity extraction (applications, queries, contacts, messages, summaries)
- Task dependency graph construction (parallel vs sequential)
- Safe Pydantic validation (never arbitrary code execution)
- Context preservation across conversational turns (follow-up queries, contact ambiguity, confirmation)
"""

from __future__ import annotations
import re
import uuid
import time
import logging
from typing import Dict, Any, List, Optional, Tuple

from backend.models.task_planner_schemas import TaskPlan, TaskItem, TaskStatus
from backend.services.contact_service import contact_service

logger = logging.getLogger(__name__)

# Known application names and their canonical keys
APP_CANONICAL_MAP = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "chrome browser": "chrome",
    "browser": "chrome",
    "browsre": "chrome",
    "brower": "chrome",
    "borwser": "chrome",
    "web browser": "chrome",
    "chorme": "chrome",
    "crome": "chrome",
    "whatsapp": "whatsapp",
    "whatsapp desktop": "whatsapp",
    "wa": "whatsapp",
    "whatsap": "whatsapp",
    "whatsaap": "whatsapp",
    "watsapp": "whatsapp",
    "edge": "msedge",
    "ms edge": "msedge",
    "microsoft edge": "msedge",
    "firefox": "firefox",
    "vs code": "code",
    "vscode": "code",
    "code": "code",
    "visual studio code": "code",
    "notepad": "notepad",
    "notepd": "notepad",
    "notpad": "notepad",
    "calculator": "calculator",
    "calc": "calculator",
    "calculater": "calculator",
    "calcualtor": "calculator",
    "hisaab": "calculator",
    "explorer": "explorer",
    "file explorer": "explorer",
    "files": "explorer",
    "terminal": "terminal",
    "youtube": "youtube",
    "yt": "youtube",
    "cmd": "terminal",
    "powershell": "terminal",
    "command prompt": "terminal",
    "spotify": "spotify",
    "spotfy": "spotify",
    "music": "spotify",
    "discord": "discord",
    "task manager": "taskmgr",
    "taskmgr": "taskmgr",
    "settings": "settings",
}

# Conjunction patterns separating distinct instructions
CONJUNCTION_PATTERN = re.compile(
    r"\b(?:and then|then|after that|after this|aur phir|phir|uske baad|saath hi|ek saath|simultaneously|at the same time|and also|and|an|&|aur|tatha)\b|,",
    re.IGNORECASE
)


class TaskPlanner:
    def __init__(self):
        # In-memory session context for multi-turn conversational follow-ups
        self.last_plan: Optional[TaskPlan] = None
        self.pending_confirmation_plan: Optional[TaskPlan] = None
        self.conversation_context: Dict[str, Any] = {
            "last_browser": "chrome",
            "last_query": None,
            "last_app": None,
            "last_contact": None,
            "awaiting_ambiguity": None,  # stores info when multiple contacts matched
        }

    def is_multi_command(self, text: str) -> bool:
        """
        Determines if a natural language sentence contains multiple commands.
        """
        if not text or not text.strip():
            return False

        clean = text.strip()
        clauses = self._split_into_candidate_clauses(clean)
        if len(clauses) > 1:
            return True

        # Check for conjunction words
        has_conjunction = bool(CONJUNCTION_PATTERN.search(clean))
        if has_conjunction and self._has_action_verb(clean):
            return True

        return self._has_multiple_action_verbs(clean)

    def _has_multiple_action_verbs(self, text: str) -> bool:
        """Checks if text contains multiple distinct action verbs or commands."""
        text_lower = text.lower()
        found_verbs = []
        verbs = [
            "open", "launch", "start", "kholo", "chalao",
            "search", "find", "google", "look up", "dhoondho", "dhoondo", "khojo",
            "send", "message", "text", "whatsapp", "bhejo",
            "call", "phone", "dial",
            "write", "note", "likho",
            "summarize", "summary", "explain",
            "screenshot", "capture",
            "close", "band karo"
        ]
        for v in verbs:
            if re.search(rf"\b{re.escape(v)}\b", text_lower):
                found_verbs.append(v)

        if ("open" in found_verbs or "launch" in found_verbs or "kholo" in found_verbs) and \
           any(v in found_verbs for v in ["search", "find", "google", "dhoondho", "dhoondo", "khojo", "send", "message", "bhejo", "call", "screenshot", "write"]):
            return True

        return len(found_verbs) >= 2

    def _split_into_candidate_clauses(self, text: str) -> List[str]:
        """
        Splits sentence along conjunctions and action boundaries while respecting quotes.
        """
        # First normalize double spaces and strip trailing punctuation
        clean_text = text.strip().rstrip(".!?,;:")
        normalized = re.sub(r"\s+", " ", clean_text)

        # 1. Atomic contact-action pattern (e.g. "Find Rahul in my contacts and call him" / "Find Ram and send him Hello")
        if re.search(r"\bfind\s+[a-zA-Z0-9\s]+?\s+(?:in\s+(?:my\s+)?contacts\s+and\s+|and\s+)(?:call|phone|send|message)\b", normalized, re.IGNORECASE):
            return [normalized]

        # 1b. Atomic gallery action pattern (e.g. "Open my gallery and find yesterday's photos")
        if re.search(r"\bopen\s+(?:my\s+)?gallery\s+and\s+find\b", normalized, re.IGNORECASE):
            return [normalized]

        # 2. If user explicitly wrote "Open Chrome and WhatsApp [simultaneously]"
        clean_no_simul = re.sub(
            r"\s+\b(?:simultaneously|together|ek saath|saath hi|at the same time)\b.*$",
            "",
            normalized,
            flags=re.IGNORECASE
        ).strip()
        multi_open_match = re.match(
            r"^(?:open|launch|kholo|chalao)\s+([a-zA-Z\s]+)\s+(?:and|an|&|aur|saath hi)\s+([a-zA-Z\s]+)$",
            clean_no_simul,
            re.IGNORECASE
        )
        if multi_open_match:
            app1 = multi_open_match.group(1).strip()
            app2 = multi_open_match.group(2).strip()
            if not self._has_action_verb(app2) and self._identify_app(app1) and self._identify_app(app2):
                return [f"open {app1}", f"open {app2}"]

        # 3. Split on strong sequential markers first
        parts = re.split(
            r"\b(?:and\s+then|then|after\s+that|aur\s+phir|phir|uske\s+baad|saath\s+hi|ek\s+saath|simultaneously)\b",
            normalized,
            flags=re.IGNORECASE
        )

        compound_action_pat = (
            r"^(?:open|launch|start|run|kholo|chalao)\s+([a-zA-Z0-9\s]+?)\s*"
            r"(?:\b(?:and\s+then|then|after\s+that|and|an|&|aur|phir)\b|,|\s)\s*"
            r"(?:and\s+|an\s+|then\s+)?(search\s+for|search\s+about|search|find|google|look\s+up|dhoondho|dhoondo|khojo|send\s+message|send|message|text|screenshot|take\s+screenshot|write|call|phone|dial)\b\s*(.*)$"
        )
        pat_hindi = (
            r"^([a-zA-Z0-9\s]+?)\s+(?:kholo|chalao)\s*"
            r"(?:\b(?:aur\s+phir|phir|aur|an|and)\b|,|\s)\s*"
            r"(?:search\s+karo\s+(.*)|(.*)\s+search\s+karo)$"
        )

        candidate_clauses = []
        for part in parts:
            part = part.strip().strip(",;").strip()
            if not part:
                continue

            # Check direct compound action on this segment (e.g. "open Chrome an search what is ai")
            compound_action_match = re.match(compound_action_pat, part, re.IGNORECASE)
            if compound_action_match:
                app_raw = compound_action_match.group(1).strip()
                action_raw = compound_action_match.group(2).strip()
                args_raw = compound_action_match.group(3).strip()
                app_key = self._identify_app(app_raw)
                if app_key:
                    candidate_clauses.append(f"open {app_key}")
                    candidate_clauses.append(f"{action_raw} {args_raw}".strip())
                    continue

            # Check Hindi compound pattern on this segment
            hindi_m = re.match(pat_hindi, part, re.IGNORECASE)
            if hindi_m:
                app_raw = hindi_m.group(1).strip()
                query_raw = (hindi_m.group(2) or hindi_m.group(3) or "").strip()
                app_key = self._identify_app(app_raw)
                if app_key:
                    candidate_clauses.append(f"open {app_key}")
                    candidate_clauses.append(f"search for {query_raw}" if query_raw else "search")
                    continue

            # Check if this subpart contains "and", "an", "&", "aur" connecting distinct action verbs
            subparts = re.split(r"\b(?:and|an|&|aur|tatha)\b", part, flags=re.IGNORECASE)
            if len(subparts) > 1:
                accumulated = []
                current = ""
                for s in subparts:
                    s_clean = s.strip()
                    if not s_clean:
                        continue
                    if self._has_action_verb(s_clean) or self._is_app_mention(s_clean):
                        if current:
                            accumulated.append(current.strip())
                        current = s_clean
                    else:
                        current = f"{current} and {s_clean}" if current else s_clean
                if current:
                    accumulated.append(current.strip())
                candidate_clauses.extend(accumulated)
            else:
                candidate_clauses.append(part)

        return [c.strip().rstrip(".!?,;:") for c in candidate_clauses if re.search(r"[a-zA-Z0-9]", c)]

    def _has_action_verb(self, text: str) -> bool:
        verbs = [
            "open", "launch", "start", "run", "kholo", "chalao",
            "search", "find", "google", "look up", "dhoondho", "dhoondo", "khojo",
            "send", "message", "text", "whatsapp", "bhejo",
            "call", "phone", "dial",
            "write", "note", "likho",
            "summarize", "summary", "explain",
            "screenshot", "capture", "photo",
            "close", "band karo"
        ]
        text_lower = text.lower()
        return any(re.search(rf"\b{re.escape(v)}\b", text_lower) for v in verbs)

    def _is_app_mention(self, text: str) -> bool:
        clean = text.lower().strip()
        return clean in APP_CANONICAL_MAP

    def _identify_app(self, text: str) -> Optional[str]:
        clean = text.lower().strip()
        if not clean:
            return None

        # If candidate contains action words (e.g. "search", "what is", "send", "call"), don't treat the entire phrase as an application
        if any(w in clean for w in ["search", "dhoondo", "dhoondho", "khojo", "what is", "send", "message", "bhejo", "call", "phone", "dial", "write"]):
            app_sub = re.match(
                r"^([a-zA-Z0-9\s]+?)\s*(?:\b(?:and\s+then|then|after\s+that|and|an|&|aur|phir)\b|,|\s)\s*(?:search|what|send|message|call|phone|dhoondo)\b",
                clean
            )
            if app_sub:
                clean = app_sub.group(1).strip()
            else:
                for k in ["chrome", "whatsapp", "notepad", "calculator", "explorer", "spotify", "code", "browser", "browsre"]:
                    if re.search(rf"\b{re.escape(k)}\b", clean):
                        return "chrome" if ("brows" in k or "chrom" in k) else k
                return None

        # 1. Exact or whole-word match in canonical map
        for alias, canonical in APP_CANONICAL_MAP.items():
            if re.search(rf"\b{re.escape(alias)}\b", clean):
                return canonical

        # 2. Fuzzy match against canonical names and aliases (handles typos like 'browsre', 'chorme')
        import difflib
        stop_words = {
            "what", "who", "when", "where", "why", "how", "the", "a", "an", "is", "it",
            "in", "on", "for", "at", "to", "of", "and", "or", "my", "your", "this",
            "that", "me", "him", "her", "them", "all", "so", "as", "if", "about", "with"
        }
        tokens = [tok for tok in clean.split() if tok not in stop_words and len(tok) >= 4]
        for tok in tokens:
            matches = difflib.get_close_matches(tok, APP_CANONICAL_MAP.keys(), n=1, cutoff=0.80)
            if matches:
                return APP_CANONICAL_MAP[matches[0]]

        if clean not in stop_words and len(clean) >= 4:
            matches = difflib.get_close_matches(clean, APP_CANONICAL_MAP.keys(), n=1, cutoff=0.80)
            if matches:
                return APP_CANONICAL_MAP[matches[0]]

        return None

    def plan_instruction(self, text: str) -> TaskPlan:
        """
        Parses a full multi-command instruction into a structured validated TaskPlan.
        Supports cross-platform and cross-device instructions across Windows and Android.
        """
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        clean_text = text.strip()

        # Check for contextual follow-up first
        follow_up_plan = self._handle_conversational_follow_up(clean_text, plan_id)
        if follow_up_plan:
            self.last_plan = follow_up_plan
            return follow_up_plan

        # Check for Cross-Device Coordination Instruction
        cross_device_plan = self._detect_cross_device_instruction(clean_text, plan_id)
        if cross_device_plan:
            self.last_plan = cross_device_plan
            if cross_device_plan.requires_confirmation:
                self.pending_confirmation_plan = cross_device_plan
            return cross_device_plan

        clauses = self._split_into_candidate_clauses(clean_text)
        tasks: List[TaskItem] = []
        app_context: Optional[str] = None
        last_task_id: Optional[str] = None
        plan_requires_conf = False
        ambiguous_contacts_list: List[Dict[str, Any]] = []

        is_explicit_parallel = bool(re.search(
            r"\b(?:simultaneously|ek saath|saath hi|together|at the same time)\b",
            clean_text,
            re.IGNORECASE
        ))

        for idx, clause in enumerate(clauses):
            task_id = f"task_{idx + 1}"
            task_item, detected_app = self._parse_single_clause(task_id, clause, app_context)

            # Ensure target device is assigned
            if not task_item.target_device or task_item.target_device == "auto":
                task_item.target_device = self._determine_target_device(clause, task_item.intent, task_item.application)

            if detected_app:
                app_context = detected_app
                self.conversation_context["last_app"] = detected_app

            # Determine dependencies
            if is_explicit_parallel:
                # All independent tasks run concurrently
                task_item.depends_on = []
            elif task_item.intent in ["search_web", "summarize_results"] and app_context in ["chrome", "msedge"]:
                # Browser action depends on the browser launch task if preceded by one
                browser_tasks = [t.id for t in tasks if t.intent == "open_application" and t.application in ["chrome", "msedge"]]
                if browser_tasks:
                    task_item.depends_on = [browser_tasks[-1]]
            elif task_item.intent == "send_message" and app_context == "whatsapp":
                # Message dispatch depends on WhatsApp launch task if preceded by one
                wa_tasks = [t.id for t in tasks if t.intent == "open_application" and t.application == "whatsapp"]
                if wa_tasks:
                    task_item.depends_on = [wa_tasks[-1]]
            elif idx > 0 and not is_explicit_parallel:
                # If sequential wording was used, link to previous step
                if re.search(r"\b(?:then|after that|aur phir|phir|uske baad)\b", clean_text, re.IGNORECASE):
                    task_item.depends_on = [last_task_id] if last_task_id else []

            # Check for contact resolution and confirmation requirements
            if task_item.intent in ["send_message", "make_call"] and task_item.contact:
                matched, ambiguous = contact_service.resolve_contact(task_item.contact)
                if ambiguous and len(ambiguous) > 1:
                    plan_requires_conf = True
                    ambiguous_contacts_list = ambiguous
                    self.conversation_context["awaiting_ambiguity"] = {
                        "task_id": task_id,
                        "candidates": ambiguous,
                        "message": task_item.message,
                        "intent": task_item.intent
                    }
                    task_item.status = TaskStatus.WAITING_CONFIRMATION
                    task_item.error = f"Multiple contacts found for '{task_item.contact}'"
                elif matched:
                    task_item.phone = matched["phone"]
                    task_item.contact = matched["name"]
                    task_item.requires_confirmation = True
                    plan_requires_conf = True
                    task_item.status = TaskStatus.WAITING_CONFIRMATION
                else:
                    task_item.requires_confirmation = True
                    plan_requires_conf = True
                    task_item.status = TaskStatus.WAITING_CONFIRMATION

            tasks.append(task_item)
            last_task_id = task_id

        # Construct TaskPlan
        plan = TaskPlan(
            plan_id=plan_id,
            original_instruction=clean_text,
            tasks=tasks,
            status="waiting_confirmation" if plan_requires_conf else "created",
            requires_confirmation=plan_requires_conf,
            confirmation_id=uuid.uuid4().hex[:6] if plan_requires_conf else None,
            ambiguous_contacts=ambiguous_contacts_list if ambiguous_contacts_list else None,
            summary=f"Plan prepared with {len(tasks)} executable steps."
        )

        self.last_plan = plan
        if plan_requires_conf:
            self.pending_confirmation_plan = plan

        return plan

    def _determine_target_device(self, clause_clean: str, intent: str, app: Optional[str]) -> str:
        """Determines target device: android | windows | cloud | auto."""
        lower = clause_clean.lower()
        if any(h in lower for h in ["on my laptop", "on laptop", "on my pc", "on pc", "on windows", "on computer"]):
            return "windows"
        if any(h in lower for h in ["on my phone", "on phone", "on android", "on mobile"]):
            return "android"

        # Android specific intents
        if intent in [
            "set_alarm", "read_notifications", "control_device_setting",
            "query_gallery", "open_phone_app", "find_phone_file", "receive_file"
        ]:
            return "android"
        if intent == "make_call":
            return "android"
        if intent == "query_contacts":
            return "android"
        if intent == "send_message" and any(w in lower for w in ["phone", "mobile", "dad", "mom", "bhejo"]):
            return "android"

        # Windows specific intents
        if intent in ["write_note", "create_folder", "find_file", "system_specs", "manage_files", "transfer_file"]:
            return "windows"
        if app in ["code", "explorer", "notepad", "calculator", "terminal", "word", "excel", "powerpoint"]:
            return "windows"
        if intent == "open_application" and app == "chrome":
            return "windows"

        return "auto"

    def _detect_cross_device_instruction(self, text: str, plan_id: str) -> Optional[TaskPlan]:
        """Detects cross-device workflows (Windows <-> Android coordination)."""
        clean = text.strip()
        lower = clean.lower()

        # 1. "Find my resume on my laptop and send it to Dad on WhatsApp"
        pat_resume_wa = re.search(
            r"\b(?:find|get|locate)\s+(?:my\s+)?([a-zA-Z0-9_\-\.\s]+?)\s+(?:on\s+my\s+laptop|on\s+laptop|on\s+windows|on\s+pc)\s+(?:and\s+)?(?:send\s+(?:it\s+)?to|whatsapp)\s+([a-zA-Z0-9\s]+?)(?:\s+(?:on|via)\s+whatsapp)?$",
            clean,
            re.IGNORECASE
        )
        if pat_resume_wa:
            doc_name = pat_resume_wa.group(1).strip()
            contact_name = pat_resume_wa.group(2).strip()
            t1 = TaskItem(
                id="task_1",
                title=f"Find '{doc_name}' on Windows laptop",
                intent="manage_files",
                target_device="windows",
                query=doc_name,
                data={"action": "find_file", "filename": doc_name},
                status=TaskStatus.PENDING
            )
            t2 = TaskItem(
                id="task_2",
                title=f"Stage '{doc_name}' for Cross-Device Transfer",
                intent="relay_file",
                target_device="cloud",
                depends_on=["task_1"],
                data={"source_device": "windows", "target_device": "android", "filename": doc_name},
                status=TaskStatus.PENDING
            )
            t3 = TaskItem(
                id="task_3",
                title=f"Send '{doc_name}' to {contact_name} on WhatsApp via Android",
                intent="send_message",
                target_device="android",
                contact=contact_name,
                application="whatsapp",
                message=f"Sharing document: {doc_name}",
                depends_on=["task_2"],
                requires_confirmation=True,
                risk_level="medium",
                data={"attachment": doc_name, "transfer_relay": True},
                status=TaskStatus.PENDING
            )
            return TaskPlan(
                plan_id=plan_id,
                original_instruction=text,
                tasks=[t1, t2, t3],
                status="waiting_confirmation",
                requires_confirmation=True,
                confirmation_id=uuid.uuid4().hex[:6],
                summary=f"Cross-device workflow: Locate '{doc_name}' on Windows, transfer to Android, and send to {contact_name} on WhatsApp."
            )

        # 2. "Show my laptop's battery status on my phone"
        pat_battery = re.search(
            r"\b(?:show|display|check)\s+(?:my\s+)?(?:laptop'?s?|pc'?s?|computer'?s?)\s+(?:battery|ram|storage|status|hardware)\s+(?:status\s+)?(?:on\s+my\s+phone|on\s+phone|on\s+android)\b",
            lower
        )
        if pat_battery or ("battery" in lower and "laptop" in lower and "phone" in lower):
            t1 = TaskItem(
                id="task_1",
                title="Query Windows laptop battery and hardware status",
                intent="system_specs",
                target_device="windows",
                data={"metrics": ["battery", "ram", "storage"]},
                status=TaskStatus.PENDING
            )
            t2 = TaskItem(
                id="task_2",
                title="Display laptop battery status notification on Android phone",
                intent="notify_device",
                target_device="android",
                depends_on=["task_1"],
                data={"source_device": "windows", "notification_type": "hardware_status"},
                status=TaskStatus.PENDING
            )
            return TaskPlan(
                plan_id=plan_id,
                original_instruction=text,
                tasks=[t1, t2],
                status="created",
                summary="Cross-device workflow: Read laptop battery metrics on Windows and present them on Android phone."
            )

        # 3. "Find the PDF on my phone and open it on my laptop"
        pat_phone_to_laptop = re.search(
            r"\b(?:find|get|locate)\s+(?:the\s+)?([a-zA-Z0-9_\-\.\s]+?)\s+(?:on\s+my\s+phone|on\s+phone)\s+(?:and\s+)?open\s+(?:it\s+)?(?:on\s+my\s+laptop|on\s+laptop|on\s+windows|on\s+pc)\b",
            clean,
            re.IGNORECASE
        )
        if pat_phone_to_laptop:
            doc_name = pat_phone_to_laptop.group(1).strip()
            t1 = TaskItem(
                id="task_1",
                title=f"Locate '{doc_name}' on Android phone",
                intent="find_phone_file",
                target_device="android",
                query=doc_name,
                status=TaskStatus.PENDING
            )
            t2 = TaskItem(
                id="task_2",
                title=f"Relay '{doc_name}' to Windows laptop",
                intent="relay_file",
                target_device="cloud",
                depends_on=["task_1"],
                data={"source_device": "android", "target_device": "windows", "filename": doc_name},
                status=TaskStatus.PENDING
            )
            t3 = TaskItem(
                id="task_3",
                title=f"Open '{doc_name}' on Windows laptop",
                intent="open_file",
                target_device="windows",
                depends_on=["task_2"],
                data={"filename": doc_name},
                status=TaskStatus.PENDING
            )
            return TaskPlan(
                plan_id=plan_id,
                original_instruction=text,
                tasks=[t1, t2, t3],
                status="created",
                summary=f"Cross-device workflow: Locate '{doc_name}' on Android, transfer to Windows, and open in default viewer."
            )

        # 4. "Transfer this file from my laptop to my phone"
        pat_transfer = re.search(
            r"\btransfer\s+(?:this\s+file|a\s+file|[a-zA-Z0-9_\-\.\s]+?)\s+from\s+(?:my\s+)?(?:laptop|pc)\s+to\s+(?:my\s+)?phone\b",
            lower
        )
        if pat_transfer:
            t1 = TaskItem(
                id="task_1",
                title="Stage selected file on Windows laptop for transfer",
                intent="transfer_file",
                target_device="windows",
                status=TaskStatus.PENDING
            )
            t2 = TaskItem(
                id="task_2",
                title="Receive and save file in Android phone Downloads folder",
                intent="receive_file",
                target_device="android",
                depends_on=["task_1"],
                status=TaskStatus.PENDING
            )
            return TaskPlan(
                plan_id=plan_id,
                original_instruction=text,
                tasks=[t1, t2],
                status="created",
                summary="Cross-device workflow: Transfer file from Windows laptop to Android phone."
            )

        return None

    def _parse_single_clause(
        self,
        task_id: str,
        clause: str,
        current_app_context: Optional[str]
    ) -> Tuple[TaskItem, Optional[str]]:
        """
        Parses a single clause into a TaskItem.
        """
        clause_clean = clause.strip()
        clause_lower = clause_clean.lower()

        # 0a. Android Device Settings (Bluetooth, WiFi, Hotspot, etc.)
        setting_m = re.search(r"\b(?:turn\s+(on|off)|enable|disable|toggle|chalu\s+karo|band\s+karo)\s+(bluetooth|wifi|hotspot|airplane\s+mode|flashlight)\b", clause_lower)
        setting_m_hi = re.search(r"\b(bluetooth|wifi|hotspot)\s+(?:on|off|chalu|band)\s*(?:karo|kardo)?\b", clause_lower)
        if setting_m or setting_m_hi:
            target_setting = setting_m.group(2) if setting_m else setting_m_hi.group(1)
            action = "on" if ("on" in clause_lower or "chalu" in clause_lower or "enable" in clause_lower) else "off"
            return TaskItem(
                id=task_id,
                title=f"Turn {action.upper()} {target_setting.title()} on Android phone",
                intent="control_device_setting",
                target_device="android",
                data={"setting": target_setting, "action": action},
                risk_level="low",
                status=TaskStatus.PENDING
            ), None

        # 0b. Android Phone Settings App
        if any(w in clause_lower for w in ["phone settings", "my phone settings", "phone ki settings", "mobile settings"]):
            return TaskItem(
                id=task_id,
                title="Open Settings on Android phone",
                intent="open_phone_app",
                application="settings",
                target_device="android",
                risk_level="low",
                status=TaskStatus.PENDING
            ), "settings"

        # 0c. Android Alarms
        alarm_m = re.search(r"\b(?:set\s+(?:an\s+)?alarm|alarm\s+lagao)\s*(?:for\s+|at\s+)?([0-9]{1,2}(?::[0-9]{2})?\s*(?:am|pm)?|[0-9]{1,2}\s*baje)?", clause_clean, re.IGNORECASE)
        if alarm_m or ("alarm" in clause_lower and any(w in clause_lower for w in ["set", "lagao", "karo", "for", "at"])):
            alarm_time = alarm_m.group(1).strip() if (alarm_m and alarm_m.group(1)) else "7 AM"
            return TaskItem(
                id=task_id,
                title=f"Set an alarm for {alarm_time} on Android phone",
                intent="set_alarm",
                target_device="android",
                data={"time": alarm_time, "label": "Alarm"},
                risk_level="low",
                status=TaskStatus.PENDING
            ), None

        # 0d. Android Notifications
        if any(w in clause_lower for w in ["read my notifications", "check my notifications", "read notifications", "notifications padho", "notifications batao"]):
            return TaskItem(
                id=task_id,
                title="Read notifications on Android phone",
                intent="read_notifications",
                target_device="android",
                risk_level="low",
                status=TaskStatus.PENDING
            ), None

        # 0e. Android Gallery & Photos
        if any(w in clause_lower for w in ["gallery", "yesterday's photos", "recent photos", "my photos", "photo album"]):
            query_str = "yesterday's photos" if "yesterday" in clause_lower else "recent photos"
            return TaskItem(
                id=task_id,
                title=f"Open Gallery and search for {query_str} on Android phone",
                intent="query_gallery",
                target_device="android",
                query=query_str,
                risk_level="low",
                status=TaskStatus.PENDING
            ), "gallery"

        # 0f. Android Contacts Lookup
        contacts_m = re.search(r"\bfind\s+([a-zA-Z0-9\s]+?)\s+in\s+(?:my\s+)?contacts\b", clause_clean, re.IGNORECASE)
        if contacts_m and not any(w in clause_lower for w in ["call", "phone", "dial"]):
            c_name = contacts_m.group(1).strip()
            return TaskItem(
                id=task_id,
                title=f"Find {c_name} in contacts on Android phone",
                intent="query_contacts",
                target_device="android",
                contact=c_name,
                risk_level="low",
                status=TaskStatus.PENDING
            ), None

        # 0g. Windows Hardware & Specs (RAM, Storage, Battery)
        if any(w in clause_lower for w in ["ram and storage", "check my laptop's ram", "battery and ram", "laptop's battery", "laptop status", "laptop specs"]):
            return TaskItem(
                id=task_id,
                title="Check Windows laptop RAM, storage, and battery metrics",
                intent="system_specs",
                target_device="windows",
                risk_level="low",
                status=TaskStatus.PENDING
            ), None

        # 0h. Windows Create Folder
        create_folder_m = re.search(r"\bcreate\s+(?:a\s+)?folder\s+(?:called|named)\s+([a-zA-Z0-9_\-\s]+)", clause_clean, re.IGNORECASE)
        if create_folder_m:
            f_name = create_folder_m.group(1).strip()
            return TaskItem(
                id=task_id,
                title=f"Create folder '{f_name}' on Windows laptop",
                intent="create_folder",
                target_device="windows",
                data={"folder_name": f_name},
                risk_level="low",
                status=TaskStatus.PENDING
            ), None

        # 0i. Windows Open Folders (Downloads, Documents, etc.)
        open_folder_m = re.search(r"\bopen\s+(?:my\s+)?(downloads|documents|desktop|music|videos)\s+(?:folder)?\b", clause_clean, re.IGNORECASE)
        if open_folder_m:
            fold = open_folder_m.group(1).strip().lower()
            return TaskItem(
                id=task_id,
                title=f"Open {fold.title()} folder in File Explorer on Windows laptop",
                intent="open_file",
                target_device="windows",
                data={"folder": fold, "is_folder": True},
                risk_level="low",
                status=TaskStatus.PENDING
            ), "explorer"

        # 0j. Windows Find Resume / Files
        find_file_m = re.search(r"\b(?:find|search\s+for|locate)\s+(?:my\s+)?(resume|pdf|document|file|[a-zA-Z0-9_\-\.]+\.[a-zA-Z]{2,4})\b", clause_clean, re.IGNORECASE)
        is_calling_tentative = any(w in clause_lower for w in ["call", "phone", "dial"])
        if find_file_m and not is_calling_tentative:
            target_f = find_file_m.group(1).strip()
            return TaskItem(
                id=task_id,
                title=f"Search for '{target_f}' in safe folders on Windows laptop",
                intent="manage_files",
                target_device="windows",
                query=target_f,
                data={"action": "find_file", "filename": target_f},
                risk_level="low",
                status=TaskStatus.PENDING
            ), "explorer"

        # 1. Open Application Intent
        # Patterns: "open chrome", "launch whatsapp", "chrome kholo", "notepad chalao"
        open_match = re.search(
            r"\b(?:open|launch|start|run|kholo|chalao)\s+([a-zA-Z0-9\s]+)",
            clause_lower
        )
        kholo_match = re.search(r"([a-zA-Z0-9\s]+)\s+(?:kholo|chalao)\b", clause_lower)

        app_name = None
        if open_match:
            candidate = open_match.group(1).strip()
            app_name = self._identify_app(candidate)
        elif kholo_match:
            candidate = kholo_match.group(1).strip()
            app_name = self._identify_app(candidate)
        elif clause_lower in APP_CANONICAL_MAP:
            app_name = APP_CANONICAL_MAP[clause_lower]

        # Check if clause is purely opening an app
        if app_name and not any(kw in clause_lower for kw in ["search", "dhoondho", "send", "message", "bhejo"]):
            return TaskItem(
                id=task_id,
                title=f"Open {app_name.title()}",
                intent="open_application",
                application=app_name,
                risk_level="low",
                status=TaskStatus.PENDING
            ), app_name

        # 2. Web Search Intent
        # Patterns: "search for AI", "search about machine learning", "AI search karo", "dhoondho X"
        # Support engines: YouTube, Google, News
        engine = "google"
        if "youtube" in clause_lower or current_app_context == "youtube":
            engine = "youtube"
        elif "news" in clause_lower:
            engine = "news"

        # Check Hindi search patterns first to avoid capturing "search" in "search karo"
        hindi_search_match = re.search(
            r"^(.*?)(?:\s+(?:ke baare mein|ke bare me|ke baare me|ke bare mein))?\s+(?:search karo|dhoondho|khojo)\b",
            clause_clean,
            re.IGNORECASE
        )
        search_match = re.search(
            r"\b(?:search for|search about|search|google|find|look up|dhoondho|khojo)\s+[\"']?([^\"'\n\r]+?)[\"']?(?:\s+(?:on|in)\s+(?:youtube|google|chrome))?$",
            clause_clean,
            re.IGNORECASE
        )

        should_summarize = bool(re.search(r"\b(?:summarize|summary|batao|explain)\b", clause_lower))
        is_calling_intent = any(w in clause_lower for w in ["call", "phone", "dial", "call lagao", "phone karo"]) or ("contacts" in clause_lower and "find" in clause_lower)

        if (hindi_search_match or search_match) and not is_calling_intent:
            raw_query = hindi_search_match.group(1) if hindi_search_match else search_match.group(1)
            # Clean up query
            clean_query = re.sub(
                r"\b(?:and then summarize the results|and summarize|summarize results|then summarize|ke baare mein|ke bare me|ke baare me|ke bare mein)\b",
                "",
                raw_query,
                flags=re.IGNORECASE
            ).strip()
            clean_query = re.sub(r"^(?:for|about)\s+", "", clean_query, flags=re.IGNORECASE).strip()

            target_app = "chrome"
            self.conversation_context["last_query"] = clean_query

            return TaskItem(
                id=task_id,
                title=f"Search {engine.title()} for '{clean_query}'",
                intent="search_web",
                application=target_app,
                query=clean_query,
                engine=engine,
                summarize=should_summarize,
                risk_level="low",
                status=TaskStatus.PENDING
            ), target_app

        # 2b. Calling Intent (English, Hindi, Punjabi, German)
        find_call_match = re.search(
            r"\bfind\s+([a-zA-Z0-9\s]+?)\s+(?:in\s+(?:my\s+)?contacts\s+and\s+|and\s+)(?:call|phone)\s*(?:him|her|them)?(?:\s+(?:on|via|with)\s+(whatsapp|phone|skype|teams))?$",
            clause_clean,
            re.IGNORECASE
        )
        call_match = re.search(
            r"\b(?:call|phone|make a call to|dial|rufe|ruf|lagao call)\s+([a-zA-Z0-9\s]+?)(?:\s+(?:an|on\s+whatsapp|via\s+whatsapp|with\s+whatsapp))?$",
            clause_clean,
            re.IGNORECASE
        )
        hindi_call_match = re.search(
            r"([a-zA-Z0-9\s]+?)\s+(?:ko|nu)\s+(?:whatsapp\s+)?(?:call\s+lagao|phone\s+karo|call\s+karo)",
            clause_clean,
            re.IGNORECASE
        )
        if (find_call_match or call_match or hindi_call_match) and not any(w in clause_lower for w in ["later", "saying", "that", "ki", "message"]):
            raw_contact = ""
            if find_call_match:
                raw_contact = find_call_match.group(1).strip()
            elif hindi_call_match:
                raw_contact = hindi_call_match.group(1).strip()
            elif call_match:
                raw_contact = call_match.group(1).strip()

            clean_contact = re.sub(r"\b(this number|number|him|her|them|ko|nu|an|my contacts|contacts)\b", "", raw_contact, flags=re.IGNORECASE).strip()
            if clean_contact:
                provider = "whatsapp" if ("whatsapp" in clause_lower or current_app_context == "whatsapp") else "phone_link"
                return TaskItem(
                    id=task_id,
                    title=f"Call {clean_contact}",
                    intent="make_call",
                    application=provider,
                    contact=clean_contact,
                    requires_confirmation=True,
                    risk_level="medium",
                    status=TaskStatus.PENDING,
                    data={"provider": provider, "contact": clean_contact}
                ), provider

        # 3. WhatsApp / Messaging Intent
        # A. Patterns like: "send a whatsapp message to Ram: I will arrive in 10 minutes"
        #                   "send a message to Amit saying the meeting is at 5 PM"
        #                   "send message to Rahul that I am coming"
        pat_to_saying = re.search(
            r"\b(?:send|post)\s+(?:a\s+)?(?:whatsapp\s+)?(?:message|text)?\s*(?:to\s+)([a-zA-Z0-9\s]+?)(?::|\s+saying\s+|\s+that\s+|\s+with\s+text\s+)\s*[\"']?([^\"'\n\r]+)[\"']?",
            clause_clean,
            re.IGNORECASE
        )
        # B. Patterns like: "message Ram saying Hi"
        #                   "message Rahul that I am coming"
        #                   "tell Mom that I will call later"
        pat_msg_saying = re.search(
            r"\b(?:message|tell|whatsapp)\s+([a-zA-Z0-9\s]+?)\s+(?:saying|that|ki)\s+[\"']?([^\"'\n\r]+)[\"']?",
            clause_clean,
            re.IGNORECASE
        )
        # C. Patterns with colon: "message Ram: Hi" or "tell Mom: I will call later"
        pat_colon = re.search(
            r"\b(?:send\s+message\s+to|message|tell|whatsapp)\s+([a-zA-Z0-9\s]+?)\s*:\s*[\"']?([^\"'\n\r]+)[\"']?",
            clause_clean,
            re.IGNORECASE
        )
        # D. "find Ram and send him Hello" or "find Ram and send Hello"
        pat_find_send = re.search(
            r"\b(?:find|search\s+for)\s+([a-zA-Z0-9\s]+?)\s+(?:and\s+)?send\s+(?:him|her|them)?\s*[\"']?([^\"'\n\r]+)[\"']?",
            clause_clean,
            re.IGNORECASE
        )
        # E. "send Hi to Ram" / "text Hi to Ram"
        pat_send_to = re.search(
            r"\b(?:send|text|message)\s+[\"']?([^\"'\n\r]+?)[\"']?\s+to\s+([a-zA-Z0-9\s]+)",
            clause_clean,
            re.IGNORECASE
        )
        # F. "tell Mom I will call later" (direct tell without saying/that)
        pat_tell_direct = re.search(
            r"\b(?:tell)\s+([a-zA-Z0-9]+)\s+[\"']?([^\"'\n\r]+)[\"']?$",
            clause_clean,
            re.IGNORECASE
        )
        # G. "message Ram Hi" / "whatsapp Rahul Hello"
        pat_msg_direct = re.search(
            r"\b(?:message|whatsapp)\s+([a-zA-Z0-9]+)\s+[\"']?([^\"'\n\r]+)[\"']?$",
            clause_clean,
            re.IGNORECASE
        )
        # H. Hindi: "Rahul ko message bhejo: I am coming" / "Ram ko Hi bhejo"
        pat_hindi_bhejo = re.search(
            r"([a-zA-Z0-9\s]+?)\s+ko\s+(?:whatsapp\s+)?(?:message\s+)?(?:bhejo|karo)\s*(?:ki|:)?\s*[\"']?([^\"'\n\r]+)[\"']?",
            clause_clean,
            re.IGNORECASE
        )
        pat_hindi_msg = re.search(
            r"([a-zA-Z0-9\s]+?)\s+ko\s+[\"']?([^\"'\n\r]+?)[\"']?\s+(?:message\s+)?(?:bhejo|karo)",
            clause_clean,
            re.IGNORECASE
        )

        if pat_to_saying:
            contact_name = pat_to_saying.group(1).strip()
            msg_content = pat_to_saying.group(2).strip()
            return self._build_message_task(task_id, contact_name, msg_content)
        elif pat_msg_saying:
            contact_name = pat_msg_saying.group(1).strip()
            msg_content = pat_msg_saying.group(2).strip()
            return self._build_message_task(task_id, contact_name, msg_content)
        elif pat_colon:
            contact_name = pat_colon.group(1).strip()
            msg_content = pat_colon.group(2).strip()
            return self._build_message_task(task_id, contact_name, msg_content)
        elif pat_find_send:
            contact_name = pat_find_send.group(1).strip()
            msg_content = pat_find_send.group(2).strip()
            return self._build_message_task(task_id, contact_name, msg_content)
        elif pat_send_to:
            contact_name = pat_send_to.group(2).strip()
            msg_content = pat_send_to.group(1).strip()
            return self._build_message_task(task_id, contact_name, msg_content)
        elif pat_tell_direct:
            contact_name = pat_tell_direct.group(1).strip()
            msg_content = pat_tell_direct.group(2).strip()
            return self._build_message_task(task_id, contact_name, msg_content)
        elif pat_msg_direct:
            contact_name = pat_msg_direct.group(1).strip()
            msg_content = pat_msg_direct.group(2).strip()
            return self._build_message_task(task_id, contact_name, msg_content)
        elif pat_hindi_bhejo:
            contact_name = pat_hindi_bhejo.group(1).strip()
            msg_content = pat_hindi_bhejo.group(2).strip()
            return self._build_message_task(task_id, contact_name, msg_content)
        elif pat_hindi_msg:
            contact_name = pat_hindi_msg.group(1).strip()
            msg_content = pat_hindi_msg.group(2).strip()
            return self._build_message_task(task_id, contact_name, msg_content)

        # 3b. Notepad / Writing Notes Intent
        write_note_match = re.search(
            r"\b(?:write|take|create)\s+(?:today's\s+|my\s+)?(?:meeting\s+)?(?:notes|note|text)\b\s*(.*)$",
            clause_clean,
            re.IGNORECASE
        )
        if write_note_match or "meeting notes" in clause_lower or "save the file in documents" in clause_lower:
            notes_text = write_note_match.group(1).strip() if (write_note_match and write_note_match.group(1).strip()) else "Meeting Notes: Discussed AI Desktop Automation upgrades."
            return TaskItem(
                id=task_id,
                title="Write Meeting Notes in Notepad",
                intent="write_note",
                application="notepad",
                data={"text": notes_text, "filename": "meeting_notes.txt", "folder": "Documents"},
                risk_level="low",
                status=TaskStatus.PENDING
            ), "notepad"


        # 4. Summarization Intent (Standalone step)
        if should_summarize:
            query = self.conversation_context.get("last_query") or "the search results"
            return TaskItem(
                id=task_id,
                title=f"Summarize results for '{query}'",
                intent="summarize_results",
                query=query,
                risk_level="low",
                status=TaskStatus.PENDING
            ), current_app_context

        # 5. Screenshot Intent
        if any(w in clause_lower for w in ["screenshot", "screen capture", "screen snapshot", "photo"]):
            return TaskItem(
                id=task_id,
                title="Capture Desktop Screenshot",
                intent="take_screenshot",
                risk_level="low",
                status=TaskStatus.PENDING
            ), current_app_context

        # 6. Fallback generic task
        return TaskItem(
            id=task_id,
            title=clause_clean,
            intent="generic_command",
            query=clause_clean,
            risk_level="low",
            status=TaskStatus.PENDING
        ), current_app_context

    def _build_message_task(self, task_id: str, contact: str, message: str) -> Tuple[TaskItem, str]:
        clean_contact = contact.strip()
        clean_msg = message.strip()
        self.conversation_context["last_contact"] = clean_contact

        return TaskItem(
            id=task_id,
            title=f"Send WhatsApp message to {clean_contact}",
            intent="send_message",
            application="whatsapp",
            contact=clean_contact,
            message=clean_msg,
            requires_confirmation=True,
            risk_level="medium",
            status=TaskStatus.PENDING
        ), "whatsapp"

    def _handle_conversational_follow_up(self, text: str, plan_id: str) -> Optional[TaskPlan]:
        """
        Handles contextual follow-up requests such as:
        - "Now search deep learning"
        - Resolving ambiguity selection: "1", "2", "Ram Sharma"
        - Confirmation responses: "Yes", "Send it", "Confirm", "Cancel"
        """
        clean = text.lower().strip()

        # 1. Ambiguity resolution if waiting for user choice
        ambiguity_ctx = self.conversation_context.get("awaiting_ambiguity")
        if ambiguity_ctx:
            candidates = ambiguity_ctx.get("candidates", [])
            selected_contact = None

            # Check if user said "1", "first", "2", "second", etc.
            if clean in ["1", "first", "pehla", "one"] and len(candidates) >= 1:
                selected_contact = candidates[0]
            elif clean in ["2", "second", "doosra", "two"] and len(candidates) >= 2:
                selected_contact = candidates[1]
            elif clean in ["3", "third", "teesra", "three"] and len(candidates) >= 3:
                selected_contact = candidates[2]
            else:
                # Check if user spoke the full name
                for c in candidates:
                    if c["name"].lower() in clean or clean in c["name"].lower():
                        selected_contact = c
                        break

            if selected_contact:
                # Ambiguity successfully resolved!
                self.conversation_context["awaiting_ambiguity"] = None
                task_item = TaskItem(
                    id=ambiguity_ctx.get("task_id", "task_resolved"),
                    title=f"Send WhatsApp message to {selected_contact['name']}",
                    intent="send_message",
                    application="whatsapp",
                    contact=selected_contact["name"],
                    phone=selected_contact["phone"],
                    message=ambiguity_ctx.get("message", "Hi"),
                    requires_confirmation=True,
                    risk_level="medium",
                    status=TaskStatus.WAITING_CONFIRMATION
                )
                plan = TaskPlan(
                    plan_id=plan_id,
                    original_instruction=text,
                    tasks=[task_item],
                    status="waiting_confirmation",
                    requires_confirmation=True,
                    confirmation_id=uuid.uuid4().hex[:6],
                    summary=f"Resolved contact: {selected_contact['name']} ({selected_contact['phone']}). Waiting for confirmation to dispatch."
                )
                self.pending_confirmation_plan = plan
                return plan

        # 2. Contextual search follow-up: "now search X", "search X also"
        now_search_match = re.match(
            r"^(?:now|then|next|aur)\s+(?:search\s+for|search|google)\s+(.+)$",
            clean,
            re.IGNORECASE
        )
        if now_search_match:
            new_query = now_search_match.group(1).strip()
            self.conversation_context["last_query"] = new_query
            task_item = TaskItem(
                id="task_1",
                title=f"Search Google for '{new_query}'",
                intent="search_web",
                application="chrome",
                query=new_query,
                risk_level="low",
                status=TaskStatus.PENDING
            )
            return TaskPlan(
                plan_id=plan_id,
                original_instruction=text,
                tasks=[task_item],
                status="created",
                summary=f"Follow-up search for '{new_query}' in Google Chrome."
            )

        return None


task_planner = TaskPlanner()
