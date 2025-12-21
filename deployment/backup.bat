@echo off
setlocal

:: Ensure we are running from the project root
pushd "%~dp0.."

:: Get current date and time for the backup folder
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set "timestamp=%datetime:~6,2%-%datetime:~4,2%-%datetime:~0,4%_%datetime:~8,2%-%datetime:~10,2%"

set "BACKUP_DIR=backups\%timestamp%"
mkdir "%BACKUP_DIR%"

:: Check DB Type from .env
for /f "tokens=2 delims==" %%a in ('findstr "DB_TYPE" .env') do set DB_TYPE=%%a
if "%DB_TYPE%"=="" set DB_TYPE=postgres

if "%DB_TYPE%"=="sqlite" (
    echo [1/2] Backing up SQLite Database...
    if exist "app\data\xpensetracker.db" (
        copy "app\data\xpensetracker.db" "%BACKUP_DIR%\xpensetracker.db" >nul
        echo     SQLite database backup successful.
    ) else (
        echo     WARNING: SQLite database file not found at app\data\xpensetracker.db
    )
) else (
    echo [1/2] Backing up PostgreSQL Database...
    :: Pre-check: Is the database container running?
    docker exec xpense-db echo Connection Check >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Container 'xpense-db' is not running!
        echo Please start the application with 'docker compose up -d' before backing up.
        echo.
        rmdir /s /q "%BACKUP_DIR%"
        pause
        exit /b 1
    )

    :: Read DB user from .env or default to 'xpense'
    for /f "tokens=2 delims==" %%a in ('findstr "POSTGRES_USER" .env') do set DB_USER=%%a
    if "%DB_USER%"=="" set DB_USER=xpense

    docker exec xpense-db pg_dump -U %DB_USER% -d xpense > "%BACKUP_DIR%\xpense_db_dump.sql"
    if %ERRORLEVEL% NEQ 0 (
        echo     ERROR: Database backup failed!
        rmdir /s /q "%BACKUP_DIR%"
        echo.
        pause
        exit /b 1
    ) else (
        echo     Database backup successful.
    )
)

echo [2/2] Backing up Configuration and Data...
echo     Note: .env and uploads/ are intentionally excluded from backups.

if exist "app\data\user_settings.json" (
    copy "app\data\user_settings.json" "%BACKUP_DIR%\user_settings.json" >nul
)

echo.
echo Backup completed successfully in: %BACKUP_DIR%
echo.
pause
exit /b 0

echo     Configuration backed up (excluding .env).

echo.
echo Backup completed successfully in: %BACKUP_DIR%
echo.
pause
