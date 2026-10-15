@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  python -m venv .venv
  if errorlevel 1 goto setup_failed
  .venv\Scripts\python -m pip install -r requirements.txt
  if errorlevel 1 goto setup_failed
)
if not exist .env copy .env.example .env
if exist "runtime\mt5\terminal64.exe" (
  echo Starting the optional portable MT5 terminal...
  if not exist "runtime\mt5\MQL5\Scripts" mkdir "runtime\mt5\MQL5\Scripts"
  copy /Y "ea\ReadOnlyDesk.mq5" "runtime\mt5\MQL5\Scripts\ReadOnlyDesk.mq5" >nul
  copy /Y "ea\desk.ini" "runtime\mt5\desk.ini" >nul
  set "MT5_PATH=%CD%\runtime\mt5\terminal64.exe"
  set "MT5_PORTABLE=true"
  set "COMPILE_NEEDED=0"
  if not exist "runtime\mt5\MQL5\Scripts\ReadOnlyDesk.ex5" set "COMPILE_NEEDED=1"
  if exist "runtime\mt5\MQL5\Scripts\ReadOnlyDesk.ex5" (
    powershell -NoProfile -Command "if ((Get-Item 'ea\ReadOnlyDesk.mq5').LastWriteTimeUtc -gt (Get-Item 'runtime\mt5\MQL5\Scripts\ReadOnlyDesk.ex5').LastWriteTimeUtc) { exit 1 }"
    if errorlevel 1 set "COMPILE_NEEDED=1"
  )
  if "!COMPILE_NEEDED!"=="1" if exist "runtime\mt5\MetaEditor64.exe" (
    echo Compiling the optional read-only exporter...
    start /wait "" "runtime\mt5\MetaEditor64.exe" /portable /compile:"%~dp0runtime\mt5\MQL5\Scripts\ReadOnlyDesk.mq5" /log:"%~dp0runtime\mt5\MQL5\Scripts\ReadOnlyDesk.log"
  )
  start "" "runtime\mt5\terminal64.exe" /portable /config:"%~dp0runtime\mt5\desk.ini"
  timeout /t 5 /nobreak >nul
) else (
  echo Open and log in to your broker's MetaTrader 5 terminal before using the desk.
  echo The portable terminal is optional; the client package does not include it.
)
set "APP_OPEN_BROWSER=true"
.venv\Scripts\python.exe -m app.main
exit /b %errorlevel%

:setup_failed
echo Python environment setup failed. Install 64-bit Python and try again.
pause
exit /b 1
