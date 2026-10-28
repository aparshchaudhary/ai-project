# Aura AI Voice Command Assistant 🎙️⚡

An intelligent, modern, production-grade **AI-Based Desktop Voice Command Assistant** built with Python (FastAPI, SQLAlchemy, PyTTSx3, SpeechRecognition) and React (TypeScript, Tailwind CSS, Lucide icons, Canvas Waveform Visualizer).

Aura allows users to control their computer, launch and manage applications, search files, automate the web, inspect live system hardware health, capture timestamped screenshots, set and receive voice reminders, and engage in conversational AI dialogues through natural voice commands in both **English and Hindi (Hinglish)**.

---

## 🌟 Key Features

1. **Dual Voice Activation Modes**:
   - **Push-to-Talk**: Click the animated reactive microphone or press the trigger.
   - **Wake-Word Detection**: Continuous listening for `"Hey Assistant"` or custom wake words.
   - **Hybrid Keyboard Input**: Fallback text bar for silent or noisy environments.

2. **Secure Intent-Driven Pipeline**:
   ```
   Voice / Text
        ↓
   Speech-to-Text (Whisper / Google STT / Web Speech API)
        ↓
   Natural Language Intent Classification & Entity Extraction
        ↓
   Safety Validator & Sandbox Check
        ↓
   Permission Layer (Low / Med / High Risk Confirmation)
        ↓
   Predefined Function Execution (No arbitrary shell scripts)
        ↓
   Text-to-Speech (pyttsx3 / Web Audio) & Audit Log
   ```

3. **Desktop Automation & Configurable App Registry**:
   - Pre-configured applications: Chrome, Microsoft Edge, Mozilla Firefox, VS Code, Notepad, Calculator, File Explorer, Terminal, Spotify, Discord, Task Manager, Settings.
   - Auto-discovers Windows paths (`C:\Program Files`, `AppData`, `PATH`).
   - In-app GUI to register custom desktop applications and executable paths.
   - Safely closes target processes by name without affecting other software.

4. **Web Automation**:
   - Natural queries: `"Search Google for machine learning"`, `"Search YouTube for Python tutorials"`, `"Search Wikipedia for quantum computing"`.
   - Opens verified HTTPS URLs in default browser safely.

5. **Bounded File & Folder Management**:
   - Natural commands: `"Find my Python files"`, `"Find all PDF files"`, `"Create a folder called College Projects"`, `"Create a file named notes.txt"`.
   - Bounded path security: strictly prevents directory traversal outside safe user directories (`Desktop`, `Documents`, `Downloads`).
   - High-risk confirmation dialog before any file deletion.

6. **System Control & Telemetry**:
   - Live hardware status: CPU usage (logical cores), RAM usage (GB used/total), Disk usage, Battery percentage & charging state, OS platform, Uptime.
   - Windows volume control: Volume up, Volume down, Mute/Unmute.
   - Workstation security: Lock screen (`LockWorkStation`), Sleep mode, Shutdown, Restart (with explicit confirmation dialog).

7. **Timestamped Screenshot Capture**:
   - `"Take a screenshot"` / `"Capture my screen"`.
   - Automatically saves high-res PNG to `screenshots/screenshot_YYYY-MM-DD_HH-MM-SS.png`.
   - In-app gallery and button to open the local folder in Windows File Explorer.

8. **Automated Reminder Hub**:
   - Natural time parsing: `"Remind me to study at 8 PM"`, `"Remind me tomorrow at 10 AM to submit assignment"`, `"Remind me in 15 minutes"`.
   - SQLite persistence with background async monitor.
   - Automatic spoken voice announcement and WebSocket alerts when due.
   - Supports daily recurring reminders.

9. **Weather & Live Information**:
   - Free meteorological forecast query via wttr.in with city detection.
   - Clear indicators showing when data originates from an external service.
   - Graceful offline fallback.

10. **Multimedia & Music Controls**:
    - Media controls via simulated Windows media keys: Play, Pause, Next Track, Previous Track.

11. **Clipboard Assistant with Privacy Guard**:
    - Safe clipboard reading (`"Read my clipboard"`), writing (`"Copy this text"`), and clearing.
    - Toggleable privacy switch in Settings preventing unauthorized clipboard memory access.

