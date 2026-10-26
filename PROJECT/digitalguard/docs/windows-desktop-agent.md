# Windows Desktop Agent Guide

The DigitalGuard Windows Desktop Agent runs continuously as a background service on the child's Windows computer to monitor process usage, enforce family safety rules, and maintain accurate screen-time quotas.

## Key Capabilities
1. **Active Application & Window Focus Tracking**:
   - Uses `ctypes.windll.user32.GetForegroundWindow()` and `GetWindowTextW()` to identify the exact window title and executable in focus.
   - Correlates PIDs with executable names using `psutil`.
2. **Accurate Idle Detection**:
   - Queries `user32.GetLastInputInfo()` to track keyboard and mouse activity.
   - If no user interaction occurs for 3 minutes (configurable), elapsed time is paused and discounted from active screen time.
3. **Application Enforcement**:
   - **BLOCK**: Disallowed applications (e.g. `cheatengine.exe`, `utorrent.exe`) are instantly minimized via `ShowWindow(hwnd, SW_MINIMIZE)` and can optionally be terminated with `proc.terminate()`. A native Windows warning dialogue is displayed.
   - **LIMITED**: Applications with daily allotments (e.g. `roblox.exe`, `discord.exe`) track cumulative minutes and halt access once the quota is reached.
4. **Bedtime & Screen-Time Quotas**:
   - Enforces daily screen time limits and bedtime schedules (e.g. 08:00 to 21:00).
5. **Chrome & Edge Native Messaging Host**:
   - Provides seamless IPC between browser extensions and local agents via standard input/output binary protocols (`struct.unpack('<I', ...)`).

## Installation & Setup on Windows
1. **Configure Environment**:
   ```bash
   set DIGITALGUARD_BACKEND_URL=http://127.0.0.1:8000
   set DIGITALGUARD_DEVICE_TOKEN=<YOUR_DEVICE_TOKEN_FROM_DASHBOARD>
   set DIGITALGUARD_AI_ENGINE_URL=http://127.0.0.1:8765
   ```
2. **Register Native Messaging Host**:
   Run the included batch script as administrator or standard user:
   ```cmd
   install_host_windows.bat
   ```
   This registers the host manifest at:
   - `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.digitalguard.agent`
   - `HKCU\Software\Microsoft\Edge\NativeMessagingHosts\com.digitalguard.agent`
   - `HKCU\Software\BraveSoftware\Brave-Browser\NativeMessagingHosts\com.digitalguard.agent`

3. **Start Agent**:
   ```cmd
   python desktop-agent/main.py
   ```
