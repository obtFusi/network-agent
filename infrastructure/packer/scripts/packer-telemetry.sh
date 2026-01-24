#!/bin/bash
# Packer Build Telemetry Helper
# Simple timing and resource tracking for Packer provisioner steps
#
# Usage:
#   source /usr/local/bin/telemetry.sh
#   telemetry_start "Step1_Base_packages"
#   ... commands ...
#   telemetry_end "Step1_Base_packages"
#   telemetry_summary  # at end of build

TELEMETRY_DIR=/var/log/packer-telemetry
mkdir -p "$TELEMETRY_DIR"

get_cpu_idle() {
    awk '/^cpu / {print $5}' /proc/stat
}

get_disk_stats() {
    # Returns: reads writes read_bytes write_bytes
    awk '/vda|sda/ {print $4, $8, $6*512, $10*512; exit}' /proc/diskstats 2>/dev/null || echo "0 0 0 0"
}

get_net_stats() {
    # Returns: rx_bytes tx_bytes
    awk '/eth0|ens/ {gsub(/:/, ""); print $2, $10; exit}' /proc/net/dev 2>/dev/null || echo "0 0"
}

get_mem_stats() {
    # Returns: used_mb available_mb
    awk '/MemTotal/ {total=$2} /MemAvailable/ {avail=$2} END {print int((total-avail)/1024), int(avail/1024)}' /proc/meminfo
}

telemetry_start() {
    local STEP_NAME="$1"
    local SAFE_NAME="${STEP_NAME//[^a-zA-Z0-9]/_}"
    local STEP_FILE="$TELEMETRY_DIR/step_${SAFE_NAME}"

    echo "$(date +%s.%N)" > "${STEP_FILE}_start_time"
    get_cpu_idle > "${STEP_FILE}_start_cpu"
    get_disk_stats > "${STEP_FILE}_start_disk"
    get_net_stats > "${STEP_FILE}_start_net"
    get_mem_stats > "${STEP_FILE}_start_mem"

    echo ''
    echo '═══════════════════════════════════════════════════════════════════════'
    echo "⏱️  [$STEP_NAME] START: $(date -Iseconds)"
    echo '───────────────────────────────────────────────────────────────────────'
}

