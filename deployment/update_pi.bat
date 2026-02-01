@echo off
setlocal

rem Usage: update_pi.bat [host] [user]
rem Example: update_pi.bat dockerpi.local pi

set PI_HOST=raspi-one
set PI_USER=faetschi
set PROJECT_DIR=~/xpense-tracker

if not "%~1"=="" set PI_HOST=%~1
if not "%~2"=="" set PI_USER=%~2

echo Updating XpenseTracker on %PI_USER%@%PI_HOST% ...
ssh %PI_USER%@%PI_HOST% "cd %PROJECT_DIR% && docker compose pull xpensetracker && docker compose up -d --no-deps --force-recreate xpensetracker && docker image prune -f"

endlocal
