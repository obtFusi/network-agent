#!/bin/bash
# 03-pull-ollama-model.sh - Ollama model management (verify or update)
#
# NOTE: Models are now PRE-BAKED into the base image via Packer.
# This script is only used for:
#   1. Runtime verification that models exist
#   2. Manual model updates (ollama pull)
#
set -euo pipefail

echo "=== Ollama Model Management ==="

# Check if we should include the model
if [[ "${INCLUDE_MODEL:-true}" != "true" ]]; then
    echo "Skipping model management (INCLUDE_MODEL=false)"
    exit 0
fi

# Expected models
PRIMARY_MODEL="${OLLAMA_MODEL:-qwen3:30b-a3b}"
SECONDARY_MODEL="qwen3:4b-instruct-2507-q4_K_M"

echo "Primary model: $PRIMARY_MODEL"
echo "Secondary model: $SECONDARY_MODEL"

# Check if Ollama is running
if ! systemctl is-active --quiet ollama; then
    echo "Starting Ollama service..."
    systemctl start ollama
    sleep 3
fi

# Verify pre-baked models exist
echo ""
echo "Checking pre-baked models..."
MODELS=$(ollama list 2>/dev/null || echo "")

if echo "$MODELS" | grep -q "qwen"; then
    echo "✅ Pre-baked models found:"
    ollama list
    echo ""
    echo "=== Models ready (pre-baked) ==="
    exit 0
fi

# No pre-baked models - pull from registry (manual update case)
echo "⚠️  No pre-baked models found - pulling from registry..."
echo "This may take 20-30 minutes for large models."
echo ""

ollama pull "$PRIMARY_MODEL"
ollama pull "$SECONDARY_MODEL"

echo ""
echo "Verifying models..."
ollama list

echo ""
echo "=== Models ready (pulled from registry) ==="