telemetry_end() {
    local STEP_NAME="$1"
    local SAFE_NAME="${STEP_NAME//[^a-zA-Z0-9]/_}"
    local STEP_FILE="$TELEMETRY_DIR/step_${SAFE_NAME}"
    local END_TIME=$(date +%s.%N)
    local START_TIME=$(cat "${STEP_FILE}_start_time" 2>/dev/null || echo "$END_TIME")
    local DURATION=$(echo "$END_TIME - $START_TIME" | bc)

    # CPU analysis
    local CPU_START=$(cat "${STEP_FILE}_start_cpu" 2>/dev/null || echo 0)
    local CPU_END=$(get_cpu_idle)
    local CPU_DELTA=$((CPU_END - CPU_START))
    local DURATION_INT=${DURATION%.*}
    [[ -z "$DURATION_INT" || "$DURATION_INT" -eq 0 ]] && DURATION_INT=1
    local CPU_USED=$((100 - CPU_DELTA / DURATION_INT))
    [[ $CPU_USED -lt 0 ]] && CPU_USED=0
    [[ $CPU_USED -gt 100 ]] && CPU_USED=100

    # Disk analysis
    read DISK_START_R DISK_START_W DISK_START_RB DISK_START_WB < "${STEP_FILE}_start_disk" 2>/dev/null || { DISK_START_R=0; DISK_START_W=0; DISK_START_RB=0; DISK_START_WB=0; }
    read DISK_END_R DISK_END_W DISK_END_RB DISK_END_WB <<< $(get_disk_stats)
    local DISK_READS=$((DISK_END_R - DISK_START_R))
    local DISK_WRITES=$((DISK_END_W - DISK_START_W))
    local DISK_READ_MB=$(( (DISK_END_RB - DISK_START_RB) / 1048576 ))
    local DISK_WRITE_MB=$(( (DISK_END_WB - DISK_START_WB) / 1048576 ))

    # Network analysis
    read NET_START_RX NET_START_TX < "${STEP_FILE}_start_net" 2>/dev/null || { NET_START_RX=0; NET_START_TX=0; }
    read NET_END_RX NET_END_TX <<< $(get_net_stats)
    local NET_RX_MB=$(( (NET_END_RX - NET_START_RX) / 1048576 ))
    local NET_TX_MB=$(( (NET_END_TX - NET_START_TX) / 1048576 ))

    # Memory analysis
    read MEM_START_USED MEM_START_AVAIL < "${STEP_FILE}_start_mem" 2>/dev/null || { MEM_START_USED=0; MEM_START_AVAIL=0; }
    read MEM_END_USED MEM_END_AVAIL <<< $(get_mem_stats)
    local MEM_DELTA=$((MEM_END_USED - MEM_START_USED))

    # Calculate throughput
    local DISK_READ_RATE=$((DISK_READ_MB / DURATION_INT))
    local DISK_WRITE_RATE=$((DISK_WRITE_MB / DURATION_INT))
    local NET_RX_RATE=$((NET_RX_MB / DURATION_INT))
    local NET_TX_RATE=$((NET_TX_MB / DURATION_INT))

    echo '───────────────────────────────────────────────────────────────────────'
    echo "⏱️  [$STEP_NAME] END: $(date -Iseconds)"
    echo ''
    printf '  %-14s %s\n' 'Duration:' "${DURATION}s"
    printf '  %-14s %s\n' 'CPU:' "~${CPU_USED}% avg"
    printf '  %-14s %s\n' 'Memory:' "${MEM_END_USED}MB used (delta ${MEM_DELTA}MB)"
    printf '  %-14s %s\n' 'Disk Read:' "${DISK_READ_MB}MB (${DISK_READ_RATE}MB/s, ${DISK_READS} ops)"
    printf '  %-14s %s\n' 'Disk Write:' "${DISK_WRITE_MB}MB (${DISK_WRITE_RATE}MB/s, ${DISK_WRITES} ops)"
    printf '  %-14s %s\n' 'Net RX:' "${NET_RX_MB}MB (${NET_RX_RATE}MB/s)"
    printf '  %-14s %s\n' 'Net TX:' "${NET_TX_MB}MB (${NET_TX_RATE}MB/s)"
    echo '═══════════════════════════════════════════════════════════════════════'
    echo ''

    # Save to summary file
    echo "${STEP_NAME}|${DURATION}|${CPU_USED}|${MEM_END_USED}|${DISK_READ_MB}|${DISK_WRITE_MB}|${NET_RX_MB}|${NET_TX_MB}" >> "$TELEMETRY_DIR/summary.csv"

    # Cleanup temp files
    rm -f "${STEP_FILE}_start_"* 2>/dev/null || true
}

telemetry_summary() {
    echo ''
    echo '╔═══════════════════════════════════════════════════════════════════════╗'
    echo '║                    BUILD TELEMETRY SUMMARY                            ║'
    echo '╠═══════════════════════════════════════════════════════════════════════╣'
    if [ -f "$TELEMETRY_DIR/summary.csv" ]; then
        local TOTAL=0
        while IFS='|' read -r name dur cpu mem dr dw nr nt; do
            printf '║ %-25s %6ss  CPU:%3s%%  Net:%4sMB  Disk:%4sMB ║\n' "$name" "${dur%.*}" "$cpu" "$nr" "$dw"
            TOTAL=$(echo "$TOTAL + $dur" | bc)
        done < "$TELEMETRY_DIR/summary.csv"
        echo '╠═══════════════════════════════════════════════════════════════════════╣'
        printf '║ %-25s %6ss                                    ║\n' 'TOTAL BUILD TIME:' "${TOTAL%.*}"
    fi
    echo '╚═══════════════════════════════════════════════════════════════════════╝'
}

# Export functions for use in subshells
export -f telemetry_start telemetry_end telemetry_summary get_cpu_idle get_disk_stats get_net_stats get_mem_stats
export TELEMETRY_DIR
