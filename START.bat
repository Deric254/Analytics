@echo off
title DericBI Analytics Engine
color 0A

echo.
echo ====================================================
echo   DericBI Analytics Engine
echo ====================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found.
    echo Install from https://www.python.org/downloads/
    echo Tick "Add Python to PATH" during install.
    pause & exit /b 1
)
echo Python OK: & python --version
echo.

cd /d "%~dp0"

echo Checking packages...
pip install dash dash-bootstrap-components plotly pandas numpy ^
    sqlalchemy pymysql openpyxl reportlab requests ^
    --quiet --exists-action i 2>nul
echo Packages ready.
echo.

echo ====================================================
echo   URL  : http://127.0.0.1:10000
echo   Stop : Close this window or Ctrl+C
echo ====================================================
echo.

REM Launch a helper that waits for server then opens browser
REM Uses curl if available, falls back to pure ping delay
start /b cmd /c "^
setlocal & ^
set /a tries=0 & ^
:poll & ^
set /a tries+=1 & ^
curl -sf http://127.0.0.1:10000/ping >nul 2>&1 & ^
if not errorlevel 1 (start http://127.0.0.1:10000 & exit) & ^
if %tries% geq 30 (start http://127.0.0.1:10000 & exit) & ^
ping -n 2 127.0.0.1 >nul & ^
goto poll"

REM Start the app — warnings suppressed
python -W ignore app.py

echo.
echo Server stopped.
pause
