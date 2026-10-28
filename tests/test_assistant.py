"""
Comprehensive Unit and Integration Tests for Voice Assistant.
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.nlp_service import nlp_service
from backend.services.security_service import security_service
from backend.services.automation_service import automation_service
from backend.services.reminder_service import reminder_service
from backend.services.system_service import system_service
from backend.services.command_service import command_service

from unittest.mock import AsyncMock
from backend.services.tts_service import tts_service

# Mock out real speaker playback during unit tests
tts_service.speak = AsyncMock()

client = TestClient(app)


def test_nlp_intent_classification():
    # 1. Open Application
    res = nlp_service.parse_intent("Open Chrome")
    assert res.intent == "open_application"
    assert res.entities.get("application") == "chrome"

    # 2. Launch VS Code
    res2 = nlp_service.parse_intent("Launch VS Code")
    assert res2.intent == "open_application"
    assert res2.entities.get("application") == "code"

    # 3. Web Search
    res3 = nlp_service.parse_intent("Search for Python tutorials")
    assert res3.intent == "search_web"
    assert "python" in res3.entities.get("query", "").lower()

    # 4. System Info
    res4 = nlp_service.parse_intent("Show CPU usage")
    assert res4.intent == "system_information"
    assert res4.entities.get("metric") == "cpu"

    # 5. Screenshot
    res5 = nlp_service.parse_intent("Take a screenshot")
    assert res5.intent == "take_screenshot"

    # 6. Hindi / Hinglish command
    res6 = nlp_service.parse_intent("Chrome kholo")
    assert res6.intent == "open_application"
    assert res6.entities.get("application") == "chrome"

    # 7. Conversational Question
    res7 = nlp_service.parse_intent("Explain machine learning")
    assert res7.intent == "conversation"
    assert res7.is_conversation is True
    assert "machine learning" in res7.response_text.lower()


def test_security_risk_levels():
    # Low-risk: Open application
    res_low = nlp_service.parse_intent("Open Notepad")
    risk, req_conf, _ = security_service.assess_risk(res_low)
    assert risk == "low"
    assert req_conf is False

    # High-risk: Shutdown
    res_high = nlp_service.parse_intent("Turn off the computer")
    assert res_high.intent == "shutdown"
    risk_sd, req_conf_sd, prompt = security_service.assess_risk(res_high)
    assert risk_sd == "high"
    assert req_conf_sd is True
    assert prompt is not None

    # High-risk: Delete file
    res_del = nlp_service.parse_intent("Delete file old_notes.txt")
    assert res_del.intent == "delete_file"
    risk_del, req_conf_del, _ = security_service.assess_risk(res_del)
    assert risk_del == "high"
    assert req_conf_del is True


def test_context_awareness_followup():
    session_id = "test_session_context"
    # Step 1: User asks to create a folder called College Projects
    res1 = nlp_service.parse_intent("Create a folder called College Projects", session_id=session_id)
    assert res1.intent == "create_folder"
    nlp_service.get_context(session_id).update(
        intent=res1.intent,
        entities=res1.entities,
        user_text="Create a folder called College Projects",
        response_text="Where should I create it?"
    )

    # Step 2: Follow-up "In Downloads"
    res2 = nlp_service.parse_intent("In Downloads", session_id=session_id)
    assert res2.intent == "create_folder"
    assert res2.entities.get("folder_name") == "College Projects"
    assert res2.entities.get("parent_folder") == "Downloads"


def test_reminder_time_parser():
    dt = reminder_service.parse_due_time("in 30 minutes")
    assert dt > datetime.now()

    dt_evening = reminder_service.parse_due_time("at 8 PM")
    assert dt_evening.hour == 20
    assert dt_evening.minute == 0


def test_system_status():
    status = system_service.get_system_status()
    assert status.cpu_percent >= 0.0
    assert status.cpu_count >= 1
    assert status.memory_total_gb > 0.0
    assert status.os_name is not None


@pytest.mark.asyncio
async def test_command_execution_pipeline():
    # Test low-risk execution: time command
    res = await command_service.process_command("What time is it?", session_id="test_exec")
    assert res.success is True
    assert res.intent == "get_time"
    assert res.requires_confirmation is False
    assert "time is" in res.response_text.lower()


@pytest.mark.asyncio
async def test_high_risk_requires_confirmation_flow():
    # User asks to shutdown computer
    res = await command_service.process_command("Turn off the computer", session_id="test_security")
    assert res.requires_confirmation is True
    assert res.status == "pending_confirmation"
    assert res.confirmation_id is not None

    # Deny confirmation
    denied = await command_service.confirm_and_execute(res.confirmation_id, approved=False)
    assert denied.status == "denied"
    assert "cancelled" in denied.response_text.lower()


def test_api_endpoints():
    # Test GET /api/system/status
    res = client.get("/api/system/status")
    assert res.status_code == 200
    data = res.json()
    assert "cpu_percent" in data
    assert "memory_percent" in data

    # Test GET /api/apps
    res_apps = client.get("/api/apps")
    assert res_apps.status_code == 200
    assert len(res_apps.json()) > 0

    # Test GET /api/help
    res_help = client.get("/api/help")
    assert res_help.status_code == 200
    assert len(res_help.json()) >= 5

    # Test POST /api/command/process
    res_cmd = client.post("/api/command/process", json={"text": "Tell me today's date"})
    assert res_cmd.status_code == 200
    body = res_cmd.json()
    assert body["intent"] == "get_date"
    assert body["success"] is True

    # Test GET /api/history
    res_hist = client.get("/api/history")
    assert res_hist.status_code == 200
    assert len(res_hist.json()) > 0
