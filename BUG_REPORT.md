# BUG_REPORT.md — Aura AI baseline audit

Audit date: 2026-11-01. Source: `ai-project-master.zip` (98 files, ~9.5k lines of app code).
Every item is marked **VERIFIED** (I ran code and observed it), **READ** (confirmed from source only,
not executed), or **UNVERIFIED** (suspected; needs the Windows machine to confirm).

## 0. Baseline results (before any change)

| Check | Result |
|---|---|
| `pytest tests` (as shipped) | **0 tests run. 2 collection errors. The backend cannot be imported.** |
| `pytest` after 2 one-line fixes (scratch copy only) | 14 passed, 1 skipped |
| `npm ci && npm run build` (tsc + vite) | Passes. 1919 modules, JS 357 kB (101 kB gzip) |
| `npm run lint` (oxlint) | 0 errors, 43 warnings |
| Frontend tests | None exist; no test runner in package.json |

Test environment: Python 3.12.3, Node 22.22.2 (Linux sandbox). **Your machine has Python 3.14.8 / Node 26.13.0;
I could not test on those versions.** See section 5.

The 14 passing tests cover NLP intent parsing, risk-level assessment, reminder parsing (one happy path),
path traversal, DPAPI/redaction and VAD maths. **No test touches app launching, the apps API, spoken
confirmation, TTS stop, screenshots, file search, or CORS/auth.** Every critical bug below slipped past them.

## 1. CRITICAL

### C1. Unauthenticated remote code execution via the apps API — VERIFIED
`POST /api/apps` stores any `exec_path` (no validation, no auth). `POST /api/apps/launch/{key}` then runs it with
`subprocess.Popen(exec_path, shell=True)` (and `os.system()` when the path starts with `start `) with no permission
check and no confirmation. CORS is `allow_origins=["*"]` with credentials, so **any web page you visit can do this to
127.0.0.1:8000.**
Reproduced in a scratch copy with `TestClient`: register `echo EXECUTED > /tmp/pwned.txt`, launch it → file written;
a pre-flight from `https://evil.example` returned that origin in `Access-Control-Allow-Origin`.
(Ran on Linux; the Windows `start`/`os.system` branch is the same code path, not run.)
Files: `api/routes.py:381-395`, `services/automation_service.py:206,264-294`, `main.py` (CORS).
This also contradicts the file's own header and README.md:214-215 ("No Arbitrary Shell Command Execution") ("without arbitrary shell execution").
**Fix (Stage 1):** remove `shell=True`/`os.system`; validate exec paths (must exist, be .exe/.lnk, not in writable
temp dirs); require a per-session API token on every route; restrict CORS to the app's own origin; route all launches
through the permission system.

### C2. Public deployment config exposes C1 to the internet — READ
`render.yaml` (`autoDeploy: true`, plan free) + `Dockerfile` + `run.py` bind `0.0.0.0` when `PORT`/`RENDER` is set, with
no authentication. **If this repo is connected to Render (or anywhere else), anyone can run commands on that server.
Please check and take it down now; I can't see whether it is live.** A Windows desktop assistant has no reason to ship
a public deployment target; I recommend removing it or gating it behind mandatory auth.

### C3. Shell injection through spoken text in TTS — READ (not executed; needs Windows)
`tts_service._speak_windows_sapi` interpolates response text into a PowerShell `-Command` string, escaping only ASCII
`'` and `"`. PowerShell also treats the typographic quotes U+2018/2019/201A/201B as single quotes, so text containing
them (common in LLM output, file names, reminder titles, web search text) can terminate the string and inject commands.
**Fix:** never build a command string from text; pass text over stdin or a temp file, or use SAPI via `pywin32`/`pyttsx3`.

### C4. Spoken approval is not connected to the pending confirmation — READ
Confirmation only works by the modal buttons calling `/command/confirm` with the ID. A spoken "Yes, allow it" is sent
through `parse_intent` as a fresh command. `ConversationContext.pending_confirmation_id` exists but is **never read or
written** anywhere. Result: voice approval does nothing, which is the exact scenario in your Part 10 example.
Also: `confirm_and_execute` hard-codes `risk_level="high"` for every approved action and `is_demo=False`.

### C5. Backend won't import (baseline blocker) — VERIFIED
`speech_service.py:13` imports only `Optional, Tuple` but uses `Dict`/`Any` → `NameError` at import.
`audio_manager.py:24` calls `logger.warning` inside its `except` before `logger` is defined at line 29 → crashes on any
machine without PortAudio. Either one alone makes the whole app unstartable.

## 2. HIGH

