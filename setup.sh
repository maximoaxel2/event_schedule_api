#!/bin/bash

APP_NAME="event_schedule_api"
REPO_DIR=$(pwd)
BIN_DIR="/usr/local/bin"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"

echo "Stopping existing service and cleaning up old files."
sudo systemctl stop "${APP_NAME}" 2>/dev/null || true
sudo rm -f "${BIN_DIR}/${APP_NAME}"
sudo rm -f "${SERVICE_FILE}"

echo "Building the project."
cargo build --release

echo "Installing the binary to ${BIN_DIR}"
sudo cp "${REPO_DIR}/target/release/${APP_NAME}" "${BIN_DIR}/${APP_NAME}"
sudo chmod +x "${BIN_DIR}/${APP_NAME}"

echo "Creating systemd daemon configuration."
sudo tee "${SERVICE_FILE}" > /dev/null <<EOF
[Unit]
Description=Event Schedule Axum API
After=network.target

[Service]
# Run as the current user, not root
User=$USER
Group=$USER

# The directory where your .env file is located
WorkingDirectory=${REPO_DIR}

# The executable path
ExecStart=${BIN_DIR}/${APP_NAME}

# Automatically load the variables from your .env file
EnvironmentFile=${REPO_DIR}/.env

# Restart policy for high availability
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

echo "Reloading systemd."
sudo systemctl daemon-reload
sudo systemctl enable "${APP_NAME}"
sudo systemctl restart "${APP_NAME}"

echo "Deployment complete."
sudo systemctl status "${APP_NAME}" --no-pager