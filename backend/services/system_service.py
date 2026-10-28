"""
System Information and Control Service.
Provides hardware metrics, volume adjustments, lock, sleep, and power state management.
"""

import os
import sys
import time
import socket
import ctypes
import platform
import subprocess
import logging
from typing import Dict, Any, Tuple, Optional

import psutil
from backend.models.schemas import SystemStatusResponse

logger = logging.getLogger(__name__)

# Windows Virtual Key codes for multimedia
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002


class SystemService:
    def __init__(self):
        self._boot_time = psutil.boot_time()

    def is_online(self) -> bool:
        try:
            # Quick socket probe to Google DNS
            socket.setdefaulttimeout(1.5)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("8.8.8.8", 53))
            s.close()
            return True
        except Exception:
            return False

    def get_system_status(self) -> SystemStatusResponse:
        cpu = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count(logical=True) or 1
        
        vm = psutil.virtual_memory()
        mem_percent = vm.percent
        mem_used_gb = round(vm.used / (1024 ** 3), 2)
        mem_total_gb = round(vm.total / (1024 ** 3), 2)

        try:
            disk = psutil.disk_usage("C:\\" if os.name == "nt" else "/")
            disk_percent = disk.percent
            disk_free_gb = round(disk.free / (1024 ** 3), 2)
            disk_total_gb = round(disk.total / (1024 ** 3), 2)
        except Exception:
            disk_percent = 0.0
            disk_free_gb = 0.0
            disk_total_gb = 0.0

        battery = psutil.sensors_battery()
        bat_percent = battery.percent if battery else None
        bat_charging = battery.power_plugged if battery else None

        uptime = round(time.time() - self._boot_time, 0)
        online = self.is_online()

        return SystemStatusResponse(
            cpu_percent=cpu,
            cpu_count=cpu_count,
            memory_percent=mem_percent,
            memory_used_gb=mem_used_gb,
            memory_total_gb=mem_total_gb,
            disk_percent=disk_percent,
            disk_free_gb=disk_free_gb,
            disk_total_gb=disk_total_gb,
            battery_percent=bat_percent,
            is_charging=bat_charging,
            os_name=platform.system(),
            os_version=f"{platform.release()} ({platform.version()})",
            hostname=platform.node(),
            uptime_seconds=uptime,
            is_online=online
        )

    def format_system_info_speech(self, metric: str = "all") -> str:
        status = self.get_system_status()
        if metric == "cpu":
            return f"Your CPU usage is currently at {status.cpu_percent} percent across {status.cpu_count} logical cores."
        elif metric == "memory":
            return f"RAM usage is {status.memory_percent} percent, using {status.memory_used_gb} gigabytes out of {status.memory_total_gb} gigabytes."
        elif metric == "disk":
            return f"Disk usage on C drive is {status.disk_percent} percent with {status.disk_free_gb} gigabytes free."
        elif metric == "battery":
            if status.battery_percent is not None:
                state = "charging" if status.is_charging else "on battery"
                return f"Battery is at {status.battery_percent} percent and is currently {state}."
            else:
                return "This system is running on continuous desktop AC power."
        else:
            return (
                f"Your system is running {status.os_name}. "
                f"CPU usage is {status.cpu_percent} percent, and memory is at {status.memory_percent} percent."
            )

    def change_volume(self, action: str) -> Tuple[bool, str]:
        if os.name != "nt":
            return False, "Volume control is currently supported on Windows."

        user32 = ctypes.windll.user32
        steps = 5  # Step count to notice effect

        try:
            if action in ["up", "increase"]:
                for _ in range(steps):
                    user32.keybd_event(VK_VOLUME_UP, 0, 0, 0)
                    user32.keybd_event(VK_VOLUME_UP, 0, KEYEVENTF_KEYUP, 0)
                return True, "Volume increased."
            elif action in ["down", "decrease", "lower"]:
                for _ in range(steps):
                    user32.keybd_event(VK_VOLUME_DOWN, 0, 0, 0)
                    user32.keybd_event(VK_VOLUME_DOWN, 0, KEYEVENTF_KEYUP, 0)
                return True, "Volume decreased."
            elif action in ["mute", "unmute"]:
                user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
                user32.keybd_event(VK_VOLUME_MUTE, 0, KEYEVENTF_KEYUP, 0)
                return True, "Volume toggled."
            return False, f"Unknown volume action: {action}"
        except Exception as e:
            return False, f"Failed to adjust volume: {str(e)}"

    def lock_screen(self) -> Tuple[bool, str]:
        if os.name == "nt":
            try:
                ctypes.windll.user32.LockWorkStation()
                return True, "Computer locked."
            except Exception as e:
                return False, f"Could not lock screen: {str(e)}"
        return False, "Screen locking is supported on Windows."

    def sleep_computer(self) -> Tuple[bool, str]:
        if os.name == "nt":
            try:
                # Suspend state command
                subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
                return True, "Putting computer to sleep."
            except Exception as e:
                return False, f"Failed to sleep: {str(e)}"
        return False, "Sleep mode supported on Windows."

    def shutdown(self) -> Tuple[bool, str]:
        if os.name == "nt":
            try:
                # 30 second timer so user has time if needed: shutdown /s /t 30
                subprocess.Popen(["shutdown", "/s", "/t", "30"])
                return True, "Shutting down the computer in 30 seconds. Run 'shutdown /a' in command prompt to abort."
            except Exception as e:
                return False, f"Shutdown command failed: {str(e)}"
        return False, "Shutdown command is supported on Windows."

    def restart(self) -> Tuple[bool, str]:
        if os.name == "nt":
            try:
                subprocess.Popen(["shutdown", "/r", "/t", "30"])
                return True, "Restarting the computer in 30 seconds."
            except Exception as e:
                return False, f"Restart command failed: {str(e)}"
        return False, "Restart command is supported on Windows."


system_service = SystemService()
