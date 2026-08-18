#!/usr/bin/env bash
# ==============================================================================
# VersusAI - Automated Let's Encrypt SSL Generator (Certbot)
# Usage: ./scripts/init-ssl.sh yourdomain.com admin@yourdomain.com
# ==============================================================================

set -e

DOMAIN=$1
EMAIL=$2

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    echo "❌ Usage: $0 <domain.com> <your-email@domain.com>"
    echo "Example: $0 versusai.example.com admin@example.com"
    exit 1
fi

echo "🔐 Installing Certbot and generating SSL for $DOMAIN ($EMAIL)..."

sudo apt-get update -y
sudo apt-get install -y certbot python3-certbot-nginx

# Request certificate
sudo certbot certonly --webroot -w /var/lib/letsencrypt \
    -d "$DOMAIN" \
    -d "www.$DOMAIN" \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    --force-renewal || sudo certbot --standalone -d "$DOMAIN" --email "$EMAIL" --agree-tos --no-eff-email

echo "✅ SSL Certificate successfully installed for $DOMAIN!"
echo "🔄 Reloading Nginx container..."
sudo docker compose restart nginx
