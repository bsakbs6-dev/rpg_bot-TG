#!/bin/bash
# 1-click deploy script for Linux VPS (Ubuntu / Debian)
set -e

echo "=== Telegram RP Bot Deployment ==="

# Check if Docker is installed
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    echo "Using Docker Compose..."
    docker compose up -d --build
    echo "Bot successfully started in Docker! Logs: docker compose logs -f"
    exit 0
fi

# Fallback to standard Python systemd service
echo "Docker not detected, setting up Python virtual environment..."
sudo apt update && sudo apt install -y python3 python3-pip python3-venv

python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

echo "Starting bot with systemd..."
CURRENT_DIR=$(pwd)
SERVICE_FILE="/etc/systemd/system/telegram-rp-bot.service"

sudo bash -c "cat > $SERVICE_FILE" <<EOL
[Unit]
Description=Telegram RP Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=$CURRENT_DIR
ExecStart=$CURRENT_DIR/venv/bin/python main.py
Restart=always
RestartSec=5
EnvironmentFile=$CURRENT_DIR/.env

[Install]
WantedBy=multi-user.target
EOL

sudo systemctl daemon-reload
sudo systemctl enable telegram-rp-bot
sudo systemctl restart telegram-rp-bot

echo "=== Bot is now running 24/7! ==="
echo "Check status: sudo systemctl status telegram-rp-bot"
echo "View logs: sudo journalctl -u telegram-rp-bot -f"
