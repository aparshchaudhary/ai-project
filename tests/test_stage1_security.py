import pytest
import time
from backend.security.permissions import permission_manager
from backend.services.command_service import command_executor
from backend.services.speech_service import speech_engine


def test_permission_confirmation_lifecycle():
    conf = permission_manager.create_confirmation_request("launch_app", "calc")
    assert conf.id is not None
    
    success = permission_manager.verify_and_grant(conf.id, approved=True)
    assert success is True
    assert permission_manager.is_granted("launch_app", "calc") is True


def test_permission_replay_prevention():
    conf = permission_manager.create_confirmation_request("launch_app", "calc")
    permission_manager.verify_and_grant(conf.id, approved=True)
    
    replay = permission_manager.verify_and_grant(conf.id, approved=True)
    assert replay is False


def test_command_injection_defense():
    res = command_executor.launch_app("cmd.exe; calc.exe")
    assert res["success"] is False
    assert "not in the security registry" in res["error"]


def test_speech_interruption():
    speech_engine.speak("This is a long sentence that should be interrupted immediately when requested.")
    time.sleep(0.02)
    speech_engine.stop_speaking()
    assert speech_engine._is_speaking is False
    assert speech_engine._speech_queue.empty() is True
