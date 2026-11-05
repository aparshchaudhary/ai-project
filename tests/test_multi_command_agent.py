"""
Comprehensive Test Suite for Multi-Command Execution, Task Planning & AI Desktop Agent.
Covers:
1. Multi-intent sentence decomposition (English, Hindi, Hinglish)
2. Dependency graph construction (sequential vs parallel execution)
3. Google Chrome web search automation & summarization
4. Contact book resolution & ambiguity handling (e.g. multiple "Ram"s)
5. Strict WhatsApp security confirmation gating
6. Multitasking failure isolation (skipping dependent steps while independent steps succeed)
7. Contextual follow-up commands ("now search deep learning", contact index selection)
8. REST API endpoints (/api/agent/plan, /api/agent/execute, /api/contacts)
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch
from starlette.testclient import TestClient

from backend.main import app
from backend.models.task_planner_schemas import TaskPlan, TaskItem, TaskStatus
from backend.services.task_planner import task_planner
from backend.services.task_scheduler import task_scheduler
from backend.services.contact_service import contact_service
from backend.services.whatsapp_service import whatsapp_service
from backend.services.browser_automation_service import browser_automation_service
from backend.services.command_service import command_service


client = TestClient(app)


class TestSentenceDecompositionAndPlanning:
    """Tests multi-command sentence splitting and task dependency assignment."""

    def test_english_four_step_instruction(self):
        instruction = "Open Google Chrome and search for Artificial Intelligence, then open WhatsApp and send Hi to Ram."
        plan = task_planner.plan_instruction(instruction)

        assert len(plan.tasks) == 4
        # Step 1: Open Chrome
        assert plan.tasks[0].intent == "open_application"
        assert plan.tasks[0].application == "chrome"
        assert plan.tasks[0].depends_on == []

        # Step 2: Search web for Artificial Intelligence (depends on Chrome)
        assert plan.tasks[1].intent == "search_web"
        assert "Artificial Intelligence" in plan.tasks[1].query
        assert plan.tasks[0].id in plan.tasks[1].depends_on

        # Step 3: Open WhatsApp
        assert plan.tasks[2].intent == "open_application"
        assert plan.tasks[2].application == "whatsapp"

        # Step 4: Send Hi to Ram (requires confirmation, depends on WhatsApp)
        assert plan.tasks[3].intent == "send_message"
        assert plan.tasks[3].contact == "Ram"
        assert plan.tasks[3].message == "Hi"
        assert plan.tasks[3].requires_confirmation is True
        assert plan.tasks[2].id in plan.tasks[3].depends_on

    def test_hinglish_two_step_instruction(self):
        instruction = "Chrome kholo aur AI ke baare mein search karo"
        plan = task_planner.plan_instruction(instruction)

        assert len(plan.tasks) == 2
        assert plan.tasks[0].intent == "open_application"
        assert plan.tasks[0].application == "chrome"

        assert plan.tasks[1].intent == "search_web"
        assert "AI" in plan.tasks[1].query
        assert plan.tasks[0].id in plan.tasks[1].depends_on

    def test_simultaneous_launch_no_dependencies(self):
        instruction = "Open Chrome and WhatsApp simultaneously."
        plan = task_planner.plan_instruction(instruction)

        assert len(plan.tasks) == 2
        # Both independent tasks must have empty depends_on so they run in parallel
        assert plan.tasks[0].depends_on == []
        assert plan.tasks[1].depends_on == []
        apps = {plan.tasks[0].application, plan.tasks[1].application}
        assert "chrome" in apps
        assert "whatsapp" in apps

    def test_search_and_summarize_intent(self):
        instruction = "Search for AI agents and then summarize the results"
        plan = task_planner.plan_instruction(instruction)

        assert len(plan.tasks) >= 1
        search_task = plan.tasks[0]
        assert search_task.intent in ["search_web", "summarize_results"]
        assert "AI agents" in (search_task.query or "")

    def test_open_chrome_an_search_stt_typo_variation(self):
        """Verifies STT variations like 'an', missing conjunctions, or 'Chrome an search what is ai'."""
        variations = [
            "Open Chrome an search what is ai",
            "Open Chrome and search what is ai",
            "Open Chrome search what is ai",
            "Open Chrome, search what is ai",
            "Chrome kholo aur search karo what is ai",
        ]
        for v in variations:
            assert task_planner.is_multi_command(v) is True, f"Failed is_multi_command for: {v}"
            plan = task_planner.plan_instruction(v)
            assert len(plan.tasks) == 2, f"Expected 2 tasks for: {v}, got {len(plan.tasks)}"
            assert plan.tasks[0].intent == "open_application"
            assert plan.tasks[0].application == "chrome"
            assert plan.tasks[1].intent == "search_web"
            assert "what is ai" in plan.tasks[1].query.lower()
            assert plan.tasks[0].id in plan.tasks[1].depends_on



class TestContactServiceAndAmbiguity:
    """Tests contact book lookup, relationship matching, and ambiguity handling."""

    def test_exact_contact_resolution(self):
        matched, ambiguous = contact_service.resolve_contact("Mom")
        assert matched is not None
        assert matched["name"] == "Mom"
        assert len(ambiguous) == 1

    def test_ambiguous_contact_resolution(self):
        # "Ram" matches both "Ram Sharma" and "Ram Kumar"
        matched, ambiguous = contact_service.resolve_contact("Ram")
        assert matched is None  # Must NOT guess one automatically!
        assert len(ambiguous) >= 2
        names = [c["name"] for c in ambiguous]
        assert "Ram Sharma" in names
        assert "Ram Kumar" in names

    def test_whatsapp_service_flags_ambiguity(self):
        prep = whatsapp_service.prepare_message("Ram", "Hello")
        assert prep["success"] is False
        assert prep["status"] == "ambiguous_contact"
        assert prep["ambiguous"] is True
        assert len(prep["contacts"]) >= 2
        assert "Which one would you like to message?" in prep["prompt"]

    def test_whatsapp_service_exact_contact_ready_for_confirmation(self):
        prep = whatsapp_service.prepare_message("Rahul Verma", "Meeting at 5")
        assert prep["success"] is True
        assert prep["status"] == "ready_for_confirmation"
        assert prep["recipient_name"] == "Rahul Verma"
        assert "Shall I send it?" in prep["confirmation_prompt"]


class TestBrowserAutomationService:
    """Tests web search execution, URL construction, and summary extraction."""

    def test_search_url_generation(self):
        with patch("webbrowser.open") as mock_open:
            res = browser_automation_service.execute_search("machine learning", engine="google", summarize=False)
            assert res["success"] is True
            assert "google.com/search?q=" in res["url"]
            assert res["search_type"] == "google_search"

    def test_youtube_search_url(self):
        with patch("webbrowser.open") as mock_open:
            res = browser_automation_service.execute_search("fastapi tutorial", engine="youtube", summarize=False)
            assert res["success"] is True
            assert "youtube.com/results?search_query=" in res["url"]
            assert res["engine"] == "youtube"

    def test_direct_url_recognition(self):
        with patch("webbrowser.open") as mock_open:
            res = browser_automation_service.execute_search("github.com", engine="google", summarize=False)
            assert res["success"] is True
            assert res["url"] == "https://github.com"
            assert res["search_type"] == "direct_url"


@pytest.mark.asyncio
async def test_scheduler_dag_and_failure_isolation():
    """
    Tests multitasking DAG execution and error isolation:
    - Task 1 fails.
    - Task 2 depends on Task 1 -> Must be marked SKIPPED.
    - Task 3 is independent -> Must proceed and complete successfully!
    """
    task1 = TaskItem(
        id="t1",
        title="Failing Task",
        intent="generic_invalid_intent_for_test",
        depends_on=[]
    )
    task2 = TaskItem(
        id="t2",
        title="Dependent on Task 1",
        intent="generic_command",
        depends_on=["t1"]
    )
    task3 = TaskItem(
        id="t3",
        title="Independent Task",
        intent="generic_command",
        depends_on=[]
    )

    plan = TaskPlan(
        plan_id="test_plan_isolation",
        original_instruction="Test DAG error isolation",
        tasks=[task1, task2, task3]
    )

    executed = await task_scheduler.execute_plan(plan)

    assert executed.tasks[0].status == TaskStatus.FAILED
    assert executed.tasks[1].status == TaskStatus.SKIPPED
    assert executed.tasks[2].status == TaskStatus.COMPLETED
    assert executed.status == "partially_failed"


@pytest.mark.asyncio
async def test_conversational_follow_up():
    """Tests context preservation across turns."""
    # First turn: search query
    plan1 = task_planner.plan_instruction("Search Google for quantum computing")
    assert "quantum computing" in plan1.tasks[0].query

    # Second turn: contextual follow up "now search deep learning"
    plan2 = task_planner.plan_instruction("Now search deep learning")
    assert plan2 is not None
    assert plan2.tasks[0].intent == "search_web"
    assert "deep learning" in plan2.tasks[0].query


@pytest.mark.asyncio
async def test_full_command_service_multi_command_flow():
    """Tests end-to-end multi-command dispatch via CommandService."""
    with patch("backend.services.tts_service.tts_service.speak") as mock_speak:
        resp = await command_service.process_command("Open Chrome and WhatsApp simultaneously.")
        assert resp.success is True
        assert resp.intent == "multi_command_plan"
        assert resp.data is not None
        assert len(resp.data["tasks"]) == 2


class TestAgentRestApiEndpoints:
    """Tests REST endpoints for Agent mode, plans, and contacts."""

    def test_plan_endpoint(self):
        res = client.post("/api/agent/plan", json={"text": "Open Chrome and search AI"})
        assert res.status_code == 200
        data = res.json()
        assert "plan_id" in data
        assert len(data["tasks"]) >= 1

    def test_contacts_crud_and_resolve(self):
        # 1. List contacts
        res = client.get("/api/contacts")
        assert res.status_code == 200
        contacts = res.json()
        assert len(contacts) >= 5

        # 2. Add new contact
        res2 = client.post("/api/contacts", json={
            "name": "Ananya Roy",
            "phone": "+919988776655",
            "relationship": "Colleague"
        })
        assert res2.status_code == 200
        created = res2.json()
        assert created["name"] == "Ananya Roy"

        # 3. Resolve single contact
        res3 = client.get("/api/contacts/resolve?q=Ananya")
        assert res3.status_code == 200
        res3_data = res3.json()
        assert res3_data["matched"]["name"] == "Ananya Roy"
        assert res3_data["ambiguous"] is False

        # 4. Resolve ambiguous contact
        res4 = client.get("/api/contacts/resolve?q=Ram")
        assert res4.status_code == 200
        res4_data = res4.json()
        assert res4_data["ambiguous"] is True
        assert res4_data["count"] >= 2

    def test_open_browsre_typo_and_search_ai(self):
        instruction = "open browsre and search ai"
        assert task_planner.is_multi_command(instruction) is True
        plan = task_planner.plan_instruction(instruction)
        assert len(plan.tasks) == 2
        assert plan.tasks[0].intent == "open_application"
        assert plan.tasks[0].application == "chrome"
        assert plan.tasks[1].intent == "search_web"
        assert plan.tasks[1].query.lower() == "ai"

    def test_open_chrome_an_search_what_is_ai(self):
        instruction = "Open Chrome an search what is ai"
        assert task_planner.is_multi_command(instruction) is True
        plan = task_planner.plan_instruction(instruction)
        assert len(plan.tasks) == 2
        assert plan.tasks[0].intent == "open_application"
        assert plan.tasks[0].application == "chrome"
        assert plan.tasks[1].intent == "search_web"
        assert "what is ai" in plan.tasks[1].query.lower()

    def test_calculator_executable_fallback_when_protocol_denied(self):
        from backend.services.desktop_window_manager import DesktopWindowManager
        dwm = DesktopWindowManager()
        # Mock os.startfile to raise PermissionError, verifying subprocess.Popen fallback runs
        with patch("os.startfile", side_effect=PermissionError("Access is denied")):
            with patch("subprocess.Popen") as mock_popen:
                mock_proc = MagicMock()
                mock_proc.pid = 9999
                mock_proc.poll.return_value = None
                mock_popen.return_value = mock_proc
                res = dwm.launch_or_activate("calculator")
                assert res.success is True
                assert res.status in ["Process started", "Window detected", "Already running"]
