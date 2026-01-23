#!/bin/bash
# 03-pull-ollama-model.sh - Pre-download Ollama model (with caching support)
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
SECONDARY_MODEL="qwen3:4b-instruct-2507-q4_K_M"

echo "Primary model: $PRIMARY_MODEL"
echo "Secondary model: $SECONDARY_MODEL"

# Create Docker volume for models
docker volume create ollama-models

# Check if cached models are available from host (injected via Packer file provisioner)
CACHE_DIR="/tmp/ollama-cache/models"
if [[ -d "$CACHE_DIR" && -n "$(ls -A $CACHE_DIR 2>/dev/null)" ]]; then
    echo "=== Using cached models from host (FAST PATH ~2min) ==="
    echo "Cache contents:"
    ls -lh "$CACHE_DIR"

    # Start Ollama container with models directory mounted directly
    docker run -d --name ollama-temp \
        -v ollama-models:/root/.ollama \
        ollama/ollama:0.14.1

    # Wait for container
    sleep 3

    # Copy the entire models directory structure
    echo "Copying cached models to Docker volume..."
    docker cp "$CACHE_DIR/." ollama-temp:/root/.ollama/models/

    # Verify models are recognized
    echo "Verifying cached models..."
    for i in {1..10}; do
        if docker exec ollama-temp ollama list 2>/dev/null | grep -q "qwen"; then
            echo "✅ Models loaded successfully!"
            docker exec ollama-temp ollama list
            break
        fi
        echo "Waiting for model recognition... ($i/10)"
        sleep 2
    done

    # Cleanup
    docker stop ollama-temp
    docker rm ollama-temp

    echo "=== Cached models loaded successfully ==="
    exit 0
fi

echo "=== No cache found, downloading from registry (SLOW PATH) ==="

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
echo "Pulling primary model: $PRIMARY_MODEL (this takes ~20-25 min for 18GB)"
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
