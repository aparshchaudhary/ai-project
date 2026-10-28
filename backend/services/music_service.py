"""
Music Control Service.
Simulates multimedia keys on Windows and interacts with configured music applications.
"""

import os
import ctypes
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3
KEYEVENTF_KEYUP = 0x0002


class MusicService:
    def _send_media_key(self, vk_code: int) -> bool:
        if os.name != "nt":
            return False
        try:
            user32 = ctypes.windll.user32
            user32.keybd_event(vk_code, 0, 0, 0)
            user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)
            return True
        except Exception as e:
            logger.error(f"Failed to send media key: {e}")
            return False

    def play_pause(self) -> Tuple[bool, str]:
        if self._send_media_key(VK_MEDIA_PLAY_PAUSE):
            return True, "Music toggled play or pause."
        return False, "Could not control media playback."

    def next_track(self) -> Tuple[bool, str]:
        if self._send_media_key(VK_MEDIA_NEXT_TRACK):
            return True, "Skipped to next track."
        return False, "Could not skip track."

    def previous_track(self) -> Tuple[bool, str]:
        if self._send_media_key(VK_MEDIA_PREV_TRACK):
            return True, "Returned to previous track."
        return False, "Could not go to previous track."


music_service = MusicService()