12. **Multilingual (English + Hindi / Hinglish)**:
    - `"Chrome kholo"` → Launches Chrome.
    - `"Screenshot lo"` → Captures screen.
    - `"Kya samay hua hai?"` → Tells current time.
    - `"Folder banao College Projects"` → Creates directory.

13. **AI Conversation Mode**:
    - Open-ended educational queries (`"Explain machine learning"`, `"What is Python?"`, `"Help me prepare for my interview"`, `"Tell me a joke"`).
    - Intelligent built-in offline responses + optional OpenAI GPT-4o-mini integration.

14. **Presentation Demo Mode**:
    - Showcase bar with 10 pre-curated demo commands for class presentations and viva exams.
    - Simulates high-risk actions safely without endangering the presentation system.

15. **Full Audit History & Analytics**:
    - Searchable history table with latency (ms), intent chips, risk tags, and single/batch deletion.
    - Interactive SVG telemetry charts: Daily command volume, most-used intents, top applications, success rate.

---

## 🏗️ Project Architecture

```
voice-assistant/
│
├── backend/
│   ├── main.py                  # FastAPI server, WebSockets, Lifespan hooks
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py          # App configuration, paths, thresholds
│   ├── database/
│   │   ├── __init__.py
│   │   ├── database.py          # SQLAlchemy SQLite connection
│   │   └── models.py            # CommandHistory, Reminder, AppRegistry, AppSetting
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py           # Pydantic request & response models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── speech_service.py    # Speech-to-Text abstraction & wake word engine
│   │   ├── tts_service.py       # Thread-safe pyttsx3 offline TTS & audio renderer
│   │   ├── nlp_service.py       # NLU Intent classification & context memory
│   │   ├── security_service.py  # Risk assessment, confirmation tokens & sandboxing
│   │   ├── automation_service.py# App registry launcher & safe web browser automation
│   │   ├── file_service.py      # Bounded file search, creation, and deletion
│   │   ├── system_service.py    # psutil hardware metrics, volume & power states
│   │   ├── screenshot_service.py# PIL ImageGrab timestamped screenshots
│   │   ├── reminder_service.py  # SQLite reminders with background async monitor
│   │   ├── clipboard_service.py # pyperclip assistant with privacy guard
│   │   ├── weather_service.py   # Meteorological API & offline fallback
│   │   ├── music_service.py     # Windows media key simulations
│   │   ├── analytics_service.py # Telemetry aggregation & latency metrics
│   │   └── command_service.py   # Master orchestrator
│   └── api/
│       ├── __init__.py
│       ├── routes.py            # REST API endpoints
│       └── websocket.py         # Real-time WebSocket connection manager
│
├── frontend/
│   ├── src/
│   │   ├── components/          # CentralMic, VoiceWaveform, Header, Sidebar, ConfirmationModal, DemoBar
│   │   ├── hooks/               # useVoiceRecognition, useWebSocket
│   │   ├── pages/               # Dashboard, AssistantView, History, Reminders, Apps, Analytics, Settings, Help
│   │   ├── services/            # api.ts
│   │   ├── types/               # TypeScript interfaces
│   │   ├── App.tsx              # Root component
│   │   └── main.tsx
│   ├── dist/                    # Compiled production static bundle
│   ├── tailwind.config.js
│   └── package.json
│
├── tests/
│   └── test_assistant.py        # 8 comprehensive pytest unit & integration tests
├── data/                        # SQLite database and persisted storage
├── screenshots/                 # Captured screen recordings
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment configuration template
├── README.md                    # Documentation
└── run.py                       # Single-command launcher script
```

---

## ⚡ Quick Start / How to Run Locally

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** & npm (already compiled into `frontend/dist`)

### Step 1: Install Python Dependencies
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate

pip install -r requirements.txt
```

### Step 2: Run the Application
Simply execute the root launcher script:
```bash
python run.py
```

The application will start the backend server and automatically open the modern dashboard in your default browser at:
👉 **`http://127.0.0.1:8000`**

### Optional CLI Arguments:
```bash
python run.py --port 8080        # Run on a different port
python run.py --no-browser       # Run headless without opening browser
python run.py --reload           # Enable auto-reloading during development
```

---

## 🧪 Running Unit & Integration Tests

