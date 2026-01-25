#!/bin/bash
# Serve Build Status - Generates JSON for the dashboard
# Runs in background and updates a JSON file every 10 seconds
#
# Usage: ./serve-build-status.sh [run_id]
# The JSON is written to /tmp/build-status.json and served via nginx

set -euo pipefail

REPO="obtFusi/network-agent"
RUN_ID="${1:-}"
OUTPUT_FILE="/tmp/build-status.json"
REFRESH_INTERVAL=10

# Get latest run if not specified
get_run_id() {
    if [[ -z "$RUN_ID" ]]; then
        RUN_ID=$(gh run list --workflow=appliance-build.yml --repo "$REPO" --limit=1 --json databaseId --jq '.[0].databaseId' 2>/dev/null || echo "")
    fi
    echo "$RUN_ID"
}

# Fetch and format build status as JSON
fetch_status() {
    local run_id=$(get_run_id)
    if [[ -z "$run_id" ]]; then
        echo '{"error": "No runs found"}'
        return
    fi

    gh run view "$run_id" --repo "$REPO" --json status,conclusion,createdAt,updatedAt,headBranch,jobs,url 2>/dev/null | jq --arg rid "$run_id" '{
        run_id: $rid,
        job: "Build Appliance",
        version: .headBranch,
        status: .status,
        conclusion: .conclusion,
        started_at: .createdAt,
        updated_at: .updatedAt,
        url: .url,
        steps: [.jobs[] | select(.name=="Build Appliance") | .steps[] | {
            name: .name,
            status: .status,
            conclusion: .conclusion,
            started_at: .startedAt,
            completed_at: .completedAt,
            duration_s: (if .startedAt and .completedAt then
                ((.completedAt | fromdateiso8601) - (.startedAt | fromdateiso8601))
                else 0 end)
        }]
    }' 2>/dev/null || echo '{"error": "Failed to fetch run data"}'
}

# Main loop
echo "Starting build status server for run: $(get_run_id)"
echo "Output: $OUTPUT_FILE"
echo "Refresh: ${REFRESH_INTERVAL}s"
echo ""

while true; do
    fetch_status > "$OUTPUT_FILE"
    echo "[$(date '+%H:%M:%S')] Updated $OUTPUT_FILE"

    # Check if build is completed
    status=$(jq -r '.status // "unknown"' "$OUTPUT_FILE" 2>/dev/null)
    if [[ "$status" == "completed" ]]; then
        echo "Build completed!"
        break
    fi

    sleep "$REFRESH_INTERVAL"
done
