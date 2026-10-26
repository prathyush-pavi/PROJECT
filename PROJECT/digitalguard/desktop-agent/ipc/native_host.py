"""
DigitalGuard Desktop Agent — Windows Native Messaging Host for Chrome / Edge

Implements the Chrome / Chromium Native Messaging Protocol:
Each message is serialized using JSON, UTF-8 encoded, and is preceded with
a 32-bit integer containing the message length in native byte order.
"""

import os
import sys
import json
import struct
import logging

# Ensure binary mode on Windows to avoid CRLF corruption
if sys.platform == "win32":
    import msvcrt
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

try:
    from config import config
except (ImportError, ValueError):
    from ..config import config
from .local_bridge import LocalBridge

logger = logging.getLogger("digitalguard.desktop.native_host")


def read_message() -> dict:
    """Read a native messaging message from stdin."""
    raw_length = sys.stdin.buffer.read(4)
    if len(raw_length) == 0:
        return {}
    message_length = struct.unpack("<I", raw_length)[0]
    message_bytes = sys.stdin.buffer.read(message_length)
    return json.loads(message_bytes.decode("utf-8"))


def send_message(message: dict):
    """Send a native messaging message to stdout."""
    encoded_content = json.dumps(message).encode("utf-8")
    encoded_length = struct.pack("<I", len(encoded_content))
    sys.stdout.buffer.write(encoded_length)
    sys.stdout.buffer.write(encoded_content)
    sys.stdout.buffer.flush()


def run_host():
    """Main loop for native messaging host."""
    bridge = LocalBridge(
        backend_url=config.backend_url,
        device_token=config.device_token,
        ai_engine_url=config.ai_engine_url,
    )

    while True:
        try:
            msg = read_message()
            if not msg:
                break

            msg_type = msg.get("type", "")

            if msg_type == "PING":
                send_message({"type": "PONG", "status": "active", "os": "windows"})

            elif msg_type == "CHECK_URL":
                url = msg.get("url", "")
                # Query local AI Engine first
                res = bridge.analyze_url(url)
                if not res:
                    res = {
                        "category": "safe",
                        "risk_score": 0.0,
                        "confidence": 0.5,
                        "recommended_action": "ALLOW",
                        "inference_mode": "MOCK",
                    }
                send_message({"type": "URL_RESULT", "url": url, "result": res})

            elif msg_type == "ANALYZE_CONTENT":
                text = msg.get("text", "")
                context = msg.get("context", "webpage")
                res = bridge.analyze_text(text, context=context)
                if not res:
                    res = {
                        "category": "neutral",
                        "risk_score": 0.0,
                        "confidence": 0.5,
                        "recommended_action": "ALLOW",
                        "inference_mode": "MOCK",
                    }
                send_message({"type": "CONTENT_RESULT", "result": res})

            else:
                send_message({"type": "ERROR", "message": f"Unknown action: {msg_type}"})

        except Exception as e:
            logger.error("Native host exception: %s", e)
            send_message({"type": "ERROR", "message": str(e)})


if __name__ == "__main__":
    run_host()
