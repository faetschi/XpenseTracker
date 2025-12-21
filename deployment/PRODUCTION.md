# Persistence Guide

## Data Persistence
Data is stored in the `/app/data/` directory, which is mapped to a host folder (usually `./data`) in `docker-compose.yaml`. This ensures all data persists even when containers are updated or recreated.

### What is stored in `/app/data/`:
1.  **Database**: `xpensetracker.db` (if using SQLite).
2.  **Settings**: `user_settings.json`.
3.  **Receipt Images**: `uploads/` folder.

## 💾 Backups
A `backup.bat` (Windows) and `backup.sh` (Linux/Pi) script are included in the `deployment/` directory. Run them to create a full snapshot of the current system.

### What it backs up:
*   **Database**: Either a PostgreSQL dump (`.sql`) or the SQLite file (`.db`).
*   **Configuration**: `user_settings.json`.

The `uploads/` folder is **excluded** from backups to save space.

### How to run:
**Windows:**
```cmd
.\deployment\backup.bat
```

**Linux / Raspberry Pi:**
```bash
chmod +x deployment/backup.sh
./deployment/backup.sh
```
Backups are saved in the `backups/DD-MM-YYYY_HH-MM` folder.

## ♻️ Restore
To restore data from a backup:

### If using SQLite:
1.  Stop the application.
2.  Copy `xpensetracker.db`, `user_settings.json`, and the `uploads/` folder from your backup into the `./data/` directory.
3.  Restart the application.

### If using PostgreSQL:
1.  **Database**:
    First, drop and recreate the database to ensure a clean state (**`WARNING`**: Deletes all current data):
    ```cmd
    docker exec -i xpense-db psql -U postgres -d postgres -c "DROP DATABASE IF EXISTS xpense WITH (FORCE); CREATE DATABASE xpense;"
    ```

    Then restore the dump:
    ```cmd
    docker exec -i xpense-db psql -U postgres -d xpense < backups/YOUR_BACKUP_FOLDER/xpense_db_dump.sql
    ```

2.  **Configuration**:
    Copy `user_settings.json` back to the `./data/` folder.

## 🔄 Migration
If you need to migrate data from PostgreSQL to SQLite (e.g. for a Raspberry Pi deployment), please refer to the [Raspberry Pi Guide](RASPBERRY-PI.md#%F0%9F%94%84-migrating-existing-data-postgres-to-sqlite).

## Important Considerations

### 1. Receipt Retention
By default, the app deletes uploaded images after **24 hours** to save space (`UPLOAD_RETENTION_MINUTES=1440`).
If you want to keep a digital archive of all your receipts:
1.  Go to **Settings**.
2.  Change "Upload Retention" to a very large number (e.g., `525600` for a year).
3.  Save.