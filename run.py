"""
Aura AI Voice Assistant — Main Entry Point Launcher.
Starts the FastAPI application and opens the desktop dashboard.
"""

import sys
import os
import time
import argparse
import webbrowser
import logging
from pathlib import Path

# Reconfigure stdout for UTF-8 compatibility on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Ensure root directory is on PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from backend.config.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("aura-launcher")


def main():
    parser = argparse.ArgumentParser(description="Aura AI Voice Command Assistant")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to run backend and UI")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open web browser")
    parser.add_argument("--reload", action="store_true", help="Enable hot reload for development")
    args = parser.parse_args()

    app_url = f"http://{args.host}:{args.port}"

    print("=" * 70)
    print("  AURA AI VOICE COMMAND ASSISTANT - DESKTOP SYSTEM")
    print("=" * 70)
    print(f" * Dashboard UI & API:  {app_url}")
    print(f" * WebSocket Endpoint:  ws://{args.host}:{args.port}/ws/assistant")
    print(f" * API Documentation:   {app_url}/docs")
    print(f" * Data Directory:      {settings.data_dir}")
    print(f" * Screenshots Folder:  {settings.screenshots_dir}")
    print(f" * Language Support:    English & Hindi (Hinglish)")
    print(f" * Wake-Word Detection: \"{settings.wake_word}\"")
    print("=" * 70)
    print(" Starting server... Press Ctrl+C to terminate.\n")

    if not args.no_browser:
        import threading
        def open_browser():
            time.sleep(1.2)
            try:
                webbrowser.open(app_url)
            except Exception as e:
                logger.warning(f"Could not automatically open browser: {e}")
        threading.Thread(target=open_browser, daemon=True).start()

    import uvicorn
    uvicorn.run("backend.main:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
