@echo off
setlocal
:: DigitalGuard Windows Native Messaging Host Launcher
set AGENT_DIR=%~dp0
if exist "%AGENT_DIR%..\.venv\Scripts\python.exe" (
    "%AGENT_DIR%..\.venv\Scripts\python.exe" -u "%AGENT_DIR%ipc\native_host.py" %*
) else (
    python -u "%AGENT_DIR%ipc\native_host.py" %*
)
