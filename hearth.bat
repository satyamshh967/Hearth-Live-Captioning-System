@echo off
setlocal
cd /d "%~dp0"

echo =========================================================
echo Starting Hearth - Offline Live Captions & Speech Translation
echo =========================================================

REM Check for virtual environment
if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

"%PYTHON_EXE%" scripts\launch_hearth.py %*
pause
