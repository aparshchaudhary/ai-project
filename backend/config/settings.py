"""
Configuration settings for Voice Assistant.
"""

from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"

DATA_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseModel):
    app_name: str = "Aura AI Voice Assistant"
    app_version: str = "1.0.0"
    host: str = "127.0.0.1"
    port: int = 8000
    base_dir: Path = BASE_DIR
    data_dir: Path = DATA_DIR
    screenshots_dir: Path = SCREENSHOTS_DIR
    db_url: str = f"sqlite:///{DATA_DIR / 'assistant.db'}"

    # Voice & Speech
    wake_word: str = "hey assistant"
    wake_word_enabled: bool = True
    default_language: str = "en"  # "en" or "hi"
    stt_engine: str = "whisper_fallback"  # "whisper_fallback", "browser", "openai"
    
    # Text-to-Speech
    tts_engine: str = "pyttsx3"
    tts_rate: int = 180
    tts_volume: float = 0.9
    tts_voice_id: Optional[str] = None

    # Safety & Permissions
    clipboard_permission_enabled: bool = True
    require_confirmation_high_risk: bool = True
    require_confirmation_med_risk: bool = True
    demo_mode: bool = False

    # Preferences
    default_browser: str = "default"
    default_music_app: str = "default"
    theme: str = "dark"

    # Cloud AI Integration (Optional)
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = "gpt-4o-mini"

    # User Safe Directories
    user_home: Path = Path.home()
    safe_dirs: List[Path] = [
        Path.home() / "Desktop",
        Path.home() / "Documents",
        Path.home() / "Downloads",
        Path.home() / "Music",
        Path.home() / "Videos",
        DATA_DIR,
        SCREENSHOTS_DIR,
    ]


settings = Settings()
