"""
Speech-to-Text and Speech Processing Service.
Supports pluggable engines: SpeechRecognition (Google/Whisper/Sphinx/Wav),
OpenAI Whisper API, and Web Speech stream integration.
"""

import os
import io
import wave
import tempfile
import logging
from abc import ABC, abstractmethod
from typing import Optional, Tuple
from pathlib import Path

from backend.config.settings import settings

logger = logging.getLogger(__name__)


class BaseSpeechEngine(ABC):
    @abstractmethod
    def transcribe(self, audio_data: bytes, filename: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """
        Returns (success, transcribed_text, error_message)
        """
        pass


class SpeechRecognitionEngine(BaseSpeechEngine):
    """
    Speech recognition engine leveraging SpeechRecognition library
    with multi-tier fallback (OpenAI Whisper -> Google Web STT -> Offline/WAV processing).
    """

    def __init__(self):
        try:
            import speech_recognition as sr
            self.sr = sr
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = 300
            self.recognizer.dynamic_energy_threshold = True
            logger.info("SpeechRecognition engine initialized successfully.")
        except Exception as e:
            self.sr = None
            self.recognizer = None
            logger.warning(f"SpeechRecognition library could not be loaded: {e}")

    def transcribe(self, audio_data: bytes, filename: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        if not audio_data or len(audio_data) == 0:
            return False, "", "Empty audio data received."

        # If OpenAI API Key is provided, try OpenAI Whisper API first
        if settings.openai_api_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=settings.openai_api_key)
                
                temp_suffix = ".wav"
                if filename and "." in filename:
                    temp_suffix = "." + filename.split(".")[-1]

                with tempfile.NamedTemporaryFile(suffix=temp_suffix, delete=False) as tmp:
                    tmp.write(audio_data)
                    tmp_path = tmp.name

                try:
                    with open(tmp_path, "rb") as audio_file:
                        transcript = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file
                        )
                    os.unlink(tmp_path)
                    return True, transcript.text.strip(), None
                except Exception as api_err:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                    logger.warning(f"OpenAI Whisper API error, falling back: {api_err}")
            except Exception as e:
                logger.warning(f"OpenAI Whisper client failed: {e}")

        # Local SpeechRecognition fallback
        if not self.sr or not self.recognizer:
            return False, "", "Speech recognition engine is not installed."

        try:
            audio_io = io.BytesIO(audio_data)
            try:
                with self.sr.AudioFile(audio_io) as source:
                    audio = self.recognizer.record(source)
            except Exception:
                # If audio is WebM or compressed, try writing to temp file
                temp_ext = ".wav" if not filename else os.path.splitext(filename)[1]
                with tempfile.NamedTemporaryFile(suffix=temp_ext, delete=False) as tmp:
                    tmp.write(audio_data)
                    tmp_path = tmp.name
                
                try:
                    with self.sr.AudioFile(tmp_path) as source:
                        audio = self.recognizer.record(source)
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

            # Try online Google STT (standard free endpoint in speech_recognition)
            try:
                # Language handling (English or Hindi)
                lang = "hi-IN" if settings.default_language == "hi" else "en-US"
                text = self.recognizer.recognize_google(audio, language=lang)
                return True, text.strip(), None
            except self.sr.UnknownValueError:
                return False, "", "Could not understand the spoken audio. Please speak clearly."
            except self.sr.RequestError as req_err:
                logger.warning(f"Online speech service error: {req_err}. Checking offline whisper...")
                # Try offline Whisper if installed
                try:
                    text = self.recognizer.recognize_whisper(audio, model="base")
                    return True, text.strip(), None
                except Exception:
                    return False, "", "Speech service offline and speech could not be recognized."

        except Exception as e:
            logger.error(f"Speech transcription exception: {e}")
            return False, "", f"Speech recognition error: {str(e)}"


class SpeechService:
    def __init__(self):
        self.engine: BaseSpeechEngine = SpeechRecognitionEngine()

    def set_engine(self, engine: BaseSpeechEngine):
        self.engine = engine

    def transcribe_audio(self, audio_bytes: bytes, filename: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        return self.engine.transcribe(audio_bytes, filename)

    def detect_wake_word(self, text: str) -> Tuple[bool, str]:
        """
        Checks if text contains or starts with the configured wake word.
        Returns (has_wake_word, remaining_command)
        """
        if not text:
            return False, ""

        clean = text.strip()
        wake = settings.wake_word.lower()

        lower_text = clean.lower()
        if lower_text.startswith(wake):
            remaining = clean[len(wake):].strip(" ,:.-!?")
            return True, remaining
        
        # Also check common variants like "hey assistant", "assistant"
        variants = ["hey assistant", "ok assistant", "hello assistant", "assistant", "hey aura", "aura"]
        for v in variants:
            if lower_text.startswith(v):
                remaining = clean[len(v):].strip(" ,:.-!?")
                return True, remaining

        return False, clean

    def record_from_hardware_mic(self, duration_seconds: float = 4.0, sample_rate: int = 16000) -> Tuple[bool, str, Optional[str]]:
        """
        Directly captures audio from the system hardware microphone via sounddevice
        and transcribes it into text.
        """
        try:
            import sounddevice as sd
            import soundfile as sf

            recording = sd.rec(int(duration_seconds * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
            sd.wait()

            buf = io.BytesIO()
            sf.write(buf, recording, sample_rate, format='WAV')
            buf.seek(0)
            wav_bytes = buf.read()

            return self.transcribe_audio(wav_bytes, filename="hardware_mic.wav")
        except Exception as e:
            logger.error(f"Hardware mic recording error: {e}")
            return False, "", f"Microphone recording error: {str(e)}"


speech_service = SpeechService()
