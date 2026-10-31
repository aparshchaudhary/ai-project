# IMPLEMENTATION_PLAN.md

Branch: `aura-2.0-dev` (git, initial commit = untouched original). The original zip is the backup; nothing is deleted.
Rule for every stage: finish with a report of files changed, features, tests run, **real results**, remaining bugs, how to verify.

## Decisions I'm making by default (tell me if you disagree)
1. **Dev on Python 3.12 + Node 22 LTS.** 3.14/26 only after a dependency check on your machine (BUG_REPORT §5).
2. **API auth:** a random per-launch bearer token. The backend serves the SPA and injects the token, so the app works unchanged; web pages from other origins can't call it. CORS locked to the app's own origin.
3. **Remove the Render/Docker deployment** (or make auth mandatory there). Desktop-only product.
4. **LLM provider interface** with OpenAI first; others are drop-in later. Key stays in the DPAPI vault / env, never in code or logs.
5. **Keep the regex intent layer as the fast path**, add an LLM tool-router behind a typed registry that can only select from allow-listed tools. The model never produces commands.
6. **Alembic** for schema changes, since Parts 3/8/11 need new tables.
7. Prefer few dependencies: PyMuPDF/pypdf, python-docx, openpyxl, python-pptx for extraction; `dateparser` or `dateutil` for time; `tzdata`; Vitest + Testing Library for the frontend. Each is justified when introduced.

## Stages

### Stage 1 — Stabilise & close the holes (do first; nothing else is safe until this lands)
- Fix C5 (imports), pin versions, write `requirements.txt` + `requirements-dev.txt`, load `.env` for real (M11).
- C1/C2/H8: per-launch token auth, CORS lockdown, remove `shell=True`/`os.system`, validate app paths, route REST launches through permissions; delete/guard cloud deploy files.
- C3 + H9/H10: rewrite TTS (no command-string interpolation; utterance IDs, queue, cancel; volume/voice honoured).
- C4 + H1/H2/H3: confirmation bound to ID, spoken yes/no/हाँ/नहीं recognised only while a confirmation is pending, expiry + replay protection, exact-match safe list, "once" vs "30 days" grants, persistent audit table.
- H4: honest screenshot errors; no fake image.
- **Tests added first (red → green):** one regression test per C/H bug above, including the RCE chain, substring grant, spoken-approval, replay, expiry, revocation, TTS-injection string, and stop-then-stale-response.
- Exit criteria: baseline 14 tests still green + new tests green; frontend build green; RCE repro now returns 401/403.

### Stage 2 — Conversation engine + application discovery
Provider interface, history store, language handling, streaming-safe async calls, offline fallback that says it's offline; separate classifier / router / executor / responder. Windows scanner (Program Files ×2, AppData, Start Menu ×2, uninstall registry, PATH), dedupe, aliases, rescan, edit/remove, disambiguation prompt. *Windows-only pieces use injected fakes in tests; real-registry check is on your manual list.*

### Stage 3 — File + screenshot intelligence
Configurable roots with consent, extractors (PDF/DOCX/TXT/CSV/XLSX/PPTX/images), content index, hashing duplicates, page references, summarise/Q&A. Screenshots: real capture or a clear error, region, folder setting, history table, thumbnails, OCR (Tesseract optional), spoken save path.

### Stage 4 — Deep research + knowledge base (RAG)
Needs a search backend. **This is the one I need your input on** (see below). Query generation, fetch/extract, cross-check, report with only real retrieved citations, cancel + progress, PDF/DOCX export. RAG: chunk, embed, store (SQLite + vector index), cited answers, remove/refresh, access control.

### Stage 5 — Voice + reminders
Voice list/preview/rate/volume/pitch, listening/processing/speaking states, pause/resume where SAPI allows, interruption end-to-end test. Reminders: proper parser (tz-aware, "every Monday", relative days, Hinglish), recurrence, snooze, missed handling, toast + sound, works with the UI closed.

### Stage 6 — Desktop automation + productivity
Typed tool registry (pydantic in/out), approved workflows, media, clipboard tools, system notifications; notes, to-dos, Pomodoro, focus mode, daily summary.

### Stage 7 — UI redesign
Router, 14 pages, design tokens (navy/midnight/violet/cyan), glass, light theme, a11y, responsive, toasts, empty states. No button without a working endpoint. Vitest component + API tests.

### Stage 8 — Security review, regression, release
Threat-model pass, dependency audit, regression checklist, docs, `.env.example`, installers/launch scripts, final ZIP, honest known-limitations list.

## Verification policy
- I report only results I actually ran, with the command. Anything needing real Windows hardware is labelled
  "unit-tested, not hardware-verified" and appears on a manual checklist for you.
- A feature is "done" only when an automated test or a recorded manual check exercises it end to end.

## What I need from you before Stage 4 (not before Stage 1)
Which research/search source do you want: a paid API key you already have (Tavily, Brave, SerpAPI, Bing), or a
keyless option (DuckDuckGo HTML scraping — free but fragile and against some terms)? I'll default to a pluggable
interface with Brave/Tavily first if you don't have a preference.
