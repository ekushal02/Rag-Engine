#!/bin/bash
# deploy/ec2_setup.sh
# Run once on a fresh Amazon Linux 2023 or Ubuntu 22.04 EC2 instance.
# Recommended instance: t3.medium (2 vCPU, 4GB RAM) — needed for cross-encoder

set -euo pipefail

echo "=== Installing Docker ==="
sudo apt-get update -y
sudo apt-get install -y docker.io docker-compose-plugin curl git

sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker "$USER"

echo "=== Installing AWS CLI ==="
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
rm -rf aws awscliv2.zip

echo "=== Done. Log out and back in for docker group to take effect ==="
echo "Then run: aws configure"