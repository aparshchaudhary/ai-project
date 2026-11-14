"""
Test Suite for LLM Integration, Autonomous AI Agent, Custom ML Intent Inference,
Entity Extraction, and Continuous Improvement Retraining Pipeline.
"""

import json
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.config.settings import settings
from backend.ml.intent_inference import intent_inference_engine
from backend.services.entity_extractor import entity_extractor
from backend.services.llm_provider import llm_service, MockLLMProvider, SYSTEM_AGENT_TOOLS
from backend.services.feedback_service import feedback_service
from backend.ml.retrain_pipeline import retrain_pipeline
from backend.services.autonomous_agent import autonomous_agent

client = TestClient(app)


class TestMLIntentInference:
    """Verifies the custom calibrated ML Intent Classifier across English, Hindi, and Hinglish."""

    def test_open_application_intent(self):
        pred = intent_inference_engine.predict("Open Google Chrome")
        assert pred.intent == "OPEN_APPLICATION"
        assert pred.confidence >= 0.60
        assert not pred.is_ambiguous

    def test_multilingual_hindi_open_app(self):
        pred = intent_inference_engine.predict("Chrome kholo")
        assert pred.intent == "OPEN_APPLICATION"
        assert pred.confidence >= 0.60

    def test_search_web_intent(self):
        pred = intent_inference_engine.predict("Search Google for Artificial Intelligence")
        assert pred.intent == "SEARCH_WEB"
        assert pred.confidence >= 0.60

    def test_call_contact_hinglish(self):
        pred = intent_inference_engine.predict("Dad ko phone karo")
        assert pred.intent == "CALL_CONTACT"
        assert pred.confidence >= 0.60

    def test_send_whatsapp_message_intent(self):
        pred = intent_inference_engine.predict("Send WhatsApp message to Ram saying Hi")
        assert pred.intent == "SEND_WHATSAPP_MESSAGE"
        assert pred.confidence >= 0.60

    def test_search_file_intent(self):
        pred = intent_inference_engine.predict("Find my resume file")
        assert pred.intent == "SEARCH_FILE"
        assert pred.confidence >= 0.60

    def test_create_folder_intent(self):
        pred = intent_inference_engine.predict("Create a folder called AI Projects")
        assert pred.intent == "CREATE_FOLDER"
        assert pred.confidence >= 0.60

    def test_ambiguity_flagging_on_empty_or_gibberish(self):
        pred = intent_inference_engine.predict("xyz123 random words blabla")
        # Either flagged as ambiguous or low confidence
        assert pred.is_ambiguous or pred.confidence < 0.65

    def test_calibrated_probabilities_ranked(self):
        pred = intent_inference_engine.predict("Call Rahul Verma")
        assert len(pred.top_intents) <= 3
        assert pred.confidence == pred.top_intents[0]["confidence"]
        assert 0.0 <= pred.confidence <= 1.0


class TestEntityExtraction:
    """Verifies strict entity extraction and safe contact resolution without hallucination."""

    def test_extract_app_name_and_query(self):
        entities = entity_extractor.extract("Open Chrome and search for Machine Learning")
        assert entities.application_name == "chrome"
        assert "machine learning" in entities.query.lower()

    def test_extract_call_contact_and_resolution(self):
        # "Rahul" is in the database contact list (Rahul Verma)
        entities = entity_extractor.extract("Call Rahul on my phone")
        assert entities.contact_name is not None
        assert "rahul" in entities.contact_name.lower()
        assert entities.device_target == "android"
        assert entities.resolved_contact is not None
        assert entities.resolved_contact.get("phone") is not None

    def test_extract_whatsapp_message(self):
        entities = entity_extractor.extract("Send message to Priya saying Meeting at 5 PM")
        assert "priya" in entities.contact_name.lower()
        assert "meeting at 5 pm" in entities.message_content.lower()

    def test_extract_file_and_folder_entities(self):
        file_ent = entity_extractor.extract("Find my resume.pdf on laptop")
        assert file_ent.file_name == "resume.pdf"
        assert file_ent.device_target == "windows"

        folder_ent = entity_extractor.extract("Create a folder called MachineLearningDocs")
        assert folder_ent.folder_path == "MachineLearningDocs"


class TestLLMProviderAndToolCalling:
    """Verifies LLM Provider abstraction, structured tool definitions, and fallback mechanisms."""

    def test_system_tools_schema_validity(self):
        assert len(SYSTEM_AGENT_TOOLS) >= 5
        tool_names = [t["function"]["name"] for t in SYSTEM_AGENT_TOOLS]
        assert "open_application" in tool_names
        assert "search_web" in tool_names
        assert "make_call" in tool_names
        assert "send_whatsapp_message" in tool_names
        assert "manage_files" in tool_names

    @pytest.mark.asyncio
    async def test_mock_llm_plan_generation(self):
        mock_provider = MockLLMProvider()
        plan = await mock_provider.generate_plan(
            instruction="Open Chrome and search about Artificial Intelligence",
            available_tools=SYSTEM_AGENT_TOOLS,
            context={}
        )
        assert "tasks" in plan
        assert len(plan["tasks"]) == 2
        assert plan["tasks"][0]["tool"] == "open_application"
        assert plan["tasks"][1]["tool"] == "search_web"
        assert plan["tasks"][1]["depends_on"] == ["task_1"]

    @pytest.mark.asyncio
    async def test_llm_service_chat_and_fallback(self):
        response = await llm_service.chat([{"role": "user", "content": "Hello"}])
        assert isinstance(response, str)
        assert len(response) > 0


