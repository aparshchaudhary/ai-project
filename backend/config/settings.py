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
    app_name: str = os.getenv("AGENT_NAME", os.getenv("APP_NAME", "Desktop AI Agent"))
    app_version: str = "2.3.0"
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

    # Cloud & Local LLM Provider Integration
    llm_provider: str = os.getenv("LLM_PROVIDER", "openai")  # "openai", "anthropic", "gemini", "groq", "ollama", "mock"
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    llm_temperature: float = 0.1
    llm_timeout_seconds: float = 15.0

    # Custom ML Intent Classifier & Feedback
    ml_models_dir: Path = DATA_DIR / "models"
    active_intent_model_dir: Path = DATA_DIR / "models" / "intent_model_v1"
    ml_intent_confidence_threshold: float = 0.65
    ml_ambiguity_delta_threshold: float = 0.15
    ml_dataset_dir: Path = DATA_DIR / "ml"
    user_feedback_path: Path = DATA_DIR / "ml" / "user_feedback.json"
    retrain_feedback_threshold: int = 10

    @property
    def user_feedback_file(self) -> Path:
        return self.user_feedback_path

    @property
    def dataset_dir(self) -> Path:
        return self.ml_dataset_dir

    @property
    def models_dir(self) -> Path:
        return self.ml_models_dir

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
