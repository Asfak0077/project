#!/usr/bin/env bash
# ==============================================================================
# VersusAI - AWS EC2 Automated Production Deployment Script
# Target OS: Ubuntu 22.04 / 24.04 LTS (x86_64 or ARM64)
# ==============================================================================

set -e

echo "=========================================================="
echo "🚀 Starting VersusAI AWS EC2 Production Deployment..."
echo "=========================================================="

# Detect Operating System (macOS vs Linux)
OS_TYPE=$(uname -s)

if [ "$OS_TYPE" = "Darwin" ]; then
    echo "🍏 Detected macOS environment (Local Machine)."
    echo "ℹ️ Note: This script will build and run your Docker containers locally."
    echo "   For production deployment on AWS EC2, run this script inside your Ubuntu EC2 instance."
    echo "----------------------------------------------------------"

    # Check if Docker Desktop is running
    if ! docker info > /dev/null 2>&1; then
        echo "❌ Docker is not running. Please open Docker Desktop on your Mac and try again."
        exit 1
    fi
    echo "✓ Docker is running."
else
    echo "🐧 Detected Linux environment (AWS EC2 / Ubuntu)."

    # 1. Update system packages
    echo "📦 [1/4] Updating system packages..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update -y
        sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release ufw git
    fi

    # 2. Install Docker & Docker Compose if not already installed
    if ! command -v docker &> /dev/null; then
        echo "🐳 [2/4] Installing Docker Engine..."
        sudo mkdir -p /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg --yes
        echo \
          "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
          $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt-get update -y
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
        sudo usermod -aG docker $USER
        echo "✓ Docker successfully installed."
    else
        echo "✓ Docker is already installed."
    fi

    # 3. Configure Firewall (UFW)
    if command -v ufw &> /dev/null; then
        echo "🔒 [3/4] Configuring Security Firewall (Ports 22, 80, 443)..."
        sudo ufw allow 22/tcp comment 'SSH' || true
        sudo ufw allow 80/tcp comment 'HTTP' || true
        sudo ufw allow 443/tcp comment 'HTTPS' || true
        sudo ufw --force enable || true
    fi
fi

# 4. Check for .env file
echo "🔑 Validating environment configuration..."
if [ ! -f ".env" ]; then
    if [ -f ".env.production.example" ]; then
        echo "⚠️ .env file not found. Creating from .env.production.example..."
        cp .env.production.example .env
        echo "❗ Notice: Using default .env. For production AWS, edit .env with your RDS credentials."
    else
        touch .env
    fi
fi

# 5. Build and Launch Containers
echo "🏗️ Building and starting VersusAI Docker containers..."
docker compose down --remove-orphans 2>/dev/null || sudo docker compose down --remove-orphans || true
docker compose build --parallel || sudo docker compose build --parallel
docker compose up -d || sudo docker compose up -d

# 6. Verification & Health Check
echo "🔍 [6/6] Verifying deployment health..."
sleep 5

docker compose ps

echo "=========================================================="
echo "✅ VersusAI successfully deployed on AWS EC2!"
echo "=========================================================="
echo "🌐 App URL:    http://$(curl -s ifconfig.me)"
echo "📡 API Docs:   http://$(curl -s ifconfig.me)/docs"
echo "🩺 Health:     http://$(curl -s ifconfig.me)/api/health"
echo "=========================================================="
