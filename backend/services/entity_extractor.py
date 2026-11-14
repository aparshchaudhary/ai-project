"""
Strict Entity Extraction Service.
Extracts contact names, message contents, applications, filenames, folders,
dates, times, and device targets.
Resolves real contact identities locally on authorized device without inventing contact info.
"""

from __future__ import annotations
import re
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from backend.services.contact_service import contact_service

# Canonical application dictionary
APP_CANONICAL = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "browser": "chrome",
    "browsre": "chrome",
    "whatsapp": "whatsapp",
    "whatsapp desktop": "whatsapp",
    "wa": "whatsapp",
    "vs code": "code",
    "vscode": "code",
    "code": "code",
    "visual studio code": "code",
    "notepad": "notepad",
    "calculator": "calculator",
    "calc": "calculator",
    "explorer": "explorer",
    "file explorer": "explorer",
    "spotify": "spotify",
    "youtube": "youtube",
    "settings": "settings",
    "terminal": "terminal",
}


class ExtractedEntities(BaseModel):
    contact_name: Optional[str] = None
    resolved_contact: Optional[Dict[str, Any]] = None
    message_content: Optional[str] = None
    application_name: Optional[str] = None
    file_name: Optional[str] = None
    folder_path: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    device_target: Optional[str] = None
    query: Optional[str] = None
    setting_name: Optional[str] = None
    action_type: Optional[str] = None


class EntityExtractor:
    def extract(self, text: str, intent_hint: Optional[str] = None) -> ExtractedEntities:
        """Extracts and normalizes entities from natural-language instructions."""
        clean = text.strip()
        lower = clean.lower()
        entities = ExtractedEntities()

        # 1. Device Target Extraction
        if any(w in lower for w in ["on my laptop", "on laptop", "on windows", "on my pc", "on pc", "computer"]):
            entities.device_target = "windows"
        elif any(w in lower for w in ["on my phone", "on phone", "on android", "on mobile", "mobile"]):
            entities.device_target = "android"

        # 2. Time Extraction (e.g. "7 AM", "6:30 PM", "5 baje", "in 10 minutes")
        time_match = re.search(r"\b([0-9]{1,2}(?::[0-9]{2})?\s*(?:am|pm|baje))\b", lower)
        if time_match:
            entities.time = time_match.group(1).strip()
        elif "in 10 minutes" in lower:
            entities.time = "in 10 minutes"

        # 3. Date Extraction (e.g. "tomorrow", "yesterday", "today")
        for d in ["tomorrow", "yesterday", "today", "kal", "aaj"]:
            if re.search(rf"\b{d}\b", lower):
                entities.date = d
                break

        # 4. Application Name
        for alias, canon in APP_CANONICAL.items():
            if re.search(rf"\b{re.escape(alias)}\b", lower):
                entities.application_name = canon
                break

        # 5. Contact Name & Message Content (for calling and messaging)
        # Calling patterns: "Call Dad", "Call Rahul", "Dad ko phone karo"
        call_match = re.search(r"\b(?:call|phone|dial|rufe|ruf)\s+([a-zA-Z0-9\s]+?)(?:\s+(?:on|via|with)\s+.*)?$", clean, re.IGNORECASE)
        hi_call = re.search(r"([a-zA-Z0-9\s]+?)\s+(?:ko|nu)\s+(?:call|phone)\s*(?:lagao|karo)?", clean, re.IGNORECASE)
        if hi_call:
            entities.contact_name = hi_call.group(1).strip()
        elif call_match and not any(w in lower for w in ["that", "saying", "message", "notes"]):
            raw_c = call_match.group(1).strip()
            entities.contact_name = re.sub(r"\b(this number|number|him|her|them)\b", "", raw_c, flags=re.IGNORECASE).strip()

        # WhatsApp Message patterns:
        msg_that = re.search(r"\b(?:tell|message|whatsapp)\s+([a-zA-Z0-9\s]+?)\s+(?:saying|that|ki)\s+[\"']?([^\"'\n\r]+)[\"']?", clean, re.IGNORECASE)
        msg_colon = re.search(r"\b(?:send\s+message\s+to|message|tell|whatsapp)\s+([a-zA-Z0-9\s]+?)\s*:\s*[\"']?([^\"'\n\r]+)[\"']?", clean, re.IGNORECASE)
        msg_to = re.search(r"\bsend\s+[\"']?([^\"'\n\r]+?)[\"']?\s+to\s+([a-zA-Z0-9\s]+)", clean, re.IGNORECASE)
        hi_msg = re.search(r"([a-zA-Z0-9\s]+?)\s+ko\s+(?:whatsapp\s+)?(?:message\s+)?(?:bhejo|karo)\s*(?:ki|:)?\s*[\"']?([^\"'\n\r]+)[\"']?", clean, re.IGNORECASE)

        if msg_that:
            entities.contact_name = msg_that.group(1).strip()
            entities.message_content = msg_that.group(2).strip()
        elif msg_colon:
            entities.contact_name = msg_colon.group(1).strip()
            entities.message_content = msg_colon.group(2).strip()
        elif msg_to:
            entities.message_content = msg_to.group(1).strip()
            entities.contact_name = msg_to.group(2).strip()
        elif hi_msg:
            entities.contact_name = hi_msg.group(1).strip()
            entities.message_content = hi_msg.group(2).strip()

        # Clean contact name
        if entities.contact_name:
            entities.contact_name = re.sub(r"\b(on whatsapp|via whatsapp|in contacts|my contacts)\b", "", entities.contact_name, flags=re.IGNORECASE).strip()

        # 6. Local Identity Resolution (never invent phone numbers!)
        if entities.contact_name:
            resolved, _ = contact_service.resolve_contact(entities.contact_name)
            if resolved:
                entities.resolved_contact = resolved
                entities.contact_name = resolved["name"]

        # 7. File Name
        file_m = re.search(r"\b(?:find|search\s+for|open|locate)\s+(?:my\s+|the\s+)?([a-zA-Z0-9_\-\.\s]+?\.(?:pdf|docx|txt|xlsx|pptx|png|jpg)|resume|invoice|budget|notes|report)\b", clean, re.IGNORECASE)
        if file_m and not entities.contact_name:
            entities.file_name = file_m.group(1).strip()

        # 8. Folder Name & Navigation Path
        folder_create = re.search(r"\b(?:folder\s+(?:called|named)|directory\s+(?:called|named))\s+([a-zA-Z0-9_\-\s]+)", clean, re.IGNORECASE)
        folder_nav = re.search(r"\b(?:open\s+(?:my\s+)?|navigate\s+to\s+|go\s+to\s+)(downloads|documents|desktop|music|videos)\b", clean, re.IGNORECASE)
        if folder_create:
            entities.folder_path = folder_create.group(1).strip()
        elif folder_nav:
            entities.folder_path = folder_nav.group(1).strip().lower()

        # 9. Search Web Query
        search_m = re.search(r"\b(?:search\s+for|search\s+about|google|search)\s+[\"']?([^\"'\n\r]+?)[\"']?(?:\s+(?:on|in)\s+(?:google|chrome|youtube))?$", clean, re.IGNORECASE)
        if search_m and not entities.file_name and not entities.contact_name:
            entities.query = search_m.group(1).strip()

        # 10. Hardware Setting & Action
        setting_m = re.search(r"\b(?:turn\s+(on|off)|enable|disable)\s+(bluetooth|wifi|hotspot)\b", lower)
        if setting_m:
            entities.action_type = "on" if "on" in setting_m.group(1) else "off"
            entities.setting_name = setting_m.group(2)

        return entities


entity_extractor = EntityExtractor()
