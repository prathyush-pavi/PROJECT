"""
DigitalGuard Desktop Agent — Windows Native Messaging Host Registration

Registers the Native Messaging Host in the Windows Registry for:
- Google Chrome: HKCU\\Software\\Google\\Chrome\\NativeMessagingHosts\\com.digitalguard.agent
- Microsoft Edge: HKCU\\Software\\Microsoft\\Edge\\NativeMessagingHosts\\com.digitalguard.agent
- Brave Browser: HKCU\\Software\\BraveSoftware\\Brave-Browser\\NativeMessagingHosts\\com.digitalguard.agent
"""

import os
import sys
import json
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

HOST_NAME = "com.digitalguard.agent"
AGENT_DIR = Path(__file__).resolve().parent
WRAPPER_BAT = AGENT_DIR / "host_wrapper.bat"
MANIFEST_PATH = AGENT_DIR / f"{HOST_NAME}.json"


def create_manifest():
    manifest_data = {
        "name": HOST_NAME,
        "description": "DigitalGuard Desktop Security & Policy Enforcement Host",
        "path": str(WRAPPER_BAT),
        "type": "stdio",
        "allowed_origins": [
            "chrome-extension://*",
        ],
    }

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    print(f"[✓] Created manifest at: {MANIFEST_PATH}")
    return MANIFEST_PATH


def register_windows_registry():
    if sys.platform != "win32":
        print("[!] Registration only applicable on Windows.")
        return

    import winreg

    registry_targets = [
        r"Software\Google\Chrome\NativeMessagingHosts",
        r"Software\Microsoft\Edge\NativeMessagingHosts",
        r"Software\BraveSoftware\Brave-Browser\NativeMessagingHosts",
    ]

    for target in registry_targets:
        try:
            full_path = f"{target}\\{HOST_NAME}"
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, full_path)
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, str(MANIFEST_PATH))
            winreg.CloseKey(key)
            print(f"[✓] Registered in HKCU\\{full_path}")
        except Exception as e:
            print(f"[✗] Failed to register in {target}: {e}")


def main():
    print("==================================================")
    print("DigitalGuard Windows Native Messaging Registration")
    print("==================================================")
    create_manifest()
    register_windows_registry()
    print("\n[✓] Registration complete. Browser extensions can now communicate with desktop-agent.")


if __name__ == "__main__":
    main()
