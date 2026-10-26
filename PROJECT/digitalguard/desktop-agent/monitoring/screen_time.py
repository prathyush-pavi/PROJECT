"""
DigitalGuard Desktop Agent — Screen Time Tracker
"""

import time
import datetime
import logging
from typing import Dict, Any

logger = logging.getLogger("digitalguard.desktop.screentime")


class ScreenTimeTracker:
    """
    Accumulates active foreground application screen time on Windows.
    Discounts idle intervals.
    """

    def __init__(self):
        self.current_date = datetime.date.today().isoformat()
        self.app_seconds: Dict[str, float] = {}
        self.total_active_seconds: float = 0.0
        self.last_tick_time: float = time.time()
        self.current_app: str = "Desktop"

    def _check_date_rollover(self):
        today = datetime.date.today().isoformat()
        if today != self.current_date:
            logger.info("Screen time date rollover detected: %s -> %s", self.current_date, today)
            self.current_date = today
            self.app_seconds.clear()
            self.total_active_seconds = 0.0

    def record_activity(self, app_name: str, is_idle: bool):
        """
        Record elapsed time for the active application since last tick.
        If user is marked idle, time is not accumulated towards active screen time.
        """
        now = time.time()
        elapsed = max(0.0, min(now - self.last_tick_time, 10.0))  # clamp spikes
        self.last_tick_time = now

        self._check_date_rollover()

        if is_idle:
            return

        clean_app = app_name.strip() or "System"
        self.app_seconds[clean_app] = self.app_seconds.get(clean_app, 0.0) + elapsed
        self.total_active_seconds += elapsed
        self.current_app = clean_app

    def get_summary(self) -> Dict[str, Any]:
        """
        Returns summary formatted for backend ingestion:
        - date: YYYY-MM-DD
        - total_minutes: int
        - app_breakdown: { "chrome.exe": 35, ... } (in minutes)
        """
        self._check_date_rollover()

        total_minutes = int(round(self.total_active_seconds / 60.0))
        breakdown = {
            app: int(round(sec / 60.0))
            for app, sec in self.app_seconds.items()
            if sec >= 30  # at least 30 seconds
        }

        return {
            "date": self.current_date,
            "total_minutes": total_minutes,
            "app_breakdown": breakdown,
            "current_app": self.current_app,
        }
