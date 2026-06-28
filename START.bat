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
echo Waiting for server to start...

REM Start Python app in this window
REM Open browser only AFTER server confirms ready (via ping loop)
start /b cmd /c "ping -n 8 127.0.0.1 >nul && start http://127.0.0.1:10000"

python app.py

echo.
echo Server stopped.
pause
