# Raspberry Pi Zero 2 W Deployment Guide

This guide documents the workflow for deploying **XpenseTracker** to a Raspberry Pi Zero 2 W using Docker Buildx (Cross-compilation) and Watchtower (Auto-updates).


## **TL;DR** - Daily Deployment Workflow

Whenever you update your code, simply `build and push` from PC with Docker via [`deploy.bat`](deploy.bat) (Windows). The Raspberry Pi will automatically fetch the latest image via Watchtower.

```bash
.\deployment\deploy.bat
```

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

### 🚀 Performance Optimization (Highly Recommended)
The Pi Zero 2 W has only 512MB RAM.  First, create a "health" alias, to monitor the Pi:

    ```bash
    # Open the File
    nano ~/.bashrc

    # Paste this alias at the end -> Save & Exit
    alias health='echo "========================================"
    echo "🔥 CPU Temp: $(vcgencmd measure_temp)"
    echo "⚡ Throttled: $(vcgencmd get_throttled)"
    echo "----------------------------------------"
    echo "💾 Memory & Swap:"
    free -h | grep -E "Mem|Swap"
    echo ""
    echo "📦 ZRAM Details:"
    zramctl
    echo "----------------------------------------"
    echo "💿 Disk Usage:"
    df -h | grep "/$"
    echo "========================================"'

    # Then update
    source ~/.bashrc
    ```

To prevent slowness and crashes, further perform these steps:

1.  **Enable Memory Limits:**
    Enable cgroup memory support so Docker can enforce the `350M` limit:
    *   Run `sudo nano /boot/cmdline.txt` (or `/boot/firmware/cmdline.txt`).
    *   Add `cgroup_enable=cpuset cgroup_enable=memory cgroup_memory=1` to the end of the line.
    *   Save and run `sudo reboot`.

2.  **Increase Swap Space:**
    Standard 100MB swap is not enough. Increase it to 512MB:
    ```bash
    # 1.
    sudo apt install dphys-swapfile -y
    sudo nano /etc/dphys-swapfile
        # Change CONF_SWAPSIZE=100 to CONF_SWAPSIZE=512
    sudo /etc/init.d/dphys-swapfile restart

    # 2.
    sudo nano /etc/default/zramswap
        ## Change these settings
        # Compression algorithm
        ALGO=zstd

        # Use 100% of RAM size for the ZRAM disk (don't worry, it's virtual)
        PERCENT=100

        # Priority (ensure it's higher than the swap file)
        PRIORITY=100

    sudo systemctl restart zramswap
    ```

    Then verify, if it worked:
    ```bash
    free -h
    zramctl
    ```

3.  **Enable ZRAM (Optional but Recommended):**
    ZRAM creates a compressed swap partition in RAM, which is much faster than the SD card:
    ```bash
    sudo apt install zram-tools -y
    ```

    Note: this might lead to conflicts: delete unused dependencies, if they occur:
    sudo apt remove systemd-zram-generator -y
    sudo apt autoremove -y

