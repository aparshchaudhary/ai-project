# Aura AI 2.0 Architecture Specification & System Audit

## 1. System Overview
Aura AI 2.0 is an enterprise-grade, privacy-first desktop voice assistant built on a decoupled architecture designed for high security, low latency, and cross-platform flexibility:
- **Frontend**: React 19, TypeScript 6, Tailwind CSS 3, Vite 8, Lucide Icons, Canvas Waveform Visualizer.
- **Backend**: Python FastAPI, Uvicorn, SQLAlchemy 2.0, SQLite (WAL mode), Pydantic v2.
- **Speech & Audio**: Pluggable SpeechRecognition (Google STT / Whisper / Sphinx / Wav), Adaptive VAD (RMS thresholding with voice-start/voice-end detection), SAPI / pyttsx3 / Web Audio TTS.
- **Security & Sandboxing**: Windows DPAPI hardware encryption (`ctypes` CryptProtectData) with AES-256 fallback, strict directory traversal sandbox, single-use confirmation PINs with TTL expiration.
- **NLP & Multilingual**: Regex & keyword-driven intent classification supporting English and Hindi/Hinglish with conversational fallback.

---

## 2. Target Layered Architecture

```
+-----------------------------------------------------------------------+
|                            REACT 19 FRONTEND                          |
|  [Dashboard] [Live Assistant] [File Center] [Research] [Security] ... |
+------------------------------------+----------------------------------+
                                     | REST API / WebSocket (ws://)
+------------------------------------v----------------------------------+
|                            FASTAPI BACKEND                            |
|  +-----------------------------------------------------------------+  |
|  |                        API ROUTE LAYER                          |  |
|  |  /api/chat  /api/apps  /api/files  /api/research  /api/permissions|  |
|  +--------------------------------+--------------------------------+  |
|                                   |                                   |
|  +--------------------------------v--------------------------------+  |
|  |                     INTENT & NLP ENGINE                         |  |
|  |  - OpenAI GPT-4o / Fallback Provider Interface                   |  |
|  |  - Rule-based Intent Classifier & Keyword Matching               |  |
|  |  - Trilingual Support (English, Hindi, Hinglish)                  |  |
|  +--------------------------------+--------------------------------+  |
|                                   |                                   |
|  +--------------------------------v--------------------------------+  |
|  |                   CONTROLLED TOOL REGISTRY                      |  |
|  |  - App Execution Guard  - File Access Guard  - Permission Check |  |
|  +--------------------------------+--------------------------------+  |
|                                   |                                   |
|  +--------------------------------v--------------------------------+  |
|  |                     CORE SERVICE LAYER                          |  |
|  |  [AppDiscovery] [FileIntelligence] [ResearchEngine] [VoiceTTS]  |  |
|  |  [ScreenshotOCR] [ReminderScheduler] [KnowledgeBase RAG]        |  |
|  +--------------------------------+--------------------------------+  |
|                                   |                                   |
|  +--------------------------------v--------------------------------+  |
|  |                      DATA & STORAGE LAYER                       |  |
|  |  - SQLite Database (SQLAlchemy 2.0 Models)                       |  |
|  |  - Vector Index (ChromaDB / FAISS Embeddings)                    |  |
|  |  - Keyring / DPAPI Credential Store                              |  |
|  +-----------------------------------------------------------------+  |
+-----------------------------------------------------------------------+
```

---

## 3. Baseline Audit & Subsystem Layout (v1.0.0 vs v2.0.0)

### Backend Layout (`backend/`)

| Layer | Files | Role | v2.0 Status |
|---|---|---|---|
| **Entry** | `main.py`, `../run.py` | App factory, CORS, static mounts, SPA fallback, reminder lifespan loop | Production ready |
| **API** | `api/routes.py`, `api/websocket.py` | HTTP REST endpoints, `ws_manager.broadcast` for state & audio streaming | Production ready |
| **Config** | `config/settings.py` | `Settings` pydantic model; persistent configuration | Updated to Pydantic V2 |
| **NLP** | `services/nlp_service.py` | Bilingual intent parser (English + Hindi/Hinglish) + entity extraction | Hardened & tested |
| **Orchestration** | `services/command_service.py` | Command processor, risk assessment, single-use confirmation check, audit log | Patched (no shell=True) |
| **Security** | `services/security_service.py`, `security/permissions.py`, `security/credential_store.py` | Risk levels, pending confirmations (single-use UUID + TTL), DPAPI encryption in `~/.aura_assistant/` | Zero-leakage DPAPI |
| **Services** | `automation_service`, `file_service`, `screenshot_service`, `reminder_service`, `system_service`, `clipboard_service`, `weather_service` | Modular system capabilities with path traversal sandboxing and process safeguards | Fully integrated |
| **Voice** | `speech_service` (STT), `audio_manager` (VAD & hardware device capture), `tts_service` (immediate audio interruption) | Adaptive VAD, streaming Web Speech, headless fallback | Tested on cloud & desktop |
| **Data** | `database/database.py`, `database/models.py` | SQLite tables: `command_history`, `reminders`, `app_registry`, `app_settings` | Thread-safe SQLite |

---

## 4. Voice & Text Command Request Flow

```
Browser Mic / Text ──POST /api/command──▶ command_service.process_command
      │
      ▼
   nlp_service.parse_intent ──▶ IntentResult (English/Hindi/Hinglish)
      │
      ▼
   security_service.assess_risk ──▶ (risk_level, requires_confirmation, prompt)
      ├─ needs_confirm: create_confirmation_request(id) ──▶ returns confirmation_id
      │       UI shows ConfirmationModal / Spoken 4-digit PIN
      │       User Confirms ──▶ POST /api/command/confirm {id, approved}
      │       (Replay-attack safe: single-use token invalidated immediately)
      │
      └─ approved: _execute_approved_intent ──▶ service call ──▶ audit log ──▶ tts_service.speak ──▶ response
WebSocket /ws/assistant broadcasts real-time pipeline status (idle/listening/transcribing/executing/speaking)
```

---

## 5. Security Boundaries: Audit vs. Implementation

| Boundary Feature | As Found (v1.0.0) | Upgraded in Aura AI 2.0 |
|---|---|---|
| **Shell Execution** | Unsafe `shell=True` in app launcher | **Patched**: Parameterized execution via `shlex.split` and allowlist |
| **Confirmation Security** | Static IDs susceptible to replay | **Patched**: Expiring UUIDs with spoken PIN & immediate invalidation |
| **Path Sandbox** | Basic string checking | **Enforced**: Strict resolution of junctions/symlinks; blocks sensitive OS roots |
| **Credential Storage** | Plaintext / environment variables | **Encrypted**: Windows DPAPI hardware encryption in user profile |
| **Headless Deployment** | Crashed on missing sound hardware | **Cloud Safe**: Dynamic hardware fallback for Docker / Render deployment |
