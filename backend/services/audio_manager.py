"""
Audio Hardware Management and Adaptive Voice Activity Detection (VAD).
Provides:
- Hardware microphone enumeration and selection.
- Real-time RMS input level measurement.
- Adaptive Voice Activity Detection (VAD) with ambient noise calibration.
- Speech-start and speech-end detection to avoid fixed delay recording.
"""

import os
import io
import time
import math
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

import numpy as np

try:
    import sounddevice as sd
    import soundfile as sf
except Exception as _e:
    sd = None
    sf = None
    logger.warning(f"Audio hardware libraries (sounddevice/soundfile) not available: {_e}")

from backend.security.credential_store import private_config

logger = logging.getLogger(__name__)



class AudioManager:
    def __init__(self):
        self.sample_rate = 16000
        self.channels = 1
        self.dtype = "int16"

    def list_input_devices(self) -> List[Dict[str, Any]]:
        """
        Lists all available hardware and system input audio devices.
        """
        devices = []
        try:
            raw_devices = sd.query_devices()
            default_input_idx = sd.default.device[0]
            selected_device = private_config.get("audio", "selected_microphone_device")

            for idx, dev in enumerate(raw_devices):
                if dev.get("max_input_channels", 0) > 0:
                    name = dev.get("name", f"Microphone {idx}")
                    host_api = dev.get("hostapi", 0)
                    
                    # Clean up encoding issues in device names if present
                    try:
                        clean_name = name.encode("utf-8", "ignore").decode("utf-8")
                    except Exception:
                        clean_name = name

                    is_default = (idx == default_input_idx)
                    is_selected = (selected_device == idx) if selected_device is not None else is_default

                    devices.append({
                        "id": idx,
                        "name": clean_name,
                        "channels": dev.get("max_input_channels", 1),
                        "default_samplerate": dev.get("default_samplerate", 16000),
                        "host_api": host_api,
                        "is_default": is_default,
                        "is_selected": is_selected
                    })
        except Exception as e:
            logger.error(f"Error enumerating audio devices: {e}")
            # Fallback entry
            devices.append({
                "id": 0,
                "name": "Default System Microphone",
                "channels": 1,
                "default_samplerate": 16000,
                "is_default": True,
                "is_selected": True
            })

        return devices

    def get_selected_device_id(self) -> Optional[int]:
        """
        Retrieves the preferred microphone device ID, validating that it currently exists.
        """
        configured_id = private_config.get("audio", "selected_microphone_device")
        if configured_id is not None:
            try:
                info = sd.query_devices(configured_id)
                if info.get("max_input_channels", 0) > 0:
                    return configured_id
            except Exception:
                logger.warning(f"Configured mic device {configured_id} is no longer available.")

        # Default fallback
        try:
            default_id = sd.default.device[0]
            if default_id is not None and default_id >= 0:
                info = sd.query_devices(default_id)
                if info.get("max_input_channels", 0) > 0:
                    return default_id
        except Exception:
            pass

        # Try device 1 (typically Intel SST microphone array on modern laptops) or first input device
        try:
            for idx, dev in enumerate(sd.query_devices()):
                if dev.get("max_input_channels", 0) > 0:
                    return idx
        except Exception:
            pass

        return None

    def select_microphone_device(self, device_id: int) -> bool:
        """
        Saves user's preferred microphone device to private configuration.
        """
        try:
            info = sd.query_devices(device_id)
            if info.get("max_input_channels", 0) > 0:
                private_config.set("audio", "selected_microphone_device", device_id)
                logger.info(f"Selected microphone device: {device_id} ({info.get('name')})")
                return True
        except Exception as e:
            logger.error(f"Could not select device {device_id}: {e}")
        return False

    def test_input_level(self, device_id: Optional[int] = None, duration: float = 0.25) -> Dict[str, Any]:
        """
        Records a short audio slice and calculates live RMS audio level (0-100%).
        """
        if sd is None:
            return {
                "success": False,
                "error": "Hardware audio recording is not available in headless cloud container. Browser Web Speech is active.",
                "device_id": 0,
                "rms": 0.0,
                "level_percent": 0.0,
                "is_speaking": False
            }
        target_device = device_id if device_id is not None else self.get_selected_device_id()
        try:
            samples = int(duration * self.sample_rate)
            rec = sd.rec(
                samples,
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                device=target_device
            )
            sd.wait()

            audio_data = rec.flatten().astype(float)
            rms = float(np.sqrt(np.mean(audio_data ** 2))) if len(audio_data) > 0 else 0.0

            # Linear to visual percent mapping: 0 to ~4000 RMS -> 0 to 100%
            level_percent = min(100.0, round((rms / 3500.0) * 100.0, 1))

            dev_info = sd.query_devices(target_device) if target_device is not None else {}
            return {
                "success": True,
                "device_id": target_device,
                "device_name": dev_info.get("name", "Unknown"),
                "rms": round(rms, 2),
                "level_percent": level_percent,
                "is_speaking": rms > 500.0
            }
        except Exception as e:
            logger.error(f"Microphone test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "device_id": target_device,
                "rms": 0.0,
                "level_percent": 0.0,
                "is_speaking": False
            }

    def capture_with_vad(
        self,
        device_id: Optional[int] = None,
        max_duration_s: float = 8.0,
        silence_timeout_ms: int = 700,
        min_speech_ms: int = 300,
        energy_threshold: Optional[float] = None
    ) -> Tuple[bool, Optional[bytes], Optional[str], Dict[str, Any]]:
        """
        Captures speech using real-time Voice Activity Detection (VAD).
        - Dynamically calibrates ambient room noise.
        - Detects when the user starts speaking.
        - Automatically cuts the recording when silence > silence_timeout_ms.
        - Avoids fixed delays and prevents UI freezes.
        """
        if sd is None:
            return False, None, "Hardware sounddevice is not supported in cloud container. Please switch to Browser Web Speech mode.", {}

        target_device = device_id if device_id is not None else self.get_selected_device_id()
        start_time = time.time()
        chunk_duration_s = 0.1  # 100ms per analysis chunk
        chunk_samples = int(chunk_duration_s * self.sample_rate)

        # 1. Ambient calibration (200ms)
        ambient_samples = int(0.2 * self.sample_rate)
        try:
            calib_rec = sd.rec(
                ambient_samples,
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                device=target_device
            )
            sd.wait()
            calib_rms = float(np.sqrt(np.mean(calib_rec.flatten().astype(float) ** 2)))
        except Exception as e:
            logger.warning(f"Calibration failed, using default ambient level: {e}")
            calib_rms = 200.0

        configured_thresh = private_config.get("audio", "vad_energy_threshold", 320)
        user_thresh = energy_threshold or configured_thresh
        # Adaptive threshold: ambient plus margin, at least user_thresh
        active_threshold = max(calib_rms * 1.6, float(user_thresh))
        logger.info(f"VAD started. Device={target_device}, Ambient RMS={calib_rms:.1f}, Active Threshold={active_threshold:.1f}")

        audio_chunks = []
        speech_detected = False
        consecutive_speech_chunks = 0
        silence_chunks = 0
        max_silence_chunks = int((silence_timeout_ms / 1000.0) / chunk_duration_s)
        no_speech_timeout_chunks = int(3.5 / chunk_duration_s)  # Give user 3.5s to start speaking
        max_total_chunks = int(max_duration_s / chunk_duration_s)

        total_chunks_recorded = 0

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                device=target_device,
                blocksize=chunk_samples
            ) as stream:
                while total_chunks_recorded < max_total_chunks:
                    chunk, overflowed = stream.read(chunk_samples)
                    total_chunks_recorded += 1
                    audio_chunks.append(chunk)

                    # Compute chunk RMS
                    chunk_float = chunk.flatten().astype(float)
                    chunk_rms = float(np.sqrt(np.mean(chunk_float ** 2)))

                    if not speech_detected:
                        # Waiting for speech to start
                        if chunk_rms >= active_threshold:
                            consecutive_speech_chunks += 1
                            if consecutive_speech_chunks >= 2:
                                speech_detected = True
                                logger.info(f"VAD: Speech detected at {(total_chunks_recorded * chunk_duration_s):.2f}s (RMS={chunk_rms:.1f})")
                        else:
                            consecutive_speech_chunks = 0

                        # Early exit if user didn't speak for 3.5 seconds
                        if total_chunks_recorded >= no_speech_timeout_chunks:
                            logger.info("VAD: No speech detected within initial timeout window.")
                            break
                    else:
                        # Speech is currently active; monitor for end of speech
                        if chunk_rms < active_threshold:
                            silence_chunks += 1
                            if silence_chunks >= max_silence_chunks:
                                logger.info(f"VAD: Silence duration reached ({silence_timeout_ms}ms). Ending capture.")
                                break
                        else:
                            silence_chunks = 0  # Still speaking

        except Exception as e:
            logger.error(f"Error during VAD stream capture: {e}")
            return False, None, f"Microphone error: {str(e)}", {}

        vad_capture_ms = round((time.time() - start_time) * 1000, 1)

        if not speech_detected or len(audio_chunks) == 0:
            return False, None, "No speech detected. Please speak clearly into your microphone.", {
                "vad_capture_ms": vad_capture_ms,
                "speech_detected": False,
                "ambient_rms": round(calib_rms, 1),
                "threshold": round(active_threshold, 1)
            }

        # Combine recorded chunks into single WAV buffer
        full_audio = np.concatenate(audio_chunks, axis=0)
        buf = io.BytesIO()
        sf.write(buf, full_audio, self.sample_rate, format="WAV")
        buf.seek(0)
        wav_bytes = buf.read()
        audio_duration_s = round(len(full_audio) / self.sample_rate, 2)

        metadata = {
            "vad_capture_ms": vad_capture_ms,
            "audio_duration_s": audio_duration_s,
            "speech_detected": True,
            "ambient_rms": round(calib_rms, 1),
            "threshold": round(active_threshold, 1),
            "device_id": target_device
        }

        return True, wav_bytes, None, metadata


audio_manager = AudioManager()
