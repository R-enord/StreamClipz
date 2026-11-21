@echo off
rem Double-click to start Clipz Hub on Windows.
rem Your data is kept in ClipzHub-data in your user folder, so updates never touch it.
cd /d "%~dp0"
echo Clipz Hub start
echo.

if not defined STREAMCLIPZ_DATA_DIR set "STREAMCLIPZ_DATA_DIR=%USERPROFILE%\ClipzHub-data"
if not exist "%STREAMCLIPZ_DATA_DIR%\" call :copy_old_data

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

echo Checking the app's parts. The first run takes about a minute...
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
exit /b 0

:copy_old_data
rem First run with a new data folder: copy the login data from the older copy. The original stays.
if exist "%USERPROFILE%\StreamClipz\data\" (
  echo Copying your existing data to %STREAMCLIPZ_DATA_DIR%
  xcopy "%USERPROFILE%\StreamClipz\data" "%STREAMCLIPZ_DATA_DIR%\" /E /I /Q >nul
  goto :eof
)
if exist "%~dp0data\" (
  echo Copying your existing data to %STREAMCLIPZ_DATA_DIR%
  xcopy "%~dp0data" "%STREAMCLIPZ_DATA_DIR%\" /E /I /Q >nul
)
goto :eof
