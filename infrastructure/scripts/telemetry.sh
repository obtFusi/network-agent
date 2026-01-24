#!/bin/bash
# CI/CD Telemetry Helper
# Tracks step/job timing, resource usage, and stores to JSON for analysis
#
# Usage:
#   source telemetry.sh
#   telemetry_init "build" "0.10.2"
#   telemetry_step_start "download_base"
#   ... do work ...
#   telemetry_step_end "download_base"
#   telemetry_finalize

set -euo pipefail

# Configuration
TELEMETRY_DIR="${TELEMETRY_DIR:-/tmp/telemetry}"
TELEMETRY_FILE=""
JOB_NAME=""
VERSION=""
JOB_START_TIME=""

# Initialize telemetry for a job
telemetry_init() {
    JOB_NAME="$1"
    VERSION="${2:-unknown}"
    JOB_START_TIME=$(date +%s.%N)

    mkdir -p "$TELEMETRY_DIR"
    TELEMETRY_FILE="$TELEMETRY_DIR/${JOB_NAME}_$(date +%Y%m%d_%H%M%S).json"

    # Initialize JSON structure
    cat > "$TELEMETRY_FILE" << EOF
{
  "job": "$JOB_NAME",
  "version": "$VERSION",
  "timestamp": "$(date -Iseconds)",
  "runner": "$(hostname)",
  "git_sha": "${GITHUB_SHA:-unknown}",
  "git_ref": "${GITHUB_REF:-unknown}",
  "run_id": "${GITHUB_RUN_ID:-0}",
  "run_number": "${GITHUB_RUN_NUMBER:-0}",
  "job_start": $JOB_START_TIME,
  "steps": [],
  "system": {
    "cpus": $(nproc),
    "memory_total_mb": $(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo),
    "disk_total_gb": $(df -BG / | awk 'NR==2 {gsub("G",""); print $2}')
  }
}
EOF

    echo "📊 Telemetry initialized: $TELEMETRY_FILE"
    echo "::notice::Telemetry tracking enabled for job: $JOB_NAME"
}

# Start tracking a step
telemetry_step_start() {
    local STEP_NAME="$1"
    local STEP_FILE="$TELEMETRY_DIR/step_${STEP_NAME//[^a-zA-Z0-9_]/_}"

    # Record start metrics
    echo "$(date +%s.%N)" > "${STEP_FILE}_start_time"

    # CPU idle (from /proc/stat)
    awk '/^cpu / {print $5}' /proc/stat > "${STEP_FILE}_start_cpu"

    # Disk stats (reads, writes, read_bytes, write_bytes)
    awk '/[sv]da|nvme0n1/ {print $4, $8, $6*512, $10*512; exit}' /proc/diskstats > "${STEP_FILE}_start_disk" 2>/dev/null || echo "0 0 0 0" > "${STEP_FILE}_start_disk"

    # Network stats (rx_bytes, tx_bytes)
    awk '/eth0|ens|enp/ {gsub(/:/, ""); print $2, $10; exit}' /proc/net/dev > "${STEP_FILE}_start_net" 2>/dev/null || echo "0 0" > "${STEP_FILE}_start_net"

    # Memory (used_mb, available_mb)
    awk '/MemTotal/ {total=$2} /MemAvailable/ {avail=$2} END {print int((total-avail)/1024), int(avail/1024)}' /proc/meminfo > "${STEP_FILE}_start_mem"

    echo ""
    echo "═══════════════════════════════════════════════════════════════════════"
    echo "⏱️  [$STEP_NAME] START: $(date -Iseconds)"
    echo "───────────────────────────────────────────────────────────────────────"
}

