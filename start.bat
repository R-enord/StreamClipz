@echo off
rem Double-click to start StreamClipz on Windows.
rem The first run installs the app's parts into your normal Python (no virtual environment).
cd /d "%~dp0"
echo StreamClipz start
echo.

set "PY="
py -3 --version >nul 2>nul
if not errorlevel 1 set "PY=py -3"
if not defined PY (
  python --version >nul 2>nul
  if not errorlevel 1 set "PY=python"
)
if not defined PY (
  echo Python 3 was not found on this computer.
  echo Install it from python.org and tick "Add python.exe to PATH" on the first screen.
  echo Then double-click start.bat again.
  pause
  exit /b 1
)

echo Installing or checking the app's parts. The first run takes about a minute...
%PY% -m pip install -q --user -r requirements.txt
if errorlevel 1 (
  echo.
  echo The app's parts could not be installed.
  echo Copy everything in this window and send it to Claude.
  pause
  exit /b 1
)

%PY% scripts\start.py
echo.
pause
