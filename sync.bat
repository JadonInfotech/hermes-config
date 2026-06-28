@echo off
echo ========================================
echo   Hermes Sync - Ongoing Sync Script
echo   Run this BEFORE starting Hermes
echo ========================================
echo.

cd /d "%LOCALAPPDATA%\hermes"

echo [1/6] Fetching latest changes...
git fetch origin main

echo.
echo [2/6] Checking for local changes...
git status --short

echo.
echo [3/6] Stashing secrets...
git stash push -m "Local secrets %date% %time%" -- .env auth.json .env.backup 2>nul

echo.
echo [4/6] Pulling latest from GitHub...
git pull origin main --no-edit

echo.
echo [5/6] Committing local changes (if any)...
git add -A
git commit -m "Sync from %computername% %date% %time%" 2>nul
if %errorlevel% neq 0 (
    echo    No changes to commit.
)

echo.
echo [6/6] Pushing to GitHub...
git push origin main

echo.
echo ========================================
echo   Sync Complete! Starting Hermes...
echo ========================================
echo.
pause