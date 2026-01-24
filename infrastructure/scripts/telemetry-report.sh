#!/bin/bash
# Telemetry Report Generator
# Reads telemetry data from MinIO and generates reports
#
# Usage:
#   ./telemetry-report.sh latest          # Show latest build telemetry
#   ./telemetry-report.sh list            # List all available telemetry
#   ./telemetry-report.sh compare V1 V2   # Compare two versions
#   ./telemetry-report.sh history N       # Show last N builds

set -euo pipefail

# Configuration (can be overridden via environment)
MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://10.0.0.165:9000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-}"
TELEMETRY_BUCKET="${TELEMETRY_BUCKET:-appliance-telemetry}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check for mc client
setup_mc() {
    if ! command -v mc &> /dev/null; then
        echo "Installing MinIO client..."
        wget -q https://dl.min.io/client/mc/release/linux-amd64/mc -O /tmp/mc
        chmod +x /tmp/mc
        MC="/tmp/mc"
    else
        MC="mc"
    fi

    # Configure alias
    $MC alias set minio "$MINIO_ENDPOINT" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" &>/dev/null
}

# List all available telemetry
cmd_list() {
    setup_mc
    echo -e "${BLUE}Available Telemetry Data:${NC}"
    echo "═══════════════════════════════════════════════════════════════════════"
    $MC ls minio/$TELEMETRY_BUCKET/ --recursive 2>/dev/null | grep ".json" | while read -r line; do
        echo "  $line"
    done
    echo ""
    echo -e "${BLUE}Latest builds:${NC}"
    $MC ls minio/$TELEMETRY_BUCKET/latest/ 2>/dev/null || echo "  No latest data found"
}

# Show latest telemetry
cmd_latest() {
    setup_mc
    local TYPE="${1:-build}"

    echo -e "${BLUE}Latest ${TYPE} Telemetry:${NC}"
    echo "═══════════════════════════════════════════════════════════════════════"

    # Download latest telemetry
    local LATEST=$($MC ls minio/$TELEMETRY_BUCKET/latest/ 2>/dev/null | grep "${TYPE}_" | tail -1 | awk '{print $NF}')

    if [[ -z "$LATEST" ]]; then
        echo -e "${RED}No telemetry data found${NC}"
        exit 1
    fi

    local TMP=$(mktemp)
    $MC cat "minio/$TELEMETRY_BUCKET/latest/$LATEST" > "$TMP" 2>/dev/null

    if command -v jq &> /dev/null; then
        echo ""
        echo -e "${GREEN}Job:${NC} $(jq -r '.job' "$TMP")"
        echo -e "${GREEN}Version:${NC} $(jq -r '.version' "$TMP")"
        echo -e "${GREEN}Timestamp:${NC} $(jq -r '.timestamp' "$TMP")"
        echo -e "${GREEN}Runner:${NC} $(jq -r '.runner' "$TMP")"
        echo -e "${GREEN}Total Duration:${NC} $(jq -r '.job_duration_s // "N/A"' "$TMP")s"
        echo ""
        echo -e "${BLUE}Steps:${NC}"
        echo "────────────────────────────────────────────────────────────────────────────────────────────"
        printf "%-25s %8s %6s %8s %6s %7s %6s %8s\n" "STEP" "DUR" "CPU%" "DISK_W" "UTIL%" "AWAIT" "QUEUE" "NET_RX"
        echo "────────────────────────────────────────────────────────────────────────────────────────────"
        jq -r '.steps[] | "\(.name)\t\(.duration_s)s\t\(.cpu_percent)%\t\(.disk_write_mb)MB\t\(.disk_util_percent // 0)%\t\(.await_ms // 0)ms\t\(.queue_depth // 0)\t\(.net_rx_mb)MB"' "$TMP" | \
        while IFS=$'\t' read -r name dur cpu disk util await queue net; do
            printf "%-25s %8s %6s %8s %6s %7s %6s %8s\n" "$name" "$dur" "$cpu" "$disk" "$util" "$await" "$queue" "$net"
        done
        echo "────────────────────────────────────────────────────────────────────────────────────────────"

        # Identify bottlenecks
        echo ""
        echo -e "${YELLOW}Bottleneck Analysis:${NC}"

        # Find slowest step
        SLOWEST=$(jq -r '.steps | max_by(.duration_s) | "\(.name): \(.duration_s)s"' "$TMP")
        echo "  Slowest step: $SLOWEST"

        # Find most network-intensive step
        NETWORK=$(jq -r '.steps | max_by(.net_rx_mb) | "\(.name): \(.net_rx_mb)MB downloaded"' "$TMP")
        echo "  Most network I/O: $NETWORK"

        # Find most disk-intensive step
        DISK=$(jq -r '.steps | max_by(.disk_write_mb) | "\(.name): \(.disk_write_mb)MB written"' "$TMP")
        echo "  Most disk I/O: $DISK"

        # Find highest disk utilization
        DISK_UTIL=$(jq -r '.steps | max_by(.disk_util_percent // 0) | "\(.name): \(.disk_util_percent // 0)% util"' "$TMP")
        echo "  Highest disk util: $DISK_UTIL"

        # Find highest await time
        AWAIT=$(jq -r '.steps | max_by(.await_ms // 0) | "\(.name): \(.await_ms // 0)ms await"' "$TMP")
        echo "  Highest I/O wait: $AWAIT"

        # Find highest queue depth
        QUEUE=$(jq -r '.steps | max_by(.queue_depth // 0) | "\(.name): \(.queue_depth // 0) queue"' "$TMP")
        echo "  Highest queue depth: $QUEUE"

        # Find highest memory usage
        MEMORY=$(jq -r '.steps | max_by(.memory_used_mb) | "\(.name): \(.memory_used_mb)MB"' "$TMP")
        echo "  Peak memory: $MEMORY"

    else
        cat "$TMP"
    fi

    rm -f "$TMP"
}

