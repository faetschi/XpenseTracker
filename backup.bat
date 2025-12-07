@echo off
setlocal

:: 1. Pre-check: Is the database container running?
docker exec xpense-db echo Connection Check >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Container 'xpense-db' is not running!
    echo Please start the application with 'docker compose up -d' before backing up.
    echo.
    pause
    exit /b 1
)

:: Get current date and time for the backup folder
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set "timestamp=%datetime:~6,2%-%datetime:~4,2%-%datetime:~0,4%_%datetime:~8,2%-%datetime:~10,2%"

set "BACKUP_DIR=backups\%timestamp%"
mkdir "%BACKUP_DIR%"

echo [1/2] Backing up Database...
:: Read DB user from .env or default to 'xpense'
for /f "tokens=2 delims==" %%a in ('findstr "POSTGRES_USER" .env') do set DB_USER=%%a
if "%DB_USER%"=="" set DB_USER=xpense

docker exec xpense-db pg_dump -U %DB_USER% -d xpense > "%BACKUP_DIR%\xpense_db_dump.sql"
if %ERRORLEVEL% NEQ 0 (
    echo     ERROR: Database backup failed!
    echo     Cleaning up...
    rmdir /s /q "%BACKUP_DIR%"
    echo.
    pause
    exit /b 1
) else (
    echo     Database backup successful.
)

echo [2/2] Backing up Configuration...
copy .env "%BACKUP_DIR%\.env" >nul
if %ERRORLEVEL% NEQ 0 (
    echo     ERROR: Failed to copy .env!
    rmdir /s /q "%BACKUP_DIR%"
    echo.
    pause
    exit /b 1
)

if exist "app\user_settings.json" (
    copy app\user_settings.json "%BACKUP_DIR%\user_settings.json" >nul
    if %ERRORLEVEL% NEQ 0 (
        echo     ERROR: Failed to copy user_settings.json!
        rmdir /s /q "%BACKUP_DIR%"
        echo.
        pause
        exit /b 1
    )
)

echo     Configuration backed up.

echo.
echo Backup completed successfully in: %BACKUP_DIR%
echo.
pause