| ID | Bug | Status |
|---|---|---|
| H1 | **Substring auto-grant.** `security_service.assess_risk` matches `s in app_target` against "safe apps", then silently writes a 30-day persistent grant. "open unicode converter" (matches `code`) and "open swap tool" (`wa`) → no prompt, persistent grant. | VERIFIED |
| H2 | **Approving one launch grants 30 days.** `consume_confirmation` always persists `APP_LAUNCH` for 30 days; there is no "just once" vs "always". Grants are keyed on the spoken string, not the resolved executable, so renaming an alias changes what a grant covers. | READ |
| H3 | **Audit log is in memory only**, capped at 200 entries, lost on restart. Spec requires logged permission changes. | READ |
| H4 | **Screenshot fabricates success.** If `ImageGrab` fails it draws a fake blue placeholder PNG and reports "Screenshot captured and saved as screenshot_<timestamp>.png". It also speaks only the timestamped filename, which the spec explicitly forbids. | READ |
| H5 | **Reminder parser returns silently wrong times** (VERIFIED, fixed clock Sat 19:00): `"every monday"` → today 8 PM; `"next friday at 5 pm"` → tomorrow 17:00; `"in 2 days"` → tomorrow 02:00; `"on 5 november at 9 am"` → 05:00; `"half past 7 in the evening"` → 07:00. The first digit in the sentence is taken as the hour; anything unparsed falls back to "+1 hour". The user is told it was scheduled. |
| H6 | **Reminders**: naive local time (no timezone), only `daily` recurrence, no snooze, no missed-reminder handling, no Windows toast or sound (only a WebSocket broadcast, so nothing fires if the UI is closed). | READ |
| H7 | **"Conversation engine" is a stub.** One synchronous OpenAI call inside `parse_intent` (blocks the event loop), single message, no history, 150-token cap, no Hindi/Hinglish handling. Offline mode = 4 canned keyword answers, else "I understand you asked about '…'". Follow-ups work only for tool intents, not chat. | READ |
| H8 | **No API authentication anywhere**, including `POST /api/settings`, which can overwrite the OpenAI key held in process memory. | READ |
| H9 | **Stop-speaking is partial.** Only kills the single tracked PowerShell process. No utterance queue/generation ID, so a response generated before Stop can still be spoken after it. The "kill orphaned SAPI processes" fallback filters on `$_.CommandLine`, which Windows PowerShell 5.1 `Get-Process` doesn't expose, so it is probably a no-op. | READ / UNVERIFIED |
| H10 | `volume` and `voice_id` parameters of `TTSService.speak` are accepted and ignored; pitch absent; `get_voices()` returns one hard-coded fake voice; `render_wav` returns `None`. | READ |

## 3. MEDIUM

- M1. `file_service.search_files` is filename-only `rglob`; no content search, text extraction, hashing, or doc Q&A. Not all scan roots are checked against the permission store.
- M2. `ScreenshotService.open_screenshots_folder` uses `os.startfile` (Windows only; fine on target but untested). No region capture, history table, OCR, search.
- M3. App registry: ~20 hard-coded seed apps; no scanner for Program Files / Start Menu / registry / PATH; `is_available` set once at creation and never refreshed; alias matching and duplicate handling are ad hoc; no "ask which one" on multiple matches.
- M4. `Base.metadata.create_all` only; no migration tool. Schema changes for Parts 3/8/11 need Alembic or a documented reset.
- M5. `CommandHistory.entities_json` stores raw entities (file names, queries) with no redaction.
- M6. Pydantic v2 class-based `Config` deprecated in `schemas.py:66,86`.
- M7. `/screenshots` is mounted as public static files with no auth.
- M8. `requirements.txt` is all `>=` with no upper bounds or lock file; `pytest` is mixed with runtime deps.
- M9. Frontend: 43 lint warnings, including impure `new Date()` in render (`Header.tsx:36`), plus zero tests.
- M11. **`.env` is never loaded** (VERIFIED by grep: no `load_dotenv`/dotenv usage anywhere). `.env.example` documents HOST, PORT, TTS_*, WAKE_WORD, etc., but only `OPENAI_API_KEY` is read, via `os.getenv`, and only if set in the shell. Everything else is hard-coded in `settings.py`.
- M10. `Dockerfile` pins Python 3.11 / Node 20 while the dev machine uses 3.14 / 26, so the project runs on three different stacks.

## 4. Feature gaps against the master prompt (nothing here exists yet)

Application scanner · file content search/RAG · deep research · screenshot gallery/OCR · voice selection/preview ·
wake-word · natural-language recurrence/snooze · knowledge base · productivity centre · 5 of 14 UI pages
(AI Chat, File Center, Research Center, Screenshot Gallery, Productivity Center). Existing pages: Dashboard,
Assistant, Applications, History, Reminders, Permissions, Diagnostics, Analytics, Settings, Help.
Partially there: system monitoring (`system_service`, psutil), media keys (`music_service`, Windows virtual-key
presses only; no playback info), clipboard read, the confirmation modal, DPAPI credential vault, path allowlist.

## 5. Version compatibility (Python 3.14.8 / Node 26.13.0) — UNVERIFIED on those versions

- `SpeechRecognition` imports `aifc` and `audioop`, both **removed in Python 3.13**. The sandbox (3.12) already emits deprecation warnings for them. On 3.14 the import may fail unless a version that depends on `standard-aifc`/`audioop-lts` is installed. Needs checking on your machine.
- `numpy`, `Pillow`, `sounddevice`, `soundfile`, `pyttsx3` need wheels for cp314; I have not confirmed they exist.
- Frontend deps (React 19, Vite 8, TS 6) built fine on Node 22; Node 26 untested. Node 26 is an odd-numbered non-LTS release.
- **Recommendation:** develop on **Python 3.12** and **Node 22 LTS** (or 24 LTS). That is what I tested, and it avoids the above. 3.13/3.14 can be adopted later once the dependency check passes.