class TestUserFeedbackAndRetraining:
    """Verifies user correction logging, statistics, and gated retraining pipeline."""

    def test_record_user_correction(self):
        corr = feedback_service.record_correction(
            raw_utterance="Kholo mera chrome",
            predicted_intent="UNKNOWN",
            corrected_intent="OPEN_APPLICATION",
            confidence=0.45,
            is_ambiguous=True,
            verified_by_user=True,
            notes="User confirmed intent should be OPEN_APPLICATION"
        )
        assert corr.raw_utterance == "Kholo mera chrome"
        assert corr.corrected_intent == "OPEN_APPLICATION"
        assert corr.verified_by_user is True

    def test_feedback_stats(self):
        stats = feedback_service.get_stats()
        assert stats["total_feedback_count"] >= 1
        assert "OPEN_APPLICATION" in stats["corrections_by_target_intent"]

    def test_gated_retraining_execution(self):
        # Force retraining to test candidate model training & promotion decision
        result = retrain_pipeline.run_gated_retrain(force=True)
        assert result["status"] in ["SUCCESS", "REJECTED_BELOW_BASELINE"]
        assert "candidate_metrics" in result
        assert result["candidate_metrics"]["accuracy"] >= 0.85


class TestAutonomousAgentOrchestration:
    """Verifies the Observe -> Plan -> Act -> Verify autonomous agent loop."""

    @pytest.mark.asyncio
    async def test_agent_observe_step(self):
        obs = await autonomous_agent.observe("Check laptop status")
        assert obs.raw_input == "Check laptop status"
        assert "ram_percent" in obs.system_metrics
        assert isinstance(obs.connected_devices, list)

    @pytest.mark.asyncio
    async def test_agent_fast_path_plan(self):
        obs = await autonomous_agent.observe("Open Chrome")
        plan = await autonomous_agent.plan(obs)
        assert plan.planner_source == "custom_ml_fast_path"
        assert len(plan.tasks) == 1
        assert plan.tasks[0].tool == "open_application"

    @pytest.mark.asyncio
    async def test_agent_compound_plan_dag(self):
        obs = await autonomous_agent.observe("Open Chrome and search for Deep Learning")
        plan = await autonomous_agent.plan(obs)
        assert len(plan.tasks) >= 2
        assert any(t.tool == "open_application" for t in plan.tasks)
        assert any(t.tool == "search_web" for t in plan.tasks)

    @pytest.mark.asyncio
    async def test_agent_full_run_cycle(self):
        result = await autonomous_agent.run_cycle("Open Calculator")
        assert result["status"] in ["COMPLETED", "WAITING_CONFIRMATION"]
        assert "tasks" in result
        assert len(result["tasks"]) >= 1

    @pytest.mark.asyncio
    async def test_agent_calling_requires_confirmation(self):
        result = await autonomous_agent.run_cycle("Call Rahul on my phone")
        assert result["status"] == "WAITING_CONFIRMATION"
        assert "call" in result["confirmation_prompt"].lower()


class TestAgentAndMLRestEndpoints:
    """Verifies the REST API endpoints for ML inference, feedback, retraining, and autonomous agent."""

    def test_predict_intent_endpoint(self):
        res = client.post("/api/ml/predict-intent", json={"text": "Open Google Chrome"})
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "OPEN_APPLICATION"
        assert "confidence" in data
        assert "top_intents" in data

    def test_user_feedback_and_stats_endpoints(self):
        # 1. Post feedback
        fb_res = client.post("/api/ml/feedback", json={
            "raw_utterance": "Mera resume dhoondo",
            "predicted_intent": "UNKNOWN",
            "corrected_intent": "SEARCH_FILE",
            "confidence": 0.40,
            "verified_by_user": True
        })
        assert fb_res.status_code == 200
        assert fb_res.json()["success"] is True

        # 2. Get stats
        stats_res = client.get("/api/ml/feedback/stats")
        assert stats_res.status_code == 200
        assert stats_res.json()["total_feedback_count"] >= 1

    def test_ml_metrics_endpoint(self):
        res = client.get("/api/ml/metrics")
        assert res.status_code == 200
        data = res.json()
        assert "active_model_version" in data
        assert "metrics" in data
        assert "classes" in data
        assert len(data["classes"]) >= 10

    def test_retrain_endpoint(self):
        res = client.post("/api/ml/retrain", json={"force": True})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] in ["SUCCESS", "REJECTED_BELOW_BASELINE"]

    def test_agent_run_endpoint(self):
        res = client.post("/api/agent/run", json={"instruction": "Check system status"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] in ["COMPLETED", "WAITING_CONFIRMATION"]
        assert "tasks" in data
