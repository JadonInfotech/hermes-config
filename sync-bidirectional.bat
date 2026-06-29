@echo off
setlocal enabledelayedexpansion

echo ========================================
echo   Hermes Bidirectional Sync
echo   Auto-sync before starting Hermes
echo ========================================
echo.

cd /d "%LOCALAPPDATA%\hermes"

REM Configure git for safe rebasing (prevents merge commits that block push)
git config pull.rebase true 2>nul
git config rebase.autostash true 2>nul

REM Ensure LF line endings for all text files in repo
git config core.autocrlf input

echo [1/7] Checking environment...
echo  Hermes directory: %LOCALAPPDATA%\hermes
echo  Computer: %COMPUTERNAME%
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
if %errorlevel% neq 0 (
    echo  Export failed! Check errors above.
    echo.
)
echo.

echo [4/7] Git: Fetching from GitHub...
git fetch origin main
if %errorlevel% neq 0 (
    echo  Fetch failed!
    echo.
)
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
git commit -m "Sync from %COMPUTERNAME% %date% %time%" 2>nul
if %errorlevel% neq 0 (
    echo   No local changes to commit.
)
echo.

echo [6/7] Git: Rebasing onto remote changes...
REM Use rebase strategy: pulls remote changes, rebases local on top
REM This keeps linear history and avoids merge commits
git pull origin main --rebase --autostash 2>nul
if %errorlevel% neq 0 (
    echo   Rebase had conflicts - resolving...
    echo   Check git status and resolve conflicts manually if needed.
    git status
)
echo.

echo [7/7] Git: Pushing to GitHub...
git push origin main
if %errorlevel% neq 0 (
    echo   Push failed! This usually means:
    echo   1. Remote has changes that need to be rebased in
    echo   2. Run this script again to pull and push
    echo.
    echo   Trying pull+push once more...
    git pull origin main --rebase --autostash 2>nul
    git push origin main
    if %errorlevel% neq 0 (
        echo   Push still failing. Check git status.
    )
)
echo.

echo [8/8] Importing merged sessions...
python "%LOCALAPPDATA%\hermes\scripts\import_sessions.py"
echo.

echo ========================================
echo   SYNC COMPLETE
echo   Sessions synced with GitHub.
echo ========================================
echo.
pause