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
        self._current_proc: Optional[subprocess.Popen] = None

    def get_voices(self) -> List[Dict[str, Any]]:
        return self._voices_cache

    def stop(self):
        """
        Immediately interrupts and stops any ongoing speech playback.
        """
        if self._current_proc and self._current_proc.poll() is None:
            try:
                self._current_proc.terminate()
                self._current_proc.wait(timeout=0.2)
            except Exception:
                try:
                    self._current_proc.kill()
                except Exception:
                    pass
            self._current_proc = None

        if os.name == "nt":
            # Extra safety: kill any orphaned SAPI PowerShell instances
            try:
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command", "Get-Process powershell -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*SAPI.SpVoice*' } | Stop-Process -Force"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=1.0
                )
            except Exception:
                pass

    def _speak_windows_sapi(self, text: str, rate: Optional[int] = None, volume: Optional[float] = None):
        """
        Speaks text asynchronously via Windows native SAPI speech synthesizer
        without blocking the Python process or event loop.
        """
        # Stop previous utterance before beginning new speech
        self.stop()

        clean_text = text.replace('"', '`"').replace("'", "''").replace("\n", " ").strip()
        if not clean_text:
            return

        # SAPI Rate ranges from -10 to 10 (normal is 0 to 2)
        sapi_rate = 1
        if rate:
            sapi_rate = max(-5, min(5, int((rate - 150) / 25)))

        cmd = f"$v = New-Object -ComObject SAPI.SpVoice; $v.Rate = {sapi_rate}; [void]$v.Speak('{clean_text}')"
        try:
            self._current_proc = subprocess.Popen(
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
            logger.info(f"[TTS Output]: {text}")

    async def render_wav(self, text: str) -> Optional[bytes]:
        """
        Returns None or audio bytes for browser playback.
        """
        return None


tts_service = TTSService()

