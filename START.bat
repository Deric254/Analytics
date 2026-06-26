@echo off
title DericBI Analytics Engine
color 0A

echo.
echo ====================================================
echo   DericBI Analytics Engine
echo ====================================================
echo.

REM ── Check Python ──────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found on this machine.
    echo.
    echo  1. Go to https://www.python.org/downloads/
    echo  2. Download Python 3.10 or newer
    echo  3. During install, tick "Add Python to PATH"
    echo  4. Run this file again
    echo.
    pause
    exit /b 1
)

echo Python OK:
python --version
echo.

REM ── Move to this script's folder ─────────────────────
cd /d "%~dp0"

REM ── Install packages (fast if already installed) ─────
echo Checking packages...
pip install dash dash-bootstrap-components plotly pandas numpy ^
    sqlalchemy pymysql openpyxl reportlab requests ^
    --quiet --exists-action i
echo Packages ready.
echo.

REM ── Open browser after 4 second delay ────────────────
echo Starting server... browser will open in a moment.
echo.
start /b cmd /c "timeout /t 4 >nul && start http://127.0.0.1:10000"

REM ── Launch app ────────────────────────────────────────
echo ====================================================
echo   URL  : http://127.0.0.1:10000
echo   Stop : Close this window or press Ctrl+C
echo ====================================================
echo.

python app.py

echo.
echo Server stopped.
pause
