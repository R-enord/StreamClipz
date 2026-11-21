@echo off
rem Double-click to start StreamClipz on Windows. First run sets up the Python environment.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First run: setting up the app. This takes about a minute.
  py -3 -m venv .venv || python -m venv .venv
  .venv\Scripts\python.exe -m pip install -q -r requirements.txt
)
.venv\Scripts\python.exe scripts\start.py
echo.
pause
