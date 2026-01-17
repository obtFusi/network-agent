#!/bin/bash
# 02-pull-images.sh - Pre-pull Docker images with pinned versions
set -euo pipefail

echo "=== Pulling Docker images ==="

# Pinned versions for reproducible builds
OLLAMA_VERSION="0.5.4"
POSTGRES_VERSION="16.6-alpine"
CADDY_VERSION="2.9-alpine"
SEARXNG_VERSION="2024.12.23"

# Pull all required images with pinned versions
echo "Pulling ollama/ollama:${OLLAMA_VERSION}..."
docker pull "ollama/ollama:${OLLAMA_VERSION}"

echo "Pulling postgres:${POSTGRES_VERSION}..."
docker pull "postgres:${POSTGRES_VERSION}"

echo "Pulling caddy:${CADDY_VERSION}..."
docker pull "caddy:${CADDY_VERSION}"

# SearXNG is optional (online mode) but pre-pull for convenience
echo "Pulling searxng/searxng:${SEARXNG_VERSION}..."
docker pull "searxng/searxng:${SEARXNG_VERSION}"

# List pulled images
echo ""
echo "=== Pulled images ==="
docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}"

echo "=== Image pull complete ==="