### 🛠️ Deployment Steps
Now on the Pi, download the image from GitHub Packages (GHCR) instead of building it locally.

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
    *Fill in API Keys & Configuration. **Important:** Set `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and a random `AUTH_SECRET` to protect your app. Save with `Ctrl+O`, Exit with `Ctrl+X`.*

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

            # 2. Access the app from network
            ports:
                - "8501:8501"
            
            # 3. Load Secrets from the .env file on the Pi
            env_file:
                - .env
            
            # 4. Environment Overrides (Specific to Pi)
            environment:
                - DB_TYPE=sqlite
            
            # 5. Persistence: Maps the Pi's folder to the container
            volumes:
                - ./data:/app/app/data
            
            # 6. Safety Limits for Pi Zero 2 W
            deploy:
                resources:
                    limits:
                        memory: 350M  # Leaves ~100MB for OS + Watchtower

            # 7. Log Rotation (Prevents SD card filling up)
            logging:
                driver: "json-file"
                options:
                    max-size: "10m" # ensures logs never take up more than 30MB
                    max-file: "3"
            
            # 8. Tag for Watchtower to update this specific container
            labels:
                - "com.centurylinklabs.watchtower.enable=true"

        watchtower:
            image: nickfedor/watchtower:arm64v8-dev
            container_name: watchtower
            restart: always
            environment:
                - WATCHTOWER_CLEANUP=true
                - WATCHTOWER_LABEL_ENABLE=true
                - WATCHTOWER_POLL_INTERVAL=300
                - TZ=Europe/Berlin
                # Notifications Setup
                - WATCHTOWER_NOTIFICATIONS=shoutrrr
                - WATCHTOWER_NOTIFICATION_URL=discord://{WEBHOOK_TOKEN}@{WEBHOOK_ID} # Change this to your Discord Webhook
                - WATCHTOWER_NOTIFICATION_REPORT=true
                - WATCHTOWER_NO_STARTUP_MESSAGE=true
                - WATCHTOWER_NOTIFICATION_TEMPLATE={{range .}}{{.Message}}{{println}}{{end}}
                - WATCHTOWER_NOTIFICATIONS_LEVEL=info
                # Use environment variables for GHCR authentication
                # - REPO_USER=GITHUB_USERNAME # Change this
                # - REPO_PASS=GITHUB_PAT # Change this
            volumes:
                - /var/run/docker.sock:/var/run/docker.sock
                - /home/faetschi/.docker/config.json:/config.json
            # Checks every 30 mins (1800s), removes old images (cleanup), only updates labeled apps
            command: --interval 1800 --cleanup --label-enable
    ```

6.  **Start the Services (inside ./xpense-tracker ):**
    ```bash
    docker compose up -d
    ```

    *Note: The containers are configured with `restart: always`, so they will automatically start whenever the Pi reboots. To ensure Docker itself starts on boot **automatically**, run:*
    ```bash
    sudo systemctl enable docker
    ```

7.  **Setup Weekly Backups (Optional):**
    To **automatically** backup your data every Sunday at 03:00 AM:
    ```bash
    # Create the folder and download the script
    mkdir -p deployment
    wget https://raw.githubusercontent.com/faetschi/XpenseTracker/master/deployment/backup.sh -O deployment/backup.sh
    # Make the script executable
    chmod +x deployment/backup.sh
    
    # Open crontab editor
    crontab -e
    ```
    Add this line at the bottom:
    ```text
    0 3 * * 0 cd ~/xpense-tracker && ./deployment/backup.sh >> backup.log 2>&1
    ```

8. **Restore Latest Backup (Optional):**
    If you ever need to revert to your latest backup:
    ```bash
    # Download the restore script
    wget https://raw.githubusercontent.com/faetschi/XpenseTracker/master/deployment/restore.sh -O deployment/restore.sh
    
    # Make it executable
    chmod +x deployment/restore.sh
    
    # Run it
    ./deployment/restore.sh
    ```

## Step 3: Daily Deployment Workflow

See the [`TL;DR - Daily Deployment Workflow`](#tldr---daily-deployment-workflow) at the top of this guide for the quick command.


## 🔄 Migrating Existing Data (Postgres/SQLite to Pi)
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
    # Navigate to project root & copy database and settings (change username@hostname)
    scp app/data/xpensetracker.db app/data/user_settings.json faetschi@raspi-one.local:~/xpense-tracker/data/
    ```

4.  **Restart the container** on the Pi:
    ```bash
    docker compose restart xpensetracker
    ```

## Troubleshooting

* **Missing Secrets?** 
    If the app fails to start, check if you created the .env file on the Pi (cat .env).
* **Missing Data?** 
    Make sure to migrate existing PostgreSQL / SQLite data by copying it onto the Pi before starting the application.
* **Update not happening?**
    Watchtower checks every 5 minutes (`--interval 300`). Wait at least 5 minutes after pushing.
* **Pi Crashing?**
    Check RAM usage. Ensure `limits: memory: 350M` is set in the compose file and that ZRAM is enabled on the Pi OS.
* **Storage Full?**
    Check if `logging` is configured in `docker-compose.yml` to prevent log files from growing infinitely.

### Documentation

https://containrrr.dev/watchtower/private-registries/#share_the_docker_configuration_file

https://watchtower.nickfedor.com/v1.13.0/configuration/arguments/#registry_authentication