@echo off
title DigitalGuard Windows Host Registration
echo ========================================================
echo Installing DigitalGuard Native Messaging Host on Windows
echo ========================================================
echo.

python "%~dp0register_host.py"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Registration failed. Ensure Python is installed and accessible.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo Installation succeeded.
pause
