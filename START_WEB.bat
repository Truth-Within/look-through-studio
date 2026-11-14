@echo off
rem Start The Look Through Studio web UI on Windows -> http://127.0.0.1:8080
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python 3.10+ is required: https://www.python.org/downloads/
  pause
  exit /b 1
)
python -m pip install -r requirements.txt
where ffmpeg >nul 2>nul
if errorlevel 1 echo NOTE: ffmpeg not found on PATH. Install it for rendering: winget install ffmpeg
python webapp.py --host 127.0.0.1 --port 8080
pause
