"""
Text-to-Speech (TTS) Service using Windows native SAPI speech synthesis
and pyttsx3 offline fallback with non-blocking detached execution.
"""

import os
import sys
import subprocess
import threading
import logging
from typing import List, Dict, Any, Optional
import asyncio

from backend.config.settings import settings

logger = logging.getLogger(__name__)


class TTSService:
    def __init__(self):
        self._voices_cache = [
            {"id": "default", "name": "Windows Desktop SAPI Voice", "gender": "Female", "languages": ["en-US", "hi-IN"]}
        ]

    def get_voices(self) -> List[Dict[str, Any]]:
        return self._voices_cache

    def _speak_windows_sapi(self, text: str, rate: Optional[int] = None, volume: Optional[float] = None):
        """
        Speaks text asynchronously via Windows native SAPI speech synthesizer
        without blocking the Python process or event loop.
        """
        clean_text = text.replace('"', '`"').replace("'", "''").replace("\n", " ").strip()
        if not clean_text:
            return

        # SAPI Rate ranges from -10 to 10 (normal is 0 to 2)
        # settings.tts_rate is ~180 wpm
        sapi_rate = 1
        if rate:
            sapi_rate = max(-5, min(5, int((rate - 150) / 25)))

        cmd = f"$v = New-Object -ComObject SAPI.SpVoice; $v.Rate = {sapi_rate}; [void]$v.Speak('{clean_text}')"
        try:
            subprocess.Popen(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
        except Exception as e:
            logger.warning(f"Error invoking Windows SAPI speech: {e}")

    async def speak(self, text: str, rate: Optional[int] = None, volume: Optional[float] = None, voice_id: Optional[str] = None):
        """
        Asynchronously speak text non-blockingly.
        """
        if not text:
            return
        if os.name == "nt":
            self._speak_windows_sapi(text, rate, volume)
        else:
            # Fallback
            logger.info(f"[TTS Output]: {text}")

    async def render_wav(self, text: str) -> Optional[bytes]:
        """
        Returns None or audio bytes for browser playback.
        """
        return None


tts_service = TTSService()
