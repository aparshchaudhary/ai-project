# Aura AI 2.0 Architecture Specification

## 1. System Overview
Aura AI 2.0 is a Windows-focused desktop AI assistant built on a decoupled architecture:
- Frontend: React 19, TypeScript, Tailwind CSS, Vite.
- Backend: Python FastAPI, SQLAlchemy 2.0, SQLite (WAL mode), Pydantic v2.
- Core Engines: OpenAI GPT-4o Provider Interface, pyttsx3/edge-tts Speech, PyTesseract OCR, ChromaDB Vector RAG, Windows Registry Application Scanner.

## 2. Layered Architecture

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
|  |  - Keyring / Credential Store                                     |  |
|  +-----------------------------------------------------------------+  |
+-----------------------------------------------------------------------+
