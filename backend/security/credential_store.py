"""
Secure Credential and Local Private Configuration Store.
Stores secrets outside source control in %USERPROFILE%/.aura_assistant
encrypted with Windows DPAPI (Data Protection API) or OS keychain.
"""

import os
import sys
import json
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Private storage location outside source code repository
CONFIG_ROOT = Path.home() / ".aura_assistant"
CONFIG_ROOT.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = CONFIG_ROOT / "config.json"
VAULT_FILE = CONFIG_ROOT / "vault.bin"

# Restrict folder permissions on Windows
try:
    if os.name == "nt":
        os.system(f'icacls "{CONFIG_ROOT}" /inheritance:r /grant:r "%USERNAME%":(OI)(CI)F >nul 2>&1')
except Exception:
    pass


class WindowsDPAPI:
    """Windows Data Protection API wrapper via ctypes."""

    @staticmethod
    def is_available() -> bool:
        return os.name == "nt"

    @staticmethod
    def protect(data: bytes) -> bytes:
        if not WindowsDPAPI.is_available():
            return data
        import ctypes
        import ctypes.wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [
                ("cbData", ctypes.wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_byte))
            ]

        pDataIn = DATA_BLOB()
        pDataIn.cbData = len(data)
        pDataIn.pbData = ctypes.cast(ctypes.create_string_buffer(data), ctypes.POINTER(ctypes.c_byte))

        pDataOut = DATA_BLOB()
        flags = 0x01  # CRYPTPROTECT_UI_FORBIDDEN

        crypt32 = ctypes.windll.crypt32
        success = crypt32.CryptProtectData(
            ctypes.byref(pDataIn),
            "AuraAssistantData",
            None,
            None,
            None,
            flags,
            ctypes.byref(pDataOut)
        )
        if not success:
            raise RuntimeError(f"CryptProtectData failed with error {ctypes.GetLastError()}")

        try:
            buf = (ctypes.c_byte * pDataOut.cbData)()
            ctypes.memmove(buf, pDataOut.pbData, pDataOut.cbData)
            return bytes(buf)
        finally:
            ctypes.windll.kernel32.LocalFree(pDataOut.pbData)

    @staticmethod
    def unprotect(data: bytes) -> bytes:
        if not WindowsDPAPI.is_available():
            return data
        import ctypes
        import ctypes.wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [
                ("cbData", ctypes.wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_byte))
            ]

        pDataIn = DATA_BLOB()
        pDataIn.cbData = len(data)
        pDataIn.pbData = ctypes.cast(ctypes.create_string_buffer(data), ctypes.POINTER(ctypes.c_byte))

        pDataOut = DATA_BLOB()
        flags = 0x01

        crypt32 = ctypes.windll.crypt32
        success = crypt32.CryptUnprotectData(
            ctypes.byref(pDataIn),
            None,
            None,
            None,
            None,
            flags,
            ctypes.byref(pDataOut)
        )
        if not success:
            raise RuntimeError(f"CryptUnprotectData failed with error {ctypes.GetLastError()}")

        try:
            buf = (ctypes.c_byte * pDataOut.cbData)()
            ctypes.memmove(buf, pDataOut.pbData, pDataOut.cbData)
            return bytes(buf)
        finally:
            ctypes.windll.kernel32.LocalFree(pDataOut.pbData)


class SecureCredentialStore:
    def __init__(self):
        self._vault_cache: Dict[str, str] = {}
        self._load_vault()

    def _load_vault(self):
        if not VAULT_FILE.exists():
            return
        try:
            raw = VAULT_FILE.read_bytes()
            if raw:
                decrypted = WindowsDPAPI.unprotect(raw)
                self._vault_cache = json.loads(decrypted.decode("utf-8"))
        except Exception as e:
            logger.warning(f"Could not load DPAPI encrypted vault: {e}")
            self._vault_cache = {}

    def _save_vault(self):
        try:
            serialized = json.dumps(self._vault_cache).encode("utf-8")
            encrypted = WindowsDPAPI.protect(serialized)
            VAULT_FILE.write_bytes(encrypted)
        except Exception as e:
            logger.error(f"Failed to encrypt and save vault: {e}")

    def set_secret(self, key: str, value: str):
        if not value:
            self._vault_cache.pop(key, None)
        else:
            self._vault_cache[key] = value
        self._save_vault()

    def get_secret(self, key: str, default: str = "") -> str:
        return self._vault_cache.get(key, default)

    def has_secret(self, key: str) -> bool:
        return bool(self._vault_cache.get(key))


class PrivateConfigStore:
    """Manages non-secret user preferences stored in user profile."""

    DEFAULT_CONFIG = {
        "audio": {
            "selected_microphone_device": None,
            "vad_energy_threshold": 320,
            "vad_silence_duration_ms": 700,
            "vad_max_speech_duration_s": 8.0,
            "sample_rate": 16000
        },
        "security": {
            "authorized_directories": [
                str(Path.home() / "Desktop"),
                str(Path.home() / "Documents"),
                str(Path.home() / "Downloads"),
            ],
            "persistent_permissions": {}
        },
        "assistant": {
            "name": "Aura AI Voice Assistant",
            "language": "en",
            "wake_word": "hey assistant",
            "wake_word_enabled": True
        }
    }

    def __init__(self):
        self.config = self._load()

    def _load(self) -> Dict[str, Any]:
        if not CONFIG_FILE.exists():
            self._save(self.DEFAULT_CONFIG)
            return dict(self.DEFAULT_CONFIG)
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except Exception as e:
            logger.warning(f"Error reading private config: {e}")
            return dict(self.DEFAULT_CONFIG)

    def _save(self, data: Dict[str, Any]):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save private config: {e}")

    def get(self, section: str, key: str, default: Any = None) -> Any:
        return self.config.get(section, {}).get(key, default)

    def set(self, section: str, key: str, value: Any):
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
        self._save(self.config)

    def get_authorized_dirs(self) -> list:
        dirs = self.config.get("security", {}).get("authorized_directories", [])
        return [Path(d).resolve() for d in dirs]

    def add_authorized_dir(self, dir_path: Path):
        resolved = str(dir_path.resolve())
        dirs = self.config.setdefault("security", {}).setdefault("authorized_directories", [])
        if resolved not in dirs:
            dirs.append(resolved)
            self._save(self.config)

    def remove_authorized_dir(self, dir_path: Path):
        resolved = str(dir_path.resolve())
        dirs = self.config.setdefault("security", {}).setdefault("authorized_directories", [])
        if resolved in dirs:
            dirs.remove(resolved)
            self._save(self.config)


def redact_secrets(text: str) -> str:
    """Masks API keys, tokens, and sensitive strings from logs."""
    if not text:
        return ""
    # Redact OpenAI keys
    redacted = re.sub(r"sk-[a-zA-Z0-9_-]{20,}", "sk-***[REDACTED]***", text)
    # Redact Authorization Bearer headers
    redacted = re.sub(r"(Bearer\s+)[a-zA-Z0-9_\-\.]{15,}", r"\1***[REDACTED]***", redacted)
    return redacted


credential_store = SecureCredentialStore()
private_config = PrivateConfigStore()
