@echo off
setlocal enabledelayedexpansion

echo ========================================
echo   Hermes Bidirectional Sync
echo   Auto-sync before starting Hermes
echo ========================================
echo.

cd /d "%LOCALAPPDATA%\hermes"

echo [1/8] Checking if Hermes is running...
tasklist | findstr /I "Hermes.exe" >nul
if %errorlevel%==0 (
    echo.
    echo  ERROR: Hermes is still running!
    echo  Please close Hermes first, then run this script.
    echo.
    pause
    exit /b 1
)

echo  OK - Hermes not running

echo.
echo [2/8] Creating session export directory...
if not exist "sync_sessions" mkdir sync_sessions
if not exist "scripts" mkdir scripts

echo.
echo [3/8] Exporting sessions to JSON files...
python "%LOCALAPPDATA%\hermes\scripts\export_sessions.py"
if %errorlevel% neq 0 (
    echo  ERROR: Failed to export sessions!
    pause
    exit /b 1
)

echo.
echo [4/8] Fetching from GitHub...
git fetch origin main
if %errorlevel% neq 0 (
    echo  WARNING: Git fetch failed, continuing anyway...
)

echo.
echo [5/8] Committing local changes...
git add sync_sessions/
git add memories/
git add config.yaml
git add SOUL.md
git add skills/
git add scripts/
git add .gitignore
git add sync-bidirectional.bat
git add .gitattributes
git add verification_evidence.db

git commit -m "Sync from %computername% %date% %time%" 2>nul
if %errorlevel% neq 0 (
    echo  No changes to commit - skipping commit
)

echo.
echo [6/8] Pulling latest from GitHub...
git pull origin main --no-edit 2>nul
if %errorlevel% neq 0 (
    echo  NOTE: Pull had conflicts - JSON merge will resolve them
)

echo.
echo [7/8] Pushing to GitHub...
git push origin main
if %errorlevel% neq 0 (
    echo  WARNING: Push failed - you may need to resolve conflicts manually
    echo  Run this script again after resolving conflicts
    pause
    exit /b 1
)

echo.
echo [8/8] Rebuilding local database...
python "%LOCALAPPDATA%\hermes\scripts\import_sessions.py"
if %errorlevel% neq 0 (
    echo  WARNING: Database rebuild had issues, but sync is complete
)

echo.
echo ========================================
echo   SYNC COMPLETE!
echo   All sessions synced with GitHub.
echo   You can now start Hermes.
echo ========================================
echo.
pause