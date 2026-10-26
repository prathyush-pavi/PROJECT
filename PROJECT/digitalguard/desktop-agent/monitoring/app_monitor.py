"""
DigitalGuard Desktop Agent — Windows Application & Window Monitor

Monitors the active foreground window on Windows using ctypes (user32.dll)
and queries process metadata via psutil.
Includes Windows idle time detection via GetLastInputInfo.
"""

import sys
import time
import logging
from dataclasses import dataclass
from typing import Optional, Tuple

logger = logging.getLogger("digitalguard.desktop.app_monitor")

# Windows API bindings via ctypes
if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.UINT),
            ("dwTime", wintypes.DWORD),
        ]
else:
    user32 = None
    kernel32 = None

try:
    import psutil
except ImportError:
    psutil = None


@dataclass
class WindowEvent:
    app_name: str
    window_title: str
    pid: int
    exe_path: str
    timestamp: float
    is_idle: bool = False


class WindowsAppMonitor:
    """
    Monitors foreground applications, active window titles, and user idle states
    on Microsoft Windows.
    """

    def __init__(self, idle_threshold_seconds: int = 180):
        self.idle_threshold_seconds = idle_threshold_seconds
        self.last_app_name: str = ""
        self.last_window_title: str = ""
        self.last_pid: int = 0
        self.last_event_time: float = time.time()

    def get_idle_duration_seconds(self) -> float:
        """
        Returns the number of seconds since the last keyboard or mouse input
        using Windows GetLastInputInfo.
        """
        if sys.platform != "win32" or not user32:
            return 0.0

        try:
            lii = LASTINPUTINFO()
            lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
            if user32.GetLastInputInfo(ctypes.byref(lii)):
                millis_since_boot = kernel32.GetTickCount()
                idle_millis = millis_since_boot - lii.dwTime
                return max(0.0, idle_millis / 1000.0)
        except Exception as e:
            logger.debug("Failed to calculate idle duration: %s", e)
        return 0.0

    def is_user_idle(self) -> bool:
        return self.get_idle_duration_seconds() >= self.idle_threshold_seconds

    def get_foreground_window_info(self) -> Tuple[int, str, str, str]:
        """
        Retrieves (pid, app_name, window_title, exe_path) for the currently focused window.
        """
        if sys.platform != "win32" or not user32:
            return (0, "UnknownApp.exe", "Mock Active Window", "")

        try:
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return (0, "Idle/Desktop", "", "")

            # Window Title
            length = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            window_title = buf.value

            # Process ID
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            process_id = pid.value

            app_name = "Unknown"
            exe_path = ""

            if psutil and process_id > 0:
                try:
                    proc = psutil.Process(process_id)
                    app_name = proc.name()
                    try:
                        exe_path = proc.exe()
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        exe_path = ""
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    app_name = "System/Protected"

            return (process_id, app_name, window_title, exe_path)

        except Exception as e:
            logger.error("Error inspecting foreground window: %s", e)
            return (0, "Error", "", "")

    def poll(self) -> Optional[WindowEvent]:
        """
        Poll current foreground state.
        Returns a WindowEvent if the user is active, or an idle event if idle threshold met.
        """
        now = time.time()
        idle = self.is_user_idle()

        pid, app_name, title, exe = self.get_foreground_window_info()

        event = WindowEvent(
            app_name=app_name,
            window_title=title,
            pid=pid,
            exe_path=exe,
            timestamp=now,
            is_idle=idle,
        )

        return event
