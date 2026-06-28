@echo off
echo ========================================
echo   Hermes Sync - Desktop 2 (Pull & Sync)
echo ========================================
echo.

cd /d "%LOCALAPPDATA%\hermes"

echo [1/5] Fetching from GitHub...
git fetch origin main

echo.
echo [2/5] Backing up local .env file...
copy "%LOCALAPPDATA%\hermes\.env" "%LOCALAPPDATA%\hermes\.env.backup" /Y

echo.
echo [3/5] Resetting to GitHub version (keeps .env)...
git reset --hard origin/main

echo.
echo [4/5] Restoring .env file...
copy "%LOCALAPPDATA%\hermes\.env.backup" "%LOCALAPPDATA%\hermes\.env" /Y
del "%LOCALAPPDATA%\hermes\.env.backup"

echo.
echo [5/5] You can now start Hermes!
echo.
echo ========================================
echo   Desktop 2 sync complete!
echo ========================================
echo.
pause