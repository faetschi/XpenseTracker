#!/bin/bash

# 1. Setup paths
BASE_DIR="$(dirname "$0")/.."
BACKUP_ROOT="$BASE_DIR/backups"
DATA_DIR="$BASE_DIR/data"
DB_NAME="xpensetracker.db"

# 2. Find the latest backup folder
LATEST_BACKUP=$(ls -dt "$BACKUP_ROOT"/*/ | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "❌ Error: No backups found in $BACKUP_ROOT"
    exit 1
fi

echo "📂 Found latest backup: $LATEST_BACKUP"
echo "⚠️  WARNING: This will overwrite your current database with the backup."
read -p "Are you sure you want to proceed? (y/N): " confirm

if [[ $confirm != [yY] ]]; then
    echo "❌ Restore cancelled."
    exit 0
fi

# 3. Stop the application
echo "🛑 Stopping xpensetracker..."
docker compose -f "$BASE_DIR/docker-compose.yml" stop xpensetracker

# 4. Create a safety backup of the CURRENT db before overwriting
if [ -f "$DATA_DIR/$DB_NAME" ]; then
    echo "💾 Creating safety backup of current database..."
    cp "$DATA_DIR/$DB_NAME" "$DATA_DIR/$DB_NAME.pre-restore.bak"
fi

# 5. Perform the restore
echo "🔄 Restoring database file..."
cp "${LATEST_BACKUP}${DB_NAME}" "$DATA_DIR/$DB_NAME"

# 6. Fix Permissions (Ensures Docker can read it)
chmod 664 "$DATA_DIR/$DB_NAME"

# 7. Start the application
echo "🚀 Starting xpensetracker..."
docker compose -f "$BASE_DIR/docker-compose.yml" up -d xpensetracker

echo "✅ Restore completed successfully!"