@echo off
title Desktop AI Agent - Universal Laptop Automation
cls
echo ======================================================================
echo    DESKTOP AI AGENT - UNIVERSAL LAPTOP AUTOMATION SYSTEM
echo ======================================================================
echo  [+] Initializing native Windows OS hooks...
echo  [+] Real window enumeration, UIA process detection & telephony enabled.
echo.

cd /d "%~dp0"

IF EXIST "venv\Scripts\python.exe" (
    SET "PYTHON_EXEC=venv\Scripts\python.exe"
) ELSE (
    SET "PYTHON_EXEC=python"
)

echo  [+] Launching Desktop AI Agent backend & UI...
echo  [+] URL: http://127.0.0.1:8000
echo.
echo  Press Ctrl+C in this window anytime to stop the assistant.
echo ======================================================================
echo.

"%PYTHON_EXEC%" run.py --port 8000

pause
