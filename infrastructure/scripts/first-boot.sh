#!/bin/bash
# first-boot.sh - Network Agent Appliance First-Boot Setup
# Runs automatically on first boot - generates secrets and starts services
# Display a unique administrative password only on the VM console.
set +x
set -euo pipefail
umask 077

MARKER="/var/lib/network-agent/.initialized"
ENV_FILE="/opt/network-agent/.env"
COMPOSE_DIR="/opt/network-agent"
CREDS_FILE="/root/network-agent-credentials.txt"
CONSOLE_PASSWORD_FILE="/var/lib/network-agent/.console-bootstrap-password"

# Check if already initialized
if [[ -f "$MARKER" ]]; then
    exit 0
fi

# Check the console before creating or displaying a bootstrap password.
if [[ ! -t 1 || "$(readlink "/proc/$$/fd/1")" != /dev/tty1 ]]; then
    echo "First boot must run on the VM console (tty1)" >&2
    exit 1
fi

install -d -m 0700 "$(dirname "$MARKER")"
IFS=: read -r _ root_marker _ < <(getent shadow root)
if [[ "$root_marker" == '!' ]]; then
    if [[ ! -e "$CONSOLE_PASSWORD_FILE" ]]; then
        bootstrap_tmp=$(mktemp "${CONSOLE_PASSWORD_FILE}.XXXXXX")
        openssl rand -hex 24 > "$bootstrap_tmp"
        mv -- "$bootstrap_tmp" "$CONSOLE_PASSWORD_FILE"
    fi
    IFS= read -r console_password < "$CONSOLE_PASSWORD_FILE"
    if [[ ! "$console_password" =~ ^[a-f0-9]{48}$ ]]; then
        echo "Invalid console bootstrap file" >&2
        exit 1
    fi
    printf 'root:%s\n' "$console_password" | chpasswd
    printf '\nNetwork Agent initial console login\nUser: root\nPassword: %s\nChange it with passwd after signing in.\n\n' "$console_password"
    unset console_password
fi
unset root_marker

if [[ ! -e "$ENV_FILE" && ! -e "$CREDS_FILE" ]]; then
    env_tmp=$(mktemp "${ENV_FILE}.XXXXXX")
    creds_tmp=$(mktemp "${CREDS_FILE}.XXXXXX")
    trap 'rm -f -- "$env_tmp" "$creds_tmp"' EXIT
    # Generate secure secrets
    POSTGRES_PASSWORD=$(openssl rand -hex 32)
    BASIC_AUTH_USER="admin"
    BASIC_AUTH_PASSWORD=$(openssl rand -hex 16)
    SEARXNG_SECRET=$(openssl rand -hex 32)

    # Generate Caddy password hash (bcrypt)
    BASIC_AUTH_HASH=$(docker run --rm caddy:2.9-alpine caddy hash-password --plaintext "$BASIC_AUTH_PASSWORD" 2>/dev/null)

    # Escape $ characters in bcrypt hash for Docker Compose .env files
    BASIC_AUTH_HASH_ESCAPED=$(printf '%s' "$BASIC_AUTH_HASH" | sed 's/\$/\$\$/g')

    # Get version (with fallback)
    APPLIANCE_VERSION=$(cat /opt/network-agent/VERSION 2>/dev/null || echo "latest")

    # Write .env file
    cat > "$env_tmp" << EOF
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
    chmod 600 "$env_tmp"

    # Get network information
    VM_IP=$(hostname -I | awk '{print $1}')

    # Save credentials to file for user reference
    cat > "$creds_tmp" << EOF
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
    chmod 600 "$creds_tmp"

    mv -- "$creds_tmp" "$CREDS_FILE"
    mv -- "$env_tmp" "$ENV_FILE"
    trap - EXIT
elif [[ ! -s "$ENV_FILE" || ! -s "$CREDS_FILE" ]]; then
    echo "Incomplete first-boot credentials. Recover the matching files from the VM console." >&2
    exit 1
fi

# Start Docker Compose
cd "$COMPOSE_DIR"
docker compose up -d --wait

# The bootstrap file is only needed until the first successful start.
rm -f -- "$CONSOLE_PASSWORD_FILE"
touch "$MARKER"
