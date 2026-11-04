@echo off
title Aura AI Desktop Voice Assistant V2
cls
echo ======================================================================
echo    AURA AI VOICE COMMAND ASSISTANT - LOCAL DESKTOP RUNNER
echo ======================================================================
echo  [+] Initializing native Windows OS hooks...
echo  [+] Real window enumeration and process detection enabled.
echo.

cd /d "%~dp0"

IF EXIST "venv\Scripts\python.exe" (
    SET "PYTHON_EXEC=venv\Scripts\python.exe"
) ELSE (
    SET "PYTHON_EXEC=python"
)

echo  [+] Launching Aura backend server & local desktop UI...
echo  [+] URL: http://127.0.0.1:8000
echo.
echo  Press Ctrl+C in this window anytime to stop the assistant.
echo ======================================================================
echo.

"%PYTHON_EXEC%" run.py --port 8000

pause
