"""
DigitalGuard Desktop Agent — Configuration (Windows Native)
"""

import os
from pathlib import Path
from dataclasses import dataclass, field

AGENT_DIR = Path(__file__).resolve().parent
DATA_DIR = AGENT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class AgentConfig:
    # Backend server settings
    backend_url: str = os.getenv("DIGITALGUARD_BACKEND_URL", "http://127.0.0.1:8000")
    device_token: str = os.getenv("DIGITALGUARD_DEVICE_TOKEN", "550e8400-e29b-41d4-a716-446655440000")

    # Local AI engine settings
    ai_engine_url: str = os.getenv("DIGITALGUARD_AI_ENGINE_URL", "http://127.0.0.1:8765")

    # Monitoring intervals (seconds)
    app_poll_interval: float = 2.0         # Check foreground window every 2s
    screentime_sync_interval: int = 60      # Send screen-time report every 60s
    policy_refresh_interval: int = 120     # Fetch updated policies every 2 mins
    heartbeat_interval: int = 60           # Ingest device heartbeat every 60s
    idle_threshold_seconds: int = 180      # If no input for 3 mins, mark as user idle

    # Persistence
    local_db_path: Path = DATA_DIR / "agent_cache.json"
    log_file_path: Path = DATA_DIR / "desktop_agent.log"

    # Enforcement flags
    kill_blocked_apps: bool = False        # If True, terminate process; if False, minimize/show alert
    show_toast_notifications: bool = True  # Native Windows alerts


config = AgentConfig()
