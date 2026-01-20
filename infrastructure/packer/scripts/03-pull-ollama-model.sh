#!/bin/bash
# 03-pull-ollama-model.sh - Pre-download Ollama model
set -euo pipefail

echo "=== Pulling Ollama model ==="

# Check if we should include the model
if [[ "${INCLUDE_MODEL:-true}" != "true" ]]; then
    echo "Skipping model download (INCLUDE_MODEL=false)"
    exit 0
fi

# Primary model (larger, better quality)
PRIMARY_MODEL="${OLLAMA_MODEL:-qwen3:30b-a3b}"
# Secondary model (smaller, faster for CPU-only)
SECONDARY_MODEL="qwen3:4b"

echo "Primary model: $PRIMARY_MODEL"
echo "Secondary model: $SECONDARY_MODEL"

# Create Docker volume for models
docker volume create ollama-models

# Start Ollama temporarily to pull model (using pinned version)
echo "Starting Ollama container..."
docker run -d --name ollama-temp \
    -v ollama-models:/root/.ollama \
    ollama/ollama:0.14.1

# Wait for Ollama to be ready
echo "Waiting for Ollama to start..."
for i in {1..30}; do
    if docker exec ollama-temp curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "Ollama is ready"
        break
    fi
    echo "Waiting... ($i/30)"
    sleep 2
done

# Pull the primary model
echo "Pulling primary model: $PRIMARY_MODEL"
docker exec ollama-temp ollama pull "$PRIMARY_MODEL"

# Pull the secondary model (smaller, faster)
echo "Pulling secondary model: $SECONDARY_MODEL"
docker exec ollama-temp ollama pull "$SECONDARY_MODEL"

# Verify models were downloaded
echo "Verifying models..."
docker exec ollama-temp ollama list

# Stop and remove temp container
echo "Cleaning up..."
docker stop ollama-temp
docker rm ollama-temp

echo "=== Model pull complete ==="
