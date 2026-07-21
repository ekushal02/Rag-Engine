#!/bin/bash
# deploy/deploy.sh
# Usage: EC2_PUBLIC_IP=1.2.3.4 ./deploy/deploy.sh
# Requires: AWS CLI configured, ECR repos created, .env on EC2,
#           EC2_PUBLIC_IP exported (used to bake the frontend's API URL)

set -euo pipefail

: "${EC2_PUBLIC_IP:?Set EC2_PUBLIC_IP before running this script, e.g. EC2_PUBLIC_IP=1.2.3.4 ./deploy/deploy.sh}"

AWS_REGION="us-east-1"                        # change to your region
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_BASE="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

BACKEND_REPO="rag-engine-backend"
FRONTEND_REPO="rag-engine-frontend"

echo "=== Logging into ECR ==="
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_BASE"

echo "=== Building backend ==="
docker build -t "$BACKEND_REPO" ./backend
docker tag "$BACKEND_REPO:latest" "$ECR_BASE/$BACKEND_REPO:latest"
docker push "$ECR_BASE/$BACKEND_REPO:latest"

echo "=== Building frontend ==="
docker build \
  --build-arg NEXT_PUBLIC_API_URL="http://$EC2_PUBLIC_IP:8000" \
  -t "$FRONTEND_REPO" ./frontend
docker tag "$FRONTEND_REPO:latest" "$ECR_BASE/$FRONTEND_REPO:latest"
docker push "$ECR_BASE/$FRONTEND_REPO:latest"

echo "=== Images pushed. SSH to EC2 and run: docker compose pull && docker compose up -d ==="
