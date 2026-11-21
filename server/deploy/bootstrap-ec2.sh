#!/usr/bin/env bash
# One-time setup of a fresh Ubuntu 24.04 EC2 server: installs Docker, Compose, nginx and
# certbot, and makes the folder the deploy workflow writes to. Run it on the server as the login user:
#   bash bootstrap-ec2.sh
set -euo pipefail
sudo apt-get update -y
sudo apt-get install -y docker.io docker-compose-v2 nginx certbot python3-certbot-nginx
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
mkdir -p ~/first-domino
echo "done: log out and back in so '$USER' can run docker without sudo"
