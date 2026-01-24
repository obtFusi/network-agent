#!/bin/bash
# Live Telemetry Monitor
# Usage: ./live-telemetry.sh [run_id]
#
# Polls GitHub Actions logs and displays telemetry in real-time

set -euo pipefail

REPO="obtFusi/network-agent"
RUN_ID="${1:-}"
REFRESH_INTERVAL=10

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get latest run if not specified
if [[ -z "$RUN_ID" ]]; then
    echo "Fetching latest appliance build run..."
    RUN_ID=$(gh run list --workflow=appliance-build.yml --limit=1 --json databaseId --jq '.[0].databaseId')
    echo "Using run ID: $RUN_ID"
fi

clear_screen() {
    printf "\033c"
}

print_header() {
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║              APPLIANCE BUILD - LIVE TELEMETRY MONITOR                  ║${NC}"
    echo -e "${CYAN}║                        Run ID: ${RUN_ID}                               ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_step_status() {
    local status="$1"
    local name="$2"
    local conclusion="${3:-}"

    case "$status" in
        completed)
            if [[ "$conclusion" == "success" ]]; then
                echo -e "  ${GREEN}✓${NC} $name"
            else
                echo -e "  ${RED}✗${NC} $name (${conclusion})"
            fi
            ;;
        in_progress)
            echo -e "  ${YELLOW}*${NC} $name ${YELLOW}(running)${NC}"
            ;;
        *)
            echo -e "  ${BLUE}○${NC} $name"
            ;;
    esac
}

parse_telemetry() {
    local log_file="$1"

    echo -e "\n${CYAN}═══ TELEMETRY DATA ═══${NC}\n"
    printf "%-25s %10s %6s %10s %12s %12s %8s %8s %8s\n" \
        "STEP" "DURATION" "CPU" "MEMORY" "DISK_READ" "DISK_WRITE" "UTIL%" "AWAIT" "QUEUE"
    echo "────────────────────────────────────────────────────────────────────────────────────────────────"

    # Parse telemetry blocks from logs
    grep -E "\[.*\] END:|Duration:|CPU:|Memory:|Disk Read:|Disk Write:|Disk I/O:" "$log_file" 2>/dev/null | \
    awk '
    /\[.*\] END:/ {
        if (step != "") {
            printf "%-25s %10s %6s %10s %12s %12s %8s %8s %8s\n", step, duration, cpu, memory, disk_read, disk_write, util, await, queue
        }
        match($0, /\[([^\]]+)\]/, arr)
        step = arr[1]
    }
    /Duration:/ { gsub(/Duration:/, ""); gsub(/s/, ""); duration = $1 "s" }
    /CPU:/ { gsub(/CPU:/, ""); gsub(/~/, ""); cpu = $1 }
    /Memory:/ { match($0, /Memory:\s*(\d+)MB/, arr); memory = arr[1] "MB" }
    /Disk Read:/ { match($0, /Disk Read:\s*(\d+)MB/, arr); disk_read = arr[1] "MB" }
    /Disk Write:/ { match($0, /Disk Write:\s*(\d+)MB/, arr); disk_write = arr[1] "MB" }
    /Disk I\/O:/ {
        match($0, /util=(\d+)%/, arr1); util = arr1[1] "%"
        match($0, /await=(\d+)ms/, arr2); await = arr2[1] "ms"
        match($0, /queue=([\d.]+)/, arr3); queue = arr3[1]
    }
    END {
        if (step != "") {
            printf "%-25s %10s %6s %10s %12s %12s %8s %8s %8s\n", step, duration, cpu, memory, disk_read, disk_write, util, await, queue
        }
    }
    '
}

show_runner_status() {
    echo -e "\n${CYAN}═══ RUNNER STATUS ═══${NC}\n"

    # Check if we can SSH to runner
    if ssh -o ConnectTimeout=2 root@github-runner 'true' 2>/dev/null; then
        # Get resource usage
        local cpu_usage=$(ssh root@github-runner 'top -bn1 | grep "Cpu(s)" | awk "{print \$2+\$4}"' 2>/dev/null || echo "N/A")
        local mem_info=$(ssh root@github-runner 'free -m | awk "/Mem:/ {printf \"%.1f/%.1fGB (%.0f%%)\", \$3/1024, \$2/1024, \$3*100/\$2}"' 2>/dev/null || echo "N/A")
        local disk_info=$(ssh root@github-runner 'df -h / | awk "NR==2 {printf \"%s/%s (%s)\", \$3, \$2, \$5}"' 2>/dev/null || echo "N/A")
        local ollama_size=$(ssh root@github-runner 'du -sh /usr/share/ollama/.ollama/models/ 2>/dev/null | cut -f1' 2>/dev/null || echo "N/A")
        local qemu_running=$(ssh root@github-runner 'pgrep -c qemu-system-x86_64 2>/dev/null || echo 0' 2>/dev/null)

        echo -e "  CPU Usage:      ${YELLOW}${cpu_usage}%${NC}"
        echo -e "  Memory:         ${YELLOW}${mem_info}${NC}"
        echo -e "  Disk:           ${YELLOW}${disk_info}${NC}"
        echo -e "  Ollama Models:  ${YELLOW}${ollama_size}${NC}"
        echo -e "  QEMU VMs:       ${YELLOW}${qemu_running}${NC}"
    else
        echo -e "  ${RED}Cannot connect to runner via SSH${NC}"
    fi
}

main() {
    while true; do
        clear_screen
        print_header

        # Get run status
        local run_data=$(gh run view "$RUN_ID" --json status,conclusion,jobs 2>/dev/null)
        local status=$(echo "$run_data" | jq -r '.status')
        local conclusion=$(echo "$run_data" | jq -r '.conclusion // empty')

        echo -e "${CYAN}═══ WORKFLOW STATUS ═══${NC}\n"
        echo -e "  Status: ${YELLOW}${status}${NC}"
        [[ -n "$conclusion" ]] && echo -e "  Conclusion: ${conclusion}"
        echo ""

        # Get job steps
        local jobs=$(echo "$run_data" | jq -r '.jobs[]')
        local build_job=$(echo "$run_data" | jq -r '.jobs[] | select(.name=="Build Appliance")')

        if [[ -n "$build_job" ]]; then
            echo -e "${CYAN}═══ BUILD STEPS ═══${NC}\n"
            echo "$build_job" | jq -r '.steps[] | "\(.status)|\(.name)|\(.conclusion // "")"' | while IFS='|' read -r step_status step_name step_conclusion; do
                print_step_status "$step_status" "$step_name" "$step_conclusion"
            done
        fi

        # Show runner status if SSH is available
        show_runner_status

        # Try to get and parse logs for telemetry
        local job_id=$(echo "$build_job" | jq -r '.databaseId // empty')
        if [[ -n "$job_id" ]]; then
            local log_file="/tmp/run_${RUN_ID}_logs.txt"
            gh run view --job="$job_id" --log > "$log_file" 2>/dev/null || true
            if [[ -s "$log_file" ]]; then
                parse_telemetry "$log_file"
            fi
        fi

        # Status line
        echo ""
        echo -e "${BLUE}Last updated: $(date '+%H:%M:%S') | Refresh: ${REFRESH_INTERVAL}s | Press Ctrl+C to exit${NC}"

        # Exit if completed
        if [[ "$status" == "completed" ]]; then
            echo -e "\n${GREEN}Build completed with conclusion: ${conclusion}${NC}"
            break
        fi

        sleep "$REFRESH_INTERVAL"
    done
}

main
