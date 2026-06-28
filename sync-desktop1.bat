@echo off
echo ========================================
echo   Hermes Sync - Desktop 1 (First Setup)
echo ========================================
echo.

cd /d "%LOCALAPPDATA%\hermes"

echo [1/4] Checking git status...
git remote -v

echo.
echo [2/4] Adding files to git...
git add -A

echo.
echo [3/4] Committing all changes...
git commit -m "Initial sync from Desktop 1 - %date%"

echo.
echo [4/4] Pushing to GitHub...
git push -u origin main --force

echo.
echo ========================================
echo   Desktop 1 is now synced!
echo ========================================
echo.
pause