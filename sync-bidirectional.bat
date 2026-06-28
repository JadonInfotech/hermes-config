@echo off
setlocal enabledelayedexpansion

echo ========================================
echo   Hermes Bidirectional Sync
echo   Auto-sync before starting Hermes
echo ========================================
echo.

cd /d "%LOCALAPPDATA%\hermes"

echo [1/7] Checking environment...
echo  Hermes directory: %LOCALAPPDATA%\hermes

echo.
echo [2/7] Checking if Hermes is running...
tasklist | findstr /I "Hermes.exe" >nul
if %errorlevel%==0 (
    echo  WARNING: Hermes is running!
    echo  Sessions will sync to GitHub but import will be skipped.
    echo  Close Hermes and run again for full sync.
    echo.
)

echo [3/7] Exporting sessions to JSON...
python "%LOCALAPPDATA%\hermes\scripts\export_sessions.py"
echo.

echo [4/7] Git: Fetching from GitHub...
git fetch origin main
echo.

echo [5/7] Git: Committing local changes...
git add sync_sessions/
git add memories/
git add config.yaml
git add SOUL.md
git add skills/
git add scripts/
git add .gitignore
git add sync-bidirectional.bat
git add .gitattributes
git commit -m "Sync from %computername% %date% %time%" 2>nul
if %errorlevel% neq 0 (
    echo   No local changes to commit.
)
echo.

echo [6/7] Git: Pulling from GitHub...
git pull origin main --no-edit 2>nul
echo.

echo [7/7] Git: Pushing to GitHub...
git push origin main
echo.

echo [8/8] Importing merged sessions...
python "%LOCALAPPDATA%\hermes\scripts\import_sessions.py"
echo.

echo ========================================
echo   SYNC COMPLETE!
echo   Sessions synced with GitHub.
echo ========================================
echo.
pause