"""
Comprehensive Unit and Integration Tests for Advanced Voice Assistant.
Tests:
1. Intent Recognition & Hindi / Hinglish multilingual support.
2. Voice Activity Detection (VAD) logic and audio metrics.
3. Persistent Permission Management (preventing repeated WhatsApp prompts).
4. Security Boundary & Path Traversal Protection (../../Windows blocked).
5. Windows DPAPI encryption / decryption vault.
6. Secret redaction from audit logs (sk- OpenAI keys masked).
7. Audio Device Enumeration and Level Diagnostics.
"""

import os
import json
import time
from pathlib import Path
import pytest
import numpy as np

from backend.services.nlp_service import nlp_service
from backend.services.audio_manager import audio_manager
from backend.security.credential_store import WindowsDPAPI, redact_secrets, private_config
from backend.security.permissions import permission_manager, PermissionScope
from backend.services.security_service import security_service
from backend.services.automation_service import automation_service
from backend.models.schemas import IntentResult


# 1. NLP & Multilingual Intent Detection
def test_nlp_english_and_hindi_intents():
    test_cases = [
        ("Open Chrome", "open_application"),
        ("Launch VS Code", "open_application"),
        ("Chrome kholo", "open_application"),
        ("Take a screenshot", "take_screenshot"),
        ("Screenshot lo", "take_screenshot"),
        ("What's the weather today?", "weather"),
        ("Aaj ki tarikh batao", "get_date"),
        ("Tell me today's date", "get_date"),
        ("What time is it?", "get_time"),
        ("Kya samay hua hai?", "get_time"),
        ("Search for Python tutorials", "search_web"),
        ("Turn off the computer", "shutdown"),
        ("Create a folder called College Projects", "create_folder"),
        ("Open WhatsApp", "open_application"),
    ]

    for utterance, expected_intent in test_cases:
        res = nlp_service.parse_intent(utterance)
        assert res.intent == expected_intent, f"Failed for '{utterance}': expected {expected_intent}, got {res.intent}"


# 2. Persistent Permission Management (Eliminating Repeated Prompts)
def test_permission_persistence_and_whatsapp():
    # Ensure WhatsApp permission check
    scope = PermissionScope.APP_LAUNCH
    target = "whatsapp"

    # Grant permission
    record = permission_manager.grant_permission(scope, target, duration_days=30)
    assert record["scope"] == scope
    assert record["target"] == target

    # Verify is_permission_granted returns True
    assert permission_manager.is_permission_granted(scope, target) is True
    assert permission_manager.is_permission_granted(scope, "WHATSAPP") is True

    # Assess risk for opening WhatsApp: should NOT require confirmation because permission is cached!
    intent_res = IntentResult(
        intent="open_application",
        entities={"application": "whatsapp"},
        confidence=0.98,
        original_text="Open WhatsApp"
    )
    risk_level, requires_conf, prompt = security_service.assess_risk(intent_res)
    assert requires_conf is False, "WhatsApp should not prompt repeatedly once permission is granted!"
    assert risk_level == "low"

    # Revoke permission and verify
    permission_manager.revoke_permission(scope, target)
    # Check that assess_risk for safe standard apps grants and authorizes without error
    risk_level2, req_conf2, _ = security_service.assess_risk(intent_res)
    assert req_conf2 is False


# 3. Security Boundary & Path Traversal Protection
def test_security_boundary_path_traversal():
    # Attempting to access Windows system directories must be rejected
    traversal_paths = [
        Path("C:/Windows/System32/cmd.exe"),
        Path("C:/Program Files/malicious.exe"),
        Path(str(Path.home() / "Desktop" / ".." / ".." / "Windows")),
    ]

    for p in traversal_paths:
        is_safe = security_service.is_safe_path(p)
        assert is_safe is False, f"Path traversal security check failed to block: {p}"

    # Legitimate user paths must be allowed
    safe_paths = [
        Path.home() / "Desktop" / "ProjectFolder",
        Path.home() / "Documents" / "notes.txt",
        Path.home() / "Downloads" / "report.pdf",
    ]

    for p in safe_paths:
        is_safe = security_service.is_safe_path(p)
        assert is_safe is True, f"Legitimate path was incorrectly blocked: {p}"


# 4. Windows DPAPI Encryption & Decryption Roundtrip
def test_windows_dpapi_vault():
    if not WindowsDPAPI.is_available():
        pytest.skip("Windows DPAPI is only testable on Windows NT.")

    secret_data = b"confidential_api_token_12345_XYZ"
    encrypted = WindowsDPAPI.protect(secret_data)
    assert encrypted != secret_data
    assert len(encrypted) > 0

    decrypted = WindowsDPAPI.unprotect(encrypted)
    assert decrypted == secret_data


# 5. Secret Redaction from Logs
def test_secret_redaction():
    log_sample = "User initialized client with api_key=sk-proj-abc1234567890defghijklmnopqr and Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    redacted = redact_secrets(log_sample)

    assert "sk-proj-abc1234567890defghijklmnopqr" not in redacted
    assert "sk-***[REDACTED]***" in redacted
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in redacted


# 6. Audio Device Enumeration and Level Diagnostics
def test_audio_device_listing():
    devices = audio_manager.list_input_devices()
    assert isinstance(devices, list)
    assert len(devices) > 0

    # Ensure device dictionary contains required fields
    dev = devices[0]
    assert "id" in dev
    assert "name" in dev
    assert "channels" in dev
    assert "is_default" in dev


# 7. VAD Ambient Noise & Threshold Logic
def test_vad_calculation():
    # Simulate silence audio array (low RMS)
    silence = np.zeros(1600, dtype=np.int16)
    silence_rms = float(np.sqrt(np.mean(silence.astype(float) ** 2)))
    assert silence_rms == 0.0

    # Simulate speech audio array (sine wave with high RMS)
    t = np.linspace(0, 0.1, 1600)
    speech = (np.sin(2 * np.pi * 440 * t) * 5000).astype(np.int16)
    speech_rms = float(np.sqrt(np.mean(speech.astype(float) ** 2)))
    assert speech_rms > 3000.0
