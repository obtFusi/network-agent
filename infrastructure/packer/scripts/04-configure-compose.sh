#!/bin/bash
# 04-configure-compose.sh - Set up Docker Compose directory
set -euo pipefail

echo "=== Configuring Docker Compose ==="

# Ensure directory exists (should be created by file provisioner)
mkdir -p /opt/network-agent

# Verify files were copied
echo "Checking files in /opt/network-agent:"
ls -la /opt/network-agent/

# Build the network-agent image
echo "Building network-agent image..."
cd /opt/network-agent
docker compose build net-agent

# Validate compose file
echo "Validating docker-compose.yml..."
docker compose config

echo "=== Compose configuration complete ==="