# End tracking a step and record metrics
telemetry_step_end() {
    local STEP_NAME="$1"
    local STEP_FILE="$TELEMETRY_DIR/step_${STEP_NAME//[^a-zA-Z0-9_]/_}"
    local END_TIME=$(date +%s.%N)
    local START_TIME=$(cat "${STEP_FILE}_start_time" 2>/dev/null || echo "$END_TIME")
    local DURATION=$(echo "$END_TIME - $START_TIME" | bc)

    # CPU analysis
    local CPU_START=$(cat "${STEP_FILE}_start_cpu" 2>/dev/null || echo 0)
    local CPU_END=$(awk '/^cpu / {print $5}' /proc/stat)
    local CPU_DELTA=$((CPU_END - CPU_START))
    local CPU_USED=0
    if [[ "${DURATION%.*}" -gt 0 ]]; then
        CPU_USED=$((100 - CPU_DELTA / ${DURATION%.*}))
        [[ $CPU_USED -lt 0 ]] && CPU_USED=0
        [[ $CPU_USED -gt 100 ]] && CPU_USED=100
    fi

    # Disk analysis
    read DISK_START_R DISK_START_W DISK_START_RB DISK_START_WB < "${STEP_FILE}_start_disk" 2>/dev/null || { DISK_START_R=0; DISK_START_W=0; DISK_START_RB=0; DISK_START_WB=0; }
    read DISK_END_R DISK_END_W DISK_END_RB DISK_END_WB <<< $(awk '/[sv]da|nvme0n1/ {print $4, $8, $6*512, $10*512; exit}' /proc/diskstats 2>/dev/null || echo "0 0 0 0")
    local DISK_READS=$((DISK_END_R - DISK_START_R))
    local DISK_WRITES=$((DISK_END_W - DISK_START_W))
    local DISK_READ_MB=$(( (DISK_END_RB - DISK_START_RB) / 1048576 ))
    local DISK_WRITE_MB=$(( (DISK_END_WB - DISK_START_WB) / 1048576 ))

    # Network analysis
    read NET_START_RX NET_START_TX < "${STEP_FILE}_start_net" 2>/dev/null || { NET_START_RX=0; NET_START_TX=0; }
    read NET_END_RX NET_END_TX <<< $(awk '/eth0|ens|enp/ {gsub(/:/, ""); print $2, $10; exit}' /proc/net/dev 2>/dev/null || echo "0 0")
    local NET_RX_MB=$(( (NET_END_RX - NET_START_RX) / 1048576 ))
    local NET_TX_MB=$(( (NET_END_TX - NET_START_TX) / 1048576 ))

    # Memory analysis
    read MEM_START_USED MEM_START_AVAIL < "${STEP_FILE}_start_mem" 2>/dev/null || { MEM_START_USED=0; MEM_START_AVAIL=0; }
    read MEM_END_USED MEM_END_AVAIL <<< $(awk '/MemTotal/ {total=$2} /MemAvailable/ {avail=$2} END {print int((total-avail)/1024), int(avail/1024)}' /proc/meminfo)
    local MEM_DELTA=$((MEM_END_USED - MEM_START_USED))

    # Calculate throughput
    local DURATION_INT=${DURATION%.*}
    [[ -z "$DURATION_INT" || "$DURATION_INT" -eq 0 ]] && DURATION_INT=1
    local DISK_READ_RATE=$((DISK_READ_MB / DURATION_INT))
    local DISK_WRITE_RATE=$((DISK_WRITE_MB / DURATION_INT))
    local NET_RX_RATE=$((NET_RX_MB / DURATION_INT))
    local NET_TX_RATE=$((NET_TX_MB / DURATION_INT))

    # Output to console
    echo "───────────────────────────────────────────────────────────────────────"
    echo "⏱️  [$STEP_NAME] END: $(date -Iseconds)"
    echo ""
    printf '  %-14s %s\n' 'Duration:' "${DURATION}s"
    printf '  %-14s %s\n' 'CPU:' "~${CPU_USED}% avg"
    printf '  %-14s %s\n' 'Memory:' "${MEM_END_USED}MB used (Δ${MEM_DELTA}MB)"
    printf '  %-14s %s\n' 'Disk Read:' "${DISK_READ_MB}MB (${DISK_READ_RATE}MB/s, ${DISK_READS} ops)"
    printf '  %-14s %s\n' 'Disk Write:' "${DISK_WRITE_MB}MB (${DISK_WRITE_RATE}MB/s, ${DISK_WRITES} ops)"
    printf '  %-14s %s\n' 'Net RX:' "${NET_RX_MB}MB (${NET_RX_RATE}MB/s)"
    printf '  %-14s %s\n' 'Net TX:' "${NET_TX_MB}MB (${NET_TX_RATE}MB/s)"
    echo "═══════════════════════════════════════════════════════════════════════"
    echo ""

    # Append to JSON (using jq if available, otherwise simple append)
    local STEP_JSON=$(cat << EOF
{
    "name": "$STEP_NAME",
    "start_time": $START_TIME,
    "end_time": $END_TIME,
    "duration_s": $DURATION,
    "cpu_percent": $CPU_USED,
    "memory_used_mb": $MEM_END_USED,
    "memory_delta_mb": $MEM_DELTA,
    "disk_read_mb": $DISK_READ_MB,
    "disk_write_mb": $DISK_WRITE_MB,
    "disk_read_ops": $DISK_READS,
    "disk_write_ops": $DISK_WRITES,
    "disk_read_rate_mbs": $DISK_READ_RATE,
    "disk_write_rate_mbs": $DISK_WRITE_RATE,
    "net_rx_mb": $NET_RX_MB,
    "net_tx_mb": $NET_TX_MB,
    "net_rx_rate_mbs": $NET_RX_RATE,
    "net_tx_rate_mbs": $NET_TX_RATE
}
EOF
)

    if command -v jq &> /dev/null && [[ -f "$TELEMETRY_FILE" ]]; then
        local TMP_FILE=$(mktemp)
        jq ".steps += [$STEP_JSON]" "$TELEMETRY_FILE" > "$TMP_FILE" && mv "$TMP_FILE" "$TELEMETRY_FILE"
    fi

    # Cleanup temp files
    rm -f "${STEP_FILE}_start_"* 2>/dev/null || true
}

