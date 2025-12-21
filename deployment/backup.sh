#!/bin/bash

# Ensure we are running from the project root
cd "$(dirname "$0")/.."

# Get current date and time for the backup folder
TIMESTAMP=$(date +"%d-%m-%Y_%H-%M")
BACKUP_ROOT="backups"
BACKUP_DIR="$BACKUP_ROOT/$TIMESTAMP"

# Ensure backup root exists
mkdir -p "$BACKUP_ROOT"
mkdir -p "$BACKUP_DIR"

# Check DB Type from .env
DB_TYPE=$(grep "DB_TYPE" .env | cut -d '=' -f2 | tr -d '[:space:]' | cut -d '#' -f1)
if [ -z "$DB_TYPE" ]; then
    DB_TYPE="postgres"
fi

if [ "$DB_TYPE" == "sqlite" ]; then
    echo "[1/2] Backing up SQLite Database safely..."
    if [ -f "app/data/xpensetracker.db" ]; then
        sqlite3 app/data/xpensetracker.db ".backup '$BACKUP_DIR/xpensetracker.db'"
        echo "    SQLite database backup successful."
    elif [ -f "data/xpensetracker.db" ]; then
        # On Pi, the volume might be mapped to ./data
        sqlite3 data/xpensetracker.db ".backup '$BACKUP_DIR/xpensetracker.db'"
        echo "    SQLite database backup successful (from ./data)."
    else
        echo "    WARNING: SQLite database file not found."
    fi
else
    echo "[1/2] Backing up PostgreSQL Database..."
    # Pre-check: Is the database container running?
    if ! docker exec xpense-db echo "Connection Check" > /dev/null 2>&1; then
        echo "ERROR: Container 'xpense-db' is not running!"
        rm -rf "$BACKUP_DIR"
        exit 1
    fi

    # Read DB user from .env or default to 'xpense'
    DB_USER=$(grep "POSTGRES_USER" .env | cut -d '=' -f2 | tr -d '[:space:]' | cut -d '#' -f1)
    if [ -z "$DB_USER" ]; then
        DB_USER="xpense"
    fi

    docker exec xpense-db pg_dump -U "$DB_USER" -d xpense > "$BACKUP_DIR/xpense_db_dump.sql"
    if [ $? -ne 0 ]; then
        echo "    ERROR: Database backup failed!"
        rm -rf "$BACKUP_DIR"
        exit 1
    else
        echo "    Database backup successful."
    fi
fi

echo "[2/2] Backing up Configuration and Data..."
echo "    Note: .env and uploads/ are intentionally excluded from backups."

# Backup settings
if [ -f "app/data/user_settings.json" ]; then
    cp "app/data/user_settings.json" "$BACKUP_DIR/user_settings.json"
elif [ -f "data/user_settings.json" ]; then
    cp "data/user_settings.json" "$BACKUP_DIR/user_settings.json"
fi

echo ""
echo "Backup completed successfully in: $BACKUP_DIR"
echo ""

# Cleanup old backups (Keep only last 5)
echo "Cleaning up old backups (keeping last 5)..."
ls -dt backups/* | tail -n +6 | xargs -d '\n' rm -rf 2>/dev/null
echo "Done."
