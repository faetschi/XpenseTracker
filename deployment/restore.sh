#!/bin/bash

# 1. Setup paths
BASE_DIR="$(dirname "$0")/.."
BACKUP_ROOT="$BASE_DIR/backups"
DATA_DIR="$BASE_DIR/data"
DB_NAME="xpensetracker.db"
SETTINGS_NAME="user_settings.json"

# 2. Find the latest backup folder
LATEST_BACKUP=$(ls -dt "$BACKUP_ROOT"/*/ | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "❌ Error: No backups found in $BACKUP_ROOT"
    exit 1
fi

echo "📂 Found latest backup: $LATEST_BACKUP"
echo "⚠️  WARNING: This will overwrite your current Database AND Settings."
read -p "Are you sure you want to proceed? (y/N): " confirm

if [[ $confirm != [yY] ]]; then
    echo "❌ Restore cancelled."
    exit 0
fi

# 3. Stop the application
echo "🛑 Stopping xpensetracker..."
docker compose -f "$BASE_DIR/docker-compose.yml" stop xpensetracker

# 4. Create safety backups of current files
echo "💾 Creating safety backups of current files..."
[ -f "$DATA_DIR/$DB_NAME" ] && cp "$DATA_DIR/$DB_NAME" "$DATA_DIR/$DB_NAME.pre-restore.bak"
[ -f "$DATA_DIR/$SETTINGS_NAME" ] && cp "$DATA_DIR/$SETTINGS_NAME" "$DATA_DIR/$SETTINGS_NAME.pre-restore.bak"

# 5. Restore Database
if [ -f "${LATEST_BACKUP}${DB_NAME}" ]; then
    echo "🔄 Restoring database..."
    cp "${LATEST_BACKUP}${DB_NAME}" "$DATA_DIR/$DB_NAME"
    chmod 664 "$DATA_DIR/$DB_NAME"
else
    echo "⚠️  Warning: $DB_NAME not found in backup folder."
fi

# 6. Restore Settings
if [ -f "${LATEST_BACKUP}${SETTINGS_NAME}" ]; then
    echo "⚙️  Restoring user settings..."
    cp "${LATEST_BACKUP}${SETTINGS_NAME}" "$DATA_DIR/$SETTINGS_NAME"
    chmod 664 "$DATA_DIR/$SETTINGS_NAME"
else
    echo "⚠️  Warning: $SETTINGS_NAME not found in backup folder."
fi

# 7. Start the application
echo "Starting xpensetracker..."
docker compose -f "$BASE_DIR/docker-compose.yml" up -d xpensetracker

echo "✅ Restore completed successfully!"