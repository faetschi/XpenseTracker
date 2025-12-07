# Production & Backup Guide

## Data Persistence
Data is stored in two places:
1.  **Database**: 
<br>
Stored in a Docker Volume named `postgres_data`. This persists even when containers restart.
2.  **Files**:
    *   **Settings**: `app/user_settings.json` (Persists on host).
    *   **Environment**: `.env` (Persists on host).
    *   **Receipt Images**: `uploads/` (Temporarily persists on host, but see "Retention" below).

## 💾 Backups
A `backup.bat` script is included in the root directory. Run it to create a full snapshot of the current system.

### What it backs up:
*   **Database Dump**: `xpense_db_dump.sql`
*   **Configuration**: `.env` and `user_settings.json`

### How to run:
Double-click `backup.bat` or run it from the terminal:
```cmd
.\backup.bat
```
Backups are saved in the `backups/DD-MM-YYYY_HH-MM` folder.

## ♻️ Restore
To restore data from a backup:

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
    Copy `.env` and `user_settings.json` back to the root/app folder.

## Important Considerations

### 1. Receipt Retention
By default, the app deletes uploaded images after **2 minutes** to save space (`UPLOAD_RETENTION_MINUTES=2`).
If you want to keep a digital archive of all your receipts in the `uploads/` folder:
1.  Go to **Settings**.
2.  Change "Upload Retention" to a very large number (e.g., `525600` for a year).
3.  Save.

### 2. Security
*   **API Keys**: Your `.env` file contains sensitive API keys. **Never share your backup folder** or commit it to public version control.
*   **Access**: The app runs on port `8501`. Ensure your firewall blocks external access if you only use it locally.
