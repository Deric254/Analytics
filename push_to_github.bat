@echo off
title Push DericBI to GitHub
color 0A

echo.
echo ====================================================
echo   Push DericBI updates to GitHub
echo ====================================================
echo.

REM Move to the folder where this script lives
cd /d "%~dp0"

REM Check git is installed
git --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Git not found.
    echo Install from https://git-scm.com/download/win
    pause & exit /b 1
)

REM Check if this is already a git repo
if not exist ".git" (
    echo Initialising git repository...
    git init
    git remote add origin https://github.com/Deric254/Analytics.git
)

REM Make sure remote is correct
git remote set-url origin https://github.com/Deric254/Analytics.git

echo.
echo Staging all files...
git add -A

echo.
echo Committing...
git commit -m "Update DericBI: Dockerfile, gunicorn, sample data, dynamic BI engine"

echo.
echo Pushing to GitHub main branch...
git push origin main

if errorlevel 1 (
    echo.
    echo If push failed, try:
    echo   git push origin master
    echo   OR
    echo   git push -u origin main --force
    echo.
)

echo.
echo Done. Render will auto-deploy in ~2 minutes.
echo Check: https://dashboard.render.com
echo.
pause
