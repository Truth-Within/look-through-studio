@echo off
rem Build the Windows desktop app (.exe) from the project root on Windows:
rem   packaging\build_windows.bat
rem -> dist\LookThroughStudio.exe   (double-click opens the dashboard in your browser)
cd /d "%~dp0.."
python -m pip install -r requirements.txt pyinstaller
python packaging\make_icons.py
pyinstaller packaging\studio-windows.spec --clean --noconfirm
echo.
echo Built: dist\LookThroughStudio.exe
echo Make sure ffmpeg is on PATH on the target machine (winget install ffmpeg).
pause
