#!/bin/bash
# runner-wrapper.sh - Ephemeral GitHub Actions Runner Wrapper
#
# This script runs the GitHub Actions runner in ephemeral mode.
# After each job completes, the runner de-registers and this script
# re-registers it with a fresh token.
#
# SECURITY: Ephemeral mode ensures no state persists between jobs,
# reducing the attack surface for a public repository.
#
# Requirements:
#   - GITHUB_PAT environment variable with admin:repo scope
#   - Runner already downloaded to /opt/actions-runner
#
# Usage:
#   GITHUB_PAT=ghp_xxx ./runner-wrapper.sh

set -euo pipefail

RUNNER_DIR="/opt/actions-runner"
REPO_URL="https://github.com/obtFusi/network-agent"
RUNNER_NAME_PREFIX="proxmox-runner"

# Validate environment
if [[ -z "${GITHUB_PAT:-}" ]]; then
    echo "ERROR: GITHUB_PAT environment variable not set"
    echo "Required: Personal Access Token with admin:repo scope"
    exit 1
fi

if [[ ! -d "$RUNNER_DIR" ]]; then
    echo "ERROR: Runner directory not found: $RUNNER_DIR"
    exit 1
fi

# Function to get registration token
get_registration_token() {
    local token
    token=$(curl -sS -X POST \
        -H "Authorization: token ${GITHUB_PAT}" \
        -H "Accept: application/vnd.github.v3+json" \
        "https://api.github.com/repos/obtFusi/network-agent/actions/runners/registration-token" \
        | jq -r '.token')

    if [[ "$token" == "null" ]] || [[ -z "$token" ]]; then
        echo "ERROR: Failed to get registration token" >&2
        return 1
    fi
    echo "$token"
}

# Function to cleanup workspace
cleanup_workspace() {
    echo "[$(date -Iseconds)] Cleaning up workspace..."
    rm -rf "$RUNNER_DIR/_work"/* 2>/dev/null || true
    docker system prune -af --volumes 2>/dev/null || true
    sync
}

# Main loop
echo "=== GitHub Actions Ephemeral Runner ==="
echo "Repository: $REPO_URL"
echo "Runner directory: $RUNNER_DIR"
echo ""

cd "$RUNNER_DIR"

while true; do
    echo "[$(date -Iseconds)] === Starting new runner instance ==="

    # Get fresh registration token
    echo "[$(date -Iseconds)] Getting registration token..."
    TOKEN=$(get_registration_token) || {
        echo "[$(date -Iseconds)] Failed to get token, retrying in 30s..."
        sleep 30
        continue
    }

    # Remove old configuration if exists
    if [[ -f ".runner" ]]; then
        echo "[$(date -Iseconds)] Removing old configuration..."
        ./config.sh remove --token "$TOKEN" 2>/dev/null || true
    fi

    # Generate unique runner name
    RUNNER_NAME="${RUNNER_NAME_PREFIX}-$(date +%s)"

    # Configure runner in ephemeral mode
    echo "[$(date -Iseconds)] Configuring runner: $RUNNER_NAME"
    ./config.sh \
        --url "$REPO_URL" \
        --token "$TOKEN" \
        --name "$RUNNER_NAME" \
        --labels "self-hosted,Linux,X64,ova-builder" \
        --ephemeral \
        --unattended \
        --replace

    # Run the runner (blocks until job completes or no job assigned)
    echo "[$(date -Iseconds)] Starting runner (waiting for jobs)..."
    ./run.sh || {
        echo "[$(date -Iseconds)] Runner exited with error, will restart..."
    }

    echo "[$(date -Iseconds)] Job completed, runner will re-register..."

    # Cleanup between jobs
    cleanup_workspace

    # Small delay before re-registering
    sleep 5
done
