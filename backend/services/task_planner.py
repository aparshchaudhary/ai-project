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
            "summarize", "summary", "explain",
            "screenshot", "capture",
            "close", "band karo"
        ]
        for v in verbs:
            if re.search(rf"\b{re.escape(v)}\b", text_lower):
                found_verbs.append(v)

        if ("open" in found_verbs or "launch" in found_verbs or "kholo" in found_verbs) and \
           any(v in found_verbs for v in ["search", "find", "google", "dhoondho", "dhoondo", "khojo", "send", "message", "bhejo", "screenshot"]):
            return True

        return len(found_verbs) >= 2

    def _split_into_candidate_clauses(self, text: str) -> List[str]:
        """
        Splits sentence along conjunctions and action boundaries while respecting quotes.
        """
        # First normalize double spaces and strip trailing punctuation
        clean_text = text.strip().rstrip(".!?,;:")
        normalized = re.sub(r"\s+", " ", clean_text)

        # 1. If user explicitly wrote "Open Chrome and WhatsApp [simultaneously]"
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
            if self._identify_app(app1) and self._identify_app(app2):
                return [f"open {app1}", f"open {app2}"]

        # 2. Split on strong sequential markers first
        parts = re.split(
            r"\b(?:and\s+then|then|after\s+that|aur\s+phir|phir|uske\s+baad|saath\s+hi|ek\s+saath|simultaneously)\b",
            normalized,
            flags=re.IGNORECASE
        )

        compound_action_pat = (
            r"^(?:open|launch|start|run|kholo|chalao)\s+([a-zA-Z0-9\s]+?)\s*"
            r"(?:\b(?:and\s+then|then|after\s+that|and|an|&|aur|phir)\b|,|\s)\s*"
            r"(?:and\s+|an\s+|then\s+)?(search\s+for|search\s+about|search|find|google|look\s+up|dhoondho|dhoondo|khojo|send\s+message|send|message|text|screenshot|take\s+screenshot|write)\b\s*(.*)$"
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
        # 1. Exact or substring match in canonical map
        for alias, canonical in APP_CANONICAL_MAP.items():
            if re.search(rf"\b{re.escape(alias)}\b", clean):
                return canonical

        # 2. Fuzzy match against canonical names and aliases (handles typos like 'browsre', 'chorme')
        import difflib
        tokens = clean.split()
        for tok in tokens:
            matches = difflib.get_close_matches(tok, APP_CANONICAL_MAP.keys(), n=1, cutoff=0.72)
            if matches:
                return APP_CANONICAL_MAP[matches[0]]

        matches = difflib.get_close_matches(clean, APP_CANONICAL_MAP.keys(), n=1, cutoff=0.72)
        if matches:
            return APP_CANONICAL_MAP[matches[0]]

        return None

    def plan_instruction(self, text: str) -> TaskPlan:
        """
        Parses a full multi-command instruction into a structured validated TaskPlan.
        """
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        clean_text = text.strip()

        # Check for contextual follow-up first
        follow_up_plan = self._handle_conversational_follow_up(clean_text, plan_id)
        if follow_up_plan:
            self.last_plan = follow_up_plan
            return follow_up_plan

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
            if task_item.intent == "send_message" and task_item.contact:
                matched, ambiguous = contact_service.resolve_contact(task_item.contact)
                if ambiguous and len(ambiguous) > 1:
                    plan_requires_conf = True
                    ambiguous_contacts_list = ambiguous
                    self.conversation_context["awaiting_ambiguity"] = {
                        "task_id": task_id,
                        "candidates": ambiguous,
                        "message": task_item.message
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

        if hindi_search_match or search_match:
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
