@echo off
rem Double-click to update Clipz Hub from GitHub. Your data is not changed.
cd /d "%~dp0"
set "PY="
py -3 --version >nul 2>nul
if not errorlevel 1 set "PY=py -3"
if not defined PY (
  python --version >nul 2>nul
  if not errorlevel 1 set "PY=python"
)
if not defined PY (
  echo Python 3 was not found on this computer. Install it from python.org first.
  pause
  exit /b 1
)
%PY% scripts\update.py
echo.
pause
