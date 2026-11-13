# Cross-Platform Autonomous Personal AI Agent
## Android + Windows Mesh Architecture, Coordinated Automation, and Setup Guide

This document outlines the architecture, setup, and usage instructions for the **Cross-Platform Autonomous Personal AI Agent** connecting Android smartphones and Windows workstations through a shared intelligent AI orchestrator.

---

## 1. System Architecture

```
User Voice / Text (Phone or Laptop)
                |
                v
  Speech Recognition & NLU Brain
                |
                v
  Central AI Agent Orchestrator (Observe-Plan-Act-Verify Loop)
                |
    +-----------+-----------+
    |                       |
    v                       v
Device Capabilities     Cross-Device DAG
& Mesh Registry         Task Planner
    |                       |
    +-----------+-----------+
                |
      WebSocket / REST Mesh
                |
        +-------+-------+
        |               |
        v               v
 [ANDROID AGENT]  [WINDOWS AGENT]
  Phone Calls      File Explorer
  WhatsApp         Google Chrome
  Contacts Book    VS Code
  Alarms & Clocks  Notepad & Office
  Device Settings  System Diagnostics
  Camera/Gallery   Folder Management
  Notifications    Screenshot Engine
        |               |
        +-------+-------+
                |
                v
      Cross-Device File Relay
   (data/relay/ secure transfer)
                |
                v
    Execution Verification &
     Truthful Status Report
```

### Core Architecture Principles
1. **Shared AI Brain & Orchestration**:
   - The central AI brain understands natural language instructions across English, Hindi, and Hinglish.
   - It performs dynamic capability discovery and assigns tasks to the device that has the required native hardware or OS APIs.
2. **Native Device Execution Nodes**:
   - **Windows Agent (Desktop AI Agent)**: Controls Win32 applications, safe file directories, system hardware metrics, and browser automation.
   - **Android Agent**: Runs natively on Android (Kotlin + Jetpack Compose) using Android system APIs (`CALL_PHONE`, `READ_CONTACTS`, WhatsApp intents, `MediaStore`, `AlarmClock`, `NotificationListenerService`).
3. **No False Simulation**:
   - The cloud backend never pretends to have direct access to local hardware resources. If a device is offline, it reports the real status and offers safe fallbacks (e.g. desktop Web WhatsApp or Phone Link dialer).

---

## 2. Command Capabilities

### Android-Native Commands
- **Calling**:
  - *"Call Dad."*
  - *"Call Mom."*
  - *"Find Rahul in my contacts and call him."*
- **Messaging & Contacts**:
  - *"Find Rahul in my contacts."*
  - *"Open WhatsApp and send Hi to Dad."*
  - *"Tell Rahul that I will reach in 10 minutes."*
- **Hardware & Device Controls**:
  - *"Turn on Bluetooth."* / *"Turn off Bluetooth."*
  - *"Open my phone settings."*
  - *"Set an alarm for 7 AM."*
- **Notifications & Media**:
  - *"Read my notifications."*
  - *"Open my gallery and find yesterday's photos."*
  - *"Open YouTube and play an AI tutorial."*
  - *"Open Spotify and play music."*

### Windows-Native Commands
- **Application Controls**:
  - *"Open File Explorer."*
  - *"Open VS Code."*
  - *"Open Chrome and research AI agents."*
  - *"Open Notepad and write my notes."*
- **File Management**:
  - *"Open my Downloads folder."*
  - *"Create a folder called AI Projects."*
  - *"Find my resume."*
- **System Metrics**:
  - *"Check my laptop's RAM and storage."*
  - *"Check my laptop's battery."*

### Cross-Device Workflows (Coordinated Multi-Step Tasks)
- *"Find my resume on my laptop and send it to Dad on WhatsApp."*
  1. **Windows**: Searches safe folders on the laptop for `resume`.
  2. **Cloud Relay**: Stages `resume.pdf` into `/api/relay/upload` with a secure transfer ID.
  3. **Android**: Downloads document and prompts human confirmation to dispatch via WhatsApp.
