#!/usr/bin/env bash
# One-time setup of a fresh Ubuntu 24.04 EC2 server: installs Docker, nginx and
# certbot, and makes the folder the deploy workflow writes to. Run it on the server as the login user:
#   bash bootstrap-ec2.sh
set -euo pipefail
sudo apt-get update -y
sudo apt-get install -y docker.io nginx certbot python3-certbot-nginx curl
sudo systemctl enable --now docker
mkdir -p ~/first-domino
echo "done: now set up nginx and certbot (docs/DEPLOY.md)"