The test suite validates intent parsing, entity extraction, context awareness, security permission tiers, time parsing, hardware status, and end-to-end API routes:

```bash
python -m pytest tests/test_assistant.py -v
```

All 8 tests pass with full coverage:
- `test_nlp_intent_classification` ✅
- `test_security_risk_levels` ✅
- `test_context_awareness_followup` ✅
- `test_reminder_time_parser` ✅
- `test_system_status` ✅
- `test_command_execution_pipeline` ✅
- `test_high_risk_requires_confirmation_flow` ✅
- `test_api_endpoints` ✅

---

## 🔒 Security Architecture

1. **No Arbitrary Shell Command Execution**:
   - The AI and NLU layers never execute raw shell strings (`cmd.exe /c ...` or arbitrary bash commands).
   - Only mapped, predefined Python functions in `command_service.py` are executed.

2. **Three-Tier Permission Layer**:
   - **Low-Risk** (Executed automatically):
     `open_application`, `search_web`, `open_website`, `take_screenshot`, `get_time`, `get_date`, `weather`, `system_information`, `play_music`, `volume_control`, `help`, `conversation`.
   - **Medium-Risk** (Configurable confirmation):
     `create_folder`, `create_file`, `rename_file`, `move_file`, `clipboard_write`, `clipboard_clear`.
   - **High-Risk** (Strictly requires explicit modal confirmation):
     `delete_file`, `shutdown`, `restart`, `sleep_computer`.

3. **Restricted File Sandbox**:
   - File creation and searches are restricted to user spaces (`Desktop`, `Documents`, `Downloads`, `data/`).
   - Requests targeting system roots (`C:\Windows`, `C:\Program Files`, system DLLs) are rejected automatically.

---

## 🎙️ Supported Voice Commands Reference

| Category | Example Voice Commands | Supported Language |
| :--- | :--- | :--- |
| **Applications** | "Open Chrome", "Launch VS Code", "Open Calculator", "Close Chrome" | English & Hindi |
| **Multilingual** | "Chrome kholo", "Screenshot lo", "Folder banao Project", "Kya samay hua hai?" | Hindi / Hinglish |
| **Web Search** | "Search Google for machine learning", "Search YouTube for Python tutorials" | English |
| **Files & Folders** | "Open my downloads folder", "Create a folder called AI Project", "Find all PDF files" | English |
| **System** | "Show CPU usage", "Show system information", "Take a screenshot", "Volume up", "Lock screen" | English |
| **Power Control** | "Turn off the computer" (Prompts confirmation), "Restart computer" | English & Hindi |
| **Reminders** | "Set a reminder for 8 PM to study", "Remind me in 15 minutes", "Show my reminders" | English |
| **Information** | "What time is it?", "Tell me today's date", "What's the weather today?" | English |
| **Media** | "Play music", "Pause music", "Next track", "Previous track" | English |
| **Clipboard** | "Read my clipboard", "Copy this text", "Clear my clipboard" | English |
| **AI Dialogue** | "Explain machine learning", "What is Python?", "Help me prepare for my interview", "Tell me a joke" | English |

---

## ⚙️ Environment Configuration (`.env`)

```ini
HOST=127.0.0.1
PORT=8000

# Voice settings
WAKE_WORD=hey assistant
WAKE_WORD_ENABLED=true
DEFAULT_LANGUAGE=en

# Text-to-Speech
TTS_ENGINE=pyttsx3
TTS_RATE=180
TTS_VOLUME=0.9

# Security
REQUIRE_CONFIRMATION_HIGH_RISK=true
REQUIRE_CONFIRMATION_MED_RISK=true
CLIPBOARD_PERMISSION_ENABLED=true
DEMO_MODE=false

# Optional Cloud AI
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
```

---

## 🎯 Presentation / Viva Demo Mode

Click the **Demo Showcase Bar** docked at the top of the dashboard to trigger any of the 10 featured showcase tasks instantly:
- Demonstrates application launch
- Demonstrates screenshot capture with instant toast
- Demonstrates live hardware meter inspection
- Demonstrates reminder creation with voice confirmation
- Demonstrates Hinglish multilingual understanding
- Demonstrates safety confirmation intercepting a shutdown request

---

## 📄 License
MIT License. Built for educational and production desktop assistant applications.