- *"Show my laptop's battery status on my phone."*
  1. **Windows**: Queries laptop battery percentage, charging state, and RAM.
  2. **Android**: Dispatches push notification to phone with live laptop metrics.
- *"Find the PDF on my phone and open it on my laptop."*
  1. **Android**: Locates the PDF in phone storage.
  2. **Cloud Relay**: Transfers file to Windows workstation.
  3. **Windows**: Opens PDF in default viewer.
- *"Transfer this file from my laptop to my phone."*
  1. **Windows**: Stages file into relay.
  2. **Android**: Downloads file directly into phone's `Downloads` folder.

---

## 3. Android Agent Setup & Installation

The native Android project is located in `android/`:
- **Language**: Kotlin 2.x
- **UI Toolkit**: Jetpack Compose & Material 3
- **Network**: OkHttp 4.12 WebSocket & Coroutines
- **Target SDK**: Android 15 (API 35), Min SDK: Android 8.0 (API 26)

### How to Build & Run Android App:
1. Open **Android Studio** (Hedgehog or newer).
2. Choose **Open Project** and select `C:\Users\hp\.gemini\antigravity\scratch\voice-assistant\android`.
3. Allow Gradle to sync dependencies.
4. Connect your Android phone via USB with **USB Debugging** enabled (or start an Android Virtual Device).
5. Click **Run 'app'** (`Shift + F10`).
6. On first launch, grant runtime permissions for:
   - Phone Calls (`CALL_PHONE`)
   - Contacts (`READ_CONTACTS`)
   - Media & Photos (`READ_MEDIA_IMAGES` / `READ_EXTERNAL_STORAGE`)
   - Notifications (`POST_NOTIFICATIONS` & Notification Listener access)
7. Enter your Backend URL (default: `https://aura-voice-assistant.onrender.com` or local LAN IP `http://192.168.x.x:8000`).
8. The app connects in the background via `AgentBackgroundService` with a persistent status notification.

---

## 4. Windows Agent (Desktop AI Agent) Setup

1. Double-click `start_assistant.bat` in the project root:
   ```cmd
   start_assistant.bat
   ```
2. The server initializes:
   - Backend: `http://localhost:8000`
   - WebSocket Mesh: `ws://localhost:8000/ws/device/windows/local_windows`
   - Frontend Dashboard: `http://localhost:8000`
3. The **Connected Devices** panel shows your Windows workstation as `ONLINE`.
4. Once your Android smartphone connects, it appears in the device mesh with its battery percentage, RAM status, and capabilities.

---

## 5. Deployment on Render Cloud

The backend is configured for deployment on Render via Docker:
- **Dockerfile**: Builds the React frontend with Vite and runs the FastAPI backend.
- **render.yaml**: Defines the web service runtime and environment variables.

### To Deploy / Update on Render:
```bash
git add .
git commit -m "feat: cross-platform autonomous AI agent with Android and Windows mesh"
git push origin master --tags
```
Render automatically triggers the build and deploys the new orchestrator endpoints:
- WebSocket endpoint: `wss://<your-render-subdomain>.onrender.com/ws/device/{device_type}/{device_id}`
- REST API: `https://<your-render-subdomain>.onrender.com/api/devices`

---

## 6. Security & Human-in-the-Loop Confirmation

To prevent unauthorized actions:
1. **Explicit Confirmation**:
   - Outgoing phone calls require human confirmation.
   - WhatsApp message dispatch requires human confirmation.
   - System modifications (shutdown, sleep, delete file) require explicit user approval.
2. **Safe Directory Allowlist**:
   - File searches and creations are strictly restricted to user directories (`Downloads`, `Documents`, `Desktop`). Path traversal (`../`) is blocked.
3. **Contact Ambiguity Protection**:
   - If multiple contacts match a name (e.g. `Ram Sharma` vs `Ram Kumar`), the agent pauses execution and displays an ambiguity picker.
