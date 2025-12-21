# Raspberry Pi Zero 2 W Deployment Guide

This guide documents the workflow for deploying **XpenseTracker** to a Raspberry Pi Zero 2 W using Docker Buildx (Cross-compilation) and Watchtower (Auto-updates).


## Step 1: First Setup on your PC (Do this once)

Your PC is likely Intel/AMD (x86 architecture), while the Pi Zero 2 W is ARM64. If you just run `docker build` on your PC, the image will not run on the Pi. You must use **Docker Buildx** to cross-compile.

1.  **Generate GitHub Personal Access Token (PAT):**
    You cannot use your GitHub password. You need a token.
    * Go to **GitHub Settings** -> **Developer settings** -> **Personal access tokens** -> **Tokens (classic)**.
    * Click **Generate new token (classic)**.
    * **Scopes:** Check `write:packages`, `read:packages`, and `delete:packages`.
    * **Copy** the token (starts with `ghp_...`).

2.  **Login to GHCR:**
    ```bash
    docker login ghcr.io -u GITHUB_USERNAME
    ```
    *Paste your PAT when asked for the password.*

3.  **Enable Buildx on:**
    Most modern Docker Desktop installs have this by default. Create a new builder instance just in case:
    ```bash
    docker buildx create --use
    ```

4.  **Security Check (.dockerignore):**
    Ensure `.dockerignore` exists in project root on your PC. It must contain `.env` to prevent uploading your secrets to GitHub Packages.
    ```text
    # .dockerignore
    .env
    __pycache__
    venv/
    .git
    ```

5.  **Initial Build & Push:**

    - Adjust your ghcr.io Username/Imagename in `deploy.bat` 
    - Run the deployment script to build the ARM64 image & push it to GitHub Packages:
        ```cmd
        .\deployment\deploy.bat
        ```
        *This ensures the image exists on GitHub before you try to pull it on the Pi.*

## Step 2: Configure the Pi (Receiver)

You need to tell the Pi to download the image from GitHub Packages (GHCR) instead of building it locally.

1.  **SSH into your Pi:**
    ```bash
    ssh pi@dockerpi.local
    ```

2.  **Create the project folder:**
    ```bash
    mkdir -p ~/xpense-tracker/data
    cd ~/xpense-tracker
    ```

3.  **Login to GHCR on the Pi:**

    Since the image is on GitHub Packages, the Pi needs permission to pull it:
    ```bash
    docker login ghcr.io -u GITHUB_USERNAME
    # Enter GitHub PAT as Password
    ```

4.  **Create your Secrets file (`.env`):**

    Since you aren't cloning the repo on the Pi, download the template from GitHub:
    ```bash
    wget https://raw.githubusercontent.com/faetschi/XpenseTracker/master/.env.example -O .env
    nano .env
    ```
    *Fill in API Keys & Configuration. Save with `Ctrl+O`, Exit with `Ctrl+X`.*

5.  **Create/Update `docker-compose.yml`:**
    ```bash
    nano docker-compose.yml
    ```
    *Paste the following content. Save with `Ctrl+O`, Exit with `Ctrl+X`:*

    ```yaml
    services:
        xpensetracker:
            # 1. Pulls the image from GHCR (no local building)
            image: ghcr.io/faetschi/xpensetracker:latest
            container_name: xpensetracker
            restart: always
            
            # 2. Load Secrets from the .env file on the Pi
            env_file:
                - .env
            
            # 3. Environment Overrides (Specific to Pi)
            environment:
                - DB_TYPE=sqlite
            
            # 4. Persistence: Maps the Pi's folder to the container
            volumes:
                - ./data:/app/data
            
            # 5. Safety Limits for Pi Zero 2 W
            deploy:
                resources:
                    limits:
                        memory: 350M  # Leaves ~100MB for OS + Watchtower

            # 6. Log Rotation (Prevents SD card filling up)
            logging:
                driver: "json-file"
                options:
                    max-size: "10m" # ensures logs never take up more than 30MB
                    max-file: "3"
            
            # 7. Tag for Watchtower to update this specific container
            labels:
                - "com.centurylinklabs.watchtower.enable=true"

        watchtower:
            image: containrrr/watchtower
            container_name: watchtower
            restart: always
            volumes:
                - /var/run/docker.sock:/var/run/docker.sock
            # Checks every 5 mins (300s), removes old images (cleanup), only updates labeled apps
            command: --interval 300 --cleanup --label-enable
    ```

6.  **Start the Services:**
    ```bash
    docker compose up -d
    ```

7.  **Setup Monthly Backups (Optional):**
    To automatically backup your data on the 1st of every month:
    ```bash
    # Make the script executable
    chmod +x deployment/backup.sh
    
    # Open crontab editor
    crontab -e
    ```
    Add this line at the bottom (runs at 03:00 AM on the 1st of every month):
    ```text
    0 3 1 * * cd ~/xpense-tracker && ./deployment/backup.sh >> backup.log 2>&1
    ```

## Step 3: Daily Deployment Workflow

Whenever you update your code, simply `build and push` from PC via one of the following two options. The Raspberry Pi will automatically fetch the latest image via Watchtower.

### *Option A: The "One-Click" Script (Recommended)*
Use the file named `deployment/deploy.bat` (Windows) so you don't have to type the build command every time.

### *Option B: Manual Command*
Run this in the project terminal on your PC:

```bash
# syntax: docker buildx build --platform [TARGET_ARCH] -t ghcr.io/[GITHUB_USER]/[IMAGE_NAME]:latest --push .

docker buildx build --platform linux/arm64 -t ghcr.io/faetschi/xpensetracker:latest --push .
```

* `--platform linux/arm64`: Tells Docker to build specifically for the Raspberry Pi's chip.
* `--push`: Automatically uploads the result to GitHub Packages.

## 🔄 Migrating Existing Data (Postgres to SQLite)
If you have been using the app with PostgreSQL on your PC and want to move your data to the Pi (SQLite):

1.  **On your PC**, run the backup script to get a SQL dump:
    ```cmd
    .\deployment\backup.bat
    ```
2.  **Run the migration script** on your PC:
    ```cmd
    python .\deployment\migrate_to_sqlite.py
    ```
    Point it to the `.sql` file in your `backups/` folder. This will create `app/data/xpensetracker.db`.
3.  **Copy the data to the Pi**:
    Run this command from your PC terminal (replace `pi@dockerpi.local` with your Pi's address):
    ```bash
    # Copy the database and settings
    scp app/data/xpensetracker.db app/data/user_settings.json pi@dockerpi.local:~/xpense-tracker/data/
    ```
4.  **Restart the container** on the Pi:
    ```bash
    docker compose up -d
    ```

## Troubleshooting

* **Missing Secrets?** 
    If the bot fails to start, check if you created the .env file on the Pi (cat .env).
* **Update not happening?**
    Watchtower checks every 5 minutes (`--interval 300`). Wait at least 5 minutes after pushing.
* **Pi Crashing?**
    Check RAM usage. Ensure `limits: memory: 350M` is set in the compose file and that ZRAM is enabled on the Pi OS.
* **Storage Full?**
    Check if `logging` is configured in `docker-compose.yml` to prevent log files from growing infinitely.