#!/bin/bash
# first-boot.sh - Network Agent Appliance First-Boot Setup
# Runs automatically on first boot - generates secrets and starts services
# Fully transparent - no user interaction required
set -euo pipefail

MARKER="/var/lib/network-agent/.initialized"
ENV_FILE="/opt/network-agent/.env"
COMPOSE_DIR="/opt/network-agent"
CREDS_FILE="/root/network-agent-credentials.txt"

# Check if already initialized
if [[ -f "$MARKER" ]]; then
    exit 0
fi

# Generate secure secrets
POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)
BASIC_AUTH_USER="admin"
BASIC_AUTH_PASSWORD=$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -c 16)
SEARXNG_SECRET=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)

# Generate Caddy password hash (bcrypt)
BASIC_AUTH_HASH=$(docker run --rm caddy:2.9-alpine caddy hash-password --plaintext "$BASIC_AUTH_PASSWORD" 2>/dev/null)

# Escape $ characters in bcrypt hash for Docker Compose .env files
BASIC_AUTH_HASH_ESCAPED=$(printf '%s' "$BASIC_AUTH_HASH" | sed 's/\$/\$\$/g')

# Get version (with fallback)
APPLIANCE_VERSION=$(cat /opt/network-agent/VERSION 2>/dev/null || echo "latest")

# Write .env file
cat > "$ENV_FILE" << EOF
# Network Agent Appliance - Generated Secrets
# Generated on: $(date -Iseconds)
# DO NOT SHARE OR COMMIT THIS FILE!

# PostgreSQL
POSTGRES_USER=agent
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}

# Caddy Basic Auth
BASIC_AUTH_USER=${BASIC_AUTH_USER}
BASIC_AUTH_HASH=${BASIC_AUTH_HASH_ESCAPED}

# SearXNG
SEARXNG_SECRET=${SEARXNG_SECRET}

# LLM Model (qwen3:4b = fast/small, qwen3:30b-a3b = quality/large)
#LLM_MODEL=qwen3:4b

# Version
VERSION=${APPLIANCE_VERSION}
EOF
chmod 600 "$ENV_FILE"

# Get network information
VM_IP=$(hostname -I | awk '{print $1}')

# Save credentials to file for user reference
cat > "$CREDS_FILE" << EOF
Network Agent Appliance - Access Credentials
=============================================
Generated: $(date)

Web Interface:
  URL:      https://${VM_IP}
  User:     ${BASIC_AUTH_USER}
  Password: ${BASIC_AUTH_PASSWORD}

SSH Access:
  User:     root
  Auth:     SSH key only (password disabled)

To change LLM model, edit /opt/network-agent/.env:
  LLM_MODEL=qwen3:4b        # Fast (default, 2.5GB)
  LLM_MODEL=qwen3:30b-a3b   # Quality (18GB)
Then restart: cd /opt/network-agent && docker compose restart net-agent

SECURITY: Delete this file after saving credentials!
  rm ${CREDS_FILE}
EOF
chmod 600 "$CREDS_FILE"

# Start Docker Compose
cd "$COMPOSE_DIR"
docker compose up -d

# Create marker file
mkdir -p "$(dirname "$MARKER")"
touch "$MARKER"
