#!/bin/bash
# first-boot.sh - Network Agent Appliance First-Boot Setup
# Generates secure secrets and forces password change
set -euo pipefail

MARKER="/var/lib/network-agent/.initialized"
ENV_FILE="/opt/network-agent/.env"
COMPOSE_DIR="/opt/network-agent"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }
info() { echo -e "${BLUE}[i]${NC} $1"; }

# Check if already initialized
if [[ -f "$MARKER" ]]; then
    log "Already initialized, skipping first-boot setup"
    exit 0
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║          NETWORK AGENT - FIRST BOOT SETUP                     ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# 1. Force root password change
warn "SECURITY: You must set a new root password!"
echo ""
while true; do
    if passwd root; then
        log "Root password changed successfully"
        break
    else
        warn "Password change failed, please try again"
    fi
done
echo ""

# 2. Generate secure secrets
info "Generating secure secrets..."

# Generate random passwords
POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)
BASIC_AUTH_USER="admin"
BASIC_AUTH_PASSWORD=$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -c 16)

# Generate Caddy password hash
# Caddy uses bcrypt, we need to run caddy in a container to hash
BASIC_AUTH_HASH=$(docker run --rm caddy:2.9-alpine caddy hash-password --plaintext "$BASIC_AUTH_PASSWORD" 2>/dev/null)

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
BASIC_AUTH_HASH=${BASIC_AUTH_HASH}

# Version
VERSION=$(cat /opt/network-agent/VERSION 2>/dev/null || echo "latest")
EOF

chmod 600 "$ENV_FILE"
log "Secrets generated and saved to $ENV_FILE"

# 3. Get network information
VM_IP=$(hostname -I | awk '{print $1}')

# 4. Display credentials
echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                    WEB INTERFACE CREDENTIALS                  ║"
echo "╠═══════════════════════════════════════════════════════════════╣"
echo "║                                                               ║"
printf "║  %-60s ║\n" "URL:      https://${VM_IP}"
printf "║  %-60s ║\n" "User:     ${BASIC_AUTH_USER}"
printf "║  %-60s ║\n" "Password: ${BASIC_AUTH_PASSWORD}"
echo "║                                                               ║"
echo "║  IMPORTANT: Save these credentials now!                       ║"
echo "║  They will not be shown again.                                ║"
echo "║                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# 5. Save credentials to temporary file for user reference
CREDS_FILE="/root/network-agent-credentials.txt"
cat > "$CREDS_FILE" << EOF
Network Agent Appliance - Credentials
Generated: $(date)

Web Interface:
  URL:      https://${VM_IP}
  User:     ${BASIC_AUTH_USER}
  Password: ${BASIC_AUTH_PASSWORD}

SSH:
  User:     root
  Password: (the one you just set)

IMPORTANT: Delete this file after saving credentials securely!
  rm $CREDS_FILE
EOF
chmod 600 "$CREDS_FILE"
warn "Credentials also saved to: $CREDS_FILE"
warn "Delete this file after saving credentials: rm $CREDS_FILE"
echo ""

# 6. Start Docker Compose
info "Starting Network Agent services..."
cd "$COMPOSE_DIR"

if docker compose up -d; then
    log "Services started successfully"
else
    error "Failed to start services. Check: docker compose logs"
fi

# 7. Wait for services to be healthy
info "Waiting for services to become healthy..."
TIMEOUT=300
ELAPSED=0
while [[ $ELAPSED -lt $TIMEOUT ]]; do
    if docker compose ps | grep -q "healthy"; then
        break
    fi
    sleep 5
    ELAPSED=$((ELAPSED + 5))
    echo -n "."
done
echo ""

# 8. Show service status
echo ""
info "Service Status:"
docker compose ps
echo ""

# 9. Create marker file
mkdir -p "$(dirname "$MARKER")"
touch "$MARKER"

# 10. Final message
echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                    SETUP COMPLETE!                            ║"
echo "╠═══════════════════════════════════════════════════════════════╣"
echo "║                                                               ║"
printf "║  %-60s ║\n" "Access: https://${VM_IP}"
echo "║                                                               ║"
echo "║  Commands:                                                    ║"
echo "║    systemctl status network-agent   # Service status          ║"
echo "║    docker compose logs -f           # View logs               ║"
echo "║    docker compose restart           # Restart services        ║"
echo "║                                                               ║"
echo "║  For L2/L3 scanning (host network mode):                      ║"
echo "║    cd /opt/network-agent                                      ║"
echo "║    docker compose down                                        ║"
echo "║    docker compose -f docker-compose.yml \\                     ║"
echo "║                   -f docker-compose.scan-mode.yml up -d       ║"
echo "║                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