# Finalize telemetry and output summary
telemetry_finalize() {
    local JOB_END_TIME=$(date +%s.%N)
    local JOB_DURATION=$(echo "$JOB_END_TIME - $JOB_START_TIME" | bc)

    # Update JSON with final data
    if command -v jq &> /dev/null && [[ -f "$TELEMETRY_FILE" ]]; then
        local TMP_FILE=$(mktemp)
        jq ". + {job_end: $JOB_END_TIME, job_duration_s: $JOB_DURATION}" "$TELEMETRY_FILE" > "$TMP_FILE" && mv "$TMP_FILE" "$TELEMETRY_FILE"
    fi

    # Print summary
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════════════╗"
    echo "║                    TELEMETRY SUMMARY: $JOB_NAME"
    echo "╠═══════════════════════════════════════════════════════════════════════╣"

    if command -v jq &> /dev/null && [[ -f "$TELEMETRY_FILE" ]]; then
        jq -r '.steps[] | "║ \(.name | .[0:28] | . + " " * (28 - length)) \(.duration_s | tostring | .[0:8])s  CPU:\(.cpu_percent | tostring | . + " " * (3 - length))%  Net:\(.net_rx_mb)MB  Disk:\(.disk_write_mb)MB ║"' "$TELEMETRY_FILE" 2>/dev/null || true
        echo "╠═══════════════════════════════════════════════════════════════════════╣"
        printf '║ %-28s %8ss                                    ║\n' "TOTAL JOB TIME:" "${JOB_DURATION%.*}"
    fi

    echo "╚═══════════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "📊 Telemetry file: $TELEMETRY_FILE"

    # Output file path for GitHub Actions
    echo "TELEMETRY_FILE=$TELEMETRY_FILE" >> "${GITHUB_OUTPUT:-/dev/null}" 2>/dev/null || true
}

# Get the telemetry file path
telemetry_get_file() {
    echo "$TELEMETRY_FILE"
}

# Export functions
export -f telemetry_init telemetry_step_start telemetry_step_end telemetry_finalize telemetry_get_file