# Compare two versions
cmd_compare() {
    local V1="$1"
    local V2="$2"
    setup_mc

    echo -e "${BLUE}Comparing $V1 vs $V2:${NC}"
    echo "═══════════════════════════════════════════════════════════════════════"

    local TMP1=$(mktemp)
    local TMP2=$(mktemp)

    $MC cat "minio/$TELEMETRY_BUCKET/latest/build_${V1}.json" > "$TMP1" 2>/dev/null || { echo "Cannot find telemetry for $V1"; exit 1; }
    $MC cat "minio/$TELEMETRY_BUCKET/latest/build_${V2}.json" > "$TMP2" 2>/dev/null || { echo "Cannot find telemetry for $V2"; exit 1; }

    if command -v jq &> /dev/null; then
        local DUR1=$(jq -r '.job_duration_s // 0' "$TMP1")
        local DUR2=$(jq -r '.job_duration_s // 0' "$TMP2")
        local DIFF=$(echo "$DUR2 - $DUR1" | bc)

        echo ""
        printf "%-20s %15s %15s %15s\n" "Metric" "$V1" "$V2" "Diff"
        echo "───────────────────────────────────────────────────────────────────────"
        printf "%-20s %14ss %14ss %14ss\n" "Total Duration" "$DUR1" "$DUR2" "$DIFF"

        # Compare individual steps
        echo ""
        echo -e "${BLUE}Step Comparison:${NC}"
        echo "───────────────────────────────────────────────────────────────────────"

        jq -r '.steps[].name' "$TMP1" | while read -r step; do
            S1=$(jq -r ".steps[] | select(.name == \"$step\") | .duration_s" "$TMP1" 2>/dev/null || echo "0")
            S2=$(jq -r ".steps[] | select(.name == \"$step\") | .duration_s" "$TMP2" 2>/dev/null || echo "0")
            SDIFF=$(echo "${S2:-0} - ${S1:-0}" | bc 2>/dev/null || echo "N/A")
            printf "%-30s %10ss %10ss %10ss\n" "$step" "${S1:-N/A}" "${S2:-N/A}" "$SDIFF"
        done
    fi

    rm -f "$TMP1" "$TMP2"
}

# Show history
cmd_history() {
    local N="${1:-5}"
    setup_mc

    echo -e "${BLUE}Last $N Builds:${NC}"
    echo "═══════════════════════════════════════════════════════════════════════"

    $MC ls minio/$TELEMETRY_BUCKET/latest/ 2>/dev/null | grep "build_" | tail -n "$N" | while read -r line; do
        FILE=$(echo "$line" | awk '{print $NF}')
        TMP=$(mktemp)
        $MC cat "minio/$TELEMETRY_BUCKET/latest/$FILE" > "$TMP" 2>/dev/null || continue

        if command -v jq &> /dev/null; then
            VERSION=$(jq -r '.version' "$TMP")
            TIMESTAMP=$(jq -r '.timestamp' "$TMP")
            DURATION=$(jq -r '.job_duration_s // "N/A"' "$TMP")
            printf "%-15s %-25s %10ss\n" "$VERSION" "$TIMESTAMP" "$DURATION"
        fi
        rm -f "$TMP"
    done
}

# Main
case "${1:-latest}" in
    list)
        cmd_list
        ;;
    latest)
        cmd_latest "${2:-build}"
        ;;
    compare)
        if [[ -z "${2:-}" || -z "${3:-}" ]]; then
            echo "Usage: $0 compare VERSION1 VERSION2"
            exit 1
        fi
        cmd_compare "$2" "$3"
        ;;
    history)
        cmd_history "${2:-5}"
        ;;
    *)
        echo "Usage: $0 {list|latest [build|e2e]|compare V1 V2|history N}"
        exit 1
        ;;
esac
