#!/bin/bash
# Updates build-status.json for the dashboard
# Run this in background: ./update-build-status.sh &
#
# The dashboard at localhost:8000/network-agent/infrastructure/telemetry-dashboard.html
# will automatically pick up the data - no token needed!

set -euo pipefail

REPO="obtFusi/network-agent"
OUTPUT_FILE="/work/network-agent/infrastructure/build-status.json"
INTERVAL=10

echo "=== Build Status Updater ==="
echo "Output: $OUTPUT_FILE"
echo "Refresh: ${INTERVAL}s"
echo ""

update_status() {
    local run_id=$(gh run list --workflow=appliance-build.yml --repo "$REPO" --limit=1 --json databaseId,status --jq '.[0] | "\(.databaseId)|\(.status)"' 2>/dev/null)

    if [[ -z "$run_id" ]]; then
        echo '{"error": "No runs found"}' > "$OUTPUT_FILE"
        return
    fi

    local id="${run_id%|*}"
    local status_json
    local logs_array="[]"

    # Fetch status
    status_json=$(gh run view "$id" --repo "$REPO" --json status,conclusion,createdAt,updatedAt,headBranch,jobs,url 2>/dev/null)

    if [[ -z "$status_json" ]]; then
        echo '{"error": "Failed to fetch"}' > "$OUTPUT_FILE"
        return
    fi

    local build_status=$(echo "$status_json" | jq -r '.status')

    # Collect live metrics and logs from runner via SSH (only during build)
    local metrics_json="{}"
    if [[ "$build_status" == "in_progress" ]]; then
        # Collect logs from Packer build (last 100 lines)
        logs_array=$(ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no root@github-runner '
            LOG="/tmp/packer-build.log"
            if [[ -f "$LOG" ]]; then
                # Get last 100 lines, escape for JSON, strip ANSI
                tail -100 "$LOG" 2>/dev/null | \
                    sed "s/\x1b\[[0-9;]*m//g" | \
                    jq -Rs "split(\"\n\") | map(select(length > 0))"
            else
                echo "[]"
            fi
        ' 2>/dev/null || echo '[]')
        metrics_json=$(ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no root@github-runner '
            STATE_FILE="/tmp/metrics_state"
            NOW=$(date +%s)

            # CPU from vmstat (1 second sample)
            cpu_line=$(vmstat 1 2 | tail -1)
            cpu_user=$(echo $cpu_line | awk "{print \$13}")
            cpu_sys=$(echo $cpu_line | awk "{print \$14}")
            cpu_idle=$(echo $cpu_line | awk "{print \$15}")
            cpu_iowait=$(echo $cpu_line | awk "{print \$16}")

            # Memory
            mem_line=$(free -m | grep Mem)
            mem_total=$(echo $mem_line | awk "{print \$2}")
            mem_used=$(echo $mem_line | awk "{print \$3}")
            mem_free=$(echo $mem_line | awk "{print \$4}")

            # Disk I/O from /proc/diskstats
            disk_line=$(cat /proc/diskstats | grep -E "sda |vda " | head -1)
            disk_reads=$(echo $disk_line | awk "{print \$4}")
            disk_writes=$(echo $disk_line | awk "{print \$8}")
            disk_read_sectors=$(echo $disk_line | awk "{print \$6}")
            disk_write_sectors=$(echo $disk_line | awk "{print \$10}")

            # Network from /proc/net/dev (all interfaces)
            net_rx=0; net_tx=0
            while read iface rx_bytes _ _ _ _ _ _ _ tx_bytes _; do
                iface=${iface%:}
                [[ "$iface" =~ ^(lo|docker|br-|veth) ]] && continue
                net_rx=$((net_rx + rx_bytes))
                net_tx=$((net_tx + tx_bytes))
            done < <(cat /proc/net/dev | tail -n +3)

            # Load average
            load=$(cat /proc/loadavg | awk "{print \$1}")

            # Calculate rates from previous state
            disk_read_rate=0; disk_write_rate=0; net_rx_rate=0; net_tx_rate=0; iops=0
            if [[ -f "$STATE_FILE" ]]; then
                source "$STATE_FILE"
                elapsed=$((NOW - PREV_TIME))
                if [[ $elapsed -gt 0 ]]; then
                    # Disk: sectors to MB/s (512 bytes per sector)
                    disk_read_rate=$(( (disk_read_sectors - PREV_DISK_READ) * 512 / elapsed / 1024 / 1024 ))
                    disk_write_rate=$(( (disk_write_sectors - PREV_DISK_WRITE) * 512 / elapsed / 1024 / 1024 ))
                    # IOPS
                    iops=$(( (disk_reads - PREV_DISK_READS + disk_writes - PREV_DISK_WRITES) / elapsed ))
                    # Network: bytes to MB/s
                    net_rx_rate=$(( (net_rx - PREV_NET_RX) / elapsed / 1024 / 1024 ))
                    net_tx_rate=$(( (net_tx - PREV_NET_TX) / elapsed / 1024 / 1024 ))
                fi
            fi

            # QEMU process info and I/O (captures VM traffic!)
            qemu_pid=$(pgrep -f "qemu-system" | head -1)
            qemu_mem=""; qemu_cpu=""; qemu_read=0; qemu_write=0
            qemu_read_rate=0; qemu_write_rate=0
            if [[ -n "$qemu_pid" ]]; then
                qemu_stats=$(ps -p $qemu_pid -o %cpu,%mem --no-headers 2>/dev/null)
                qemu_cpu=$(echo $qemu_stats | awk "{print \$1}")
                qemu_mem=$(echo $qemu_stats | awk "{print \$2}")
                # Get QEMU process I/O from /proc (this captures VM network + disk!)
                if [[ -f "/proc/$qemu_pid/io" ]]; then
                    qemu_read=$(grep "^read_bytes:" /proc/$qemu_pid/io | awk "{print \$2}")
                    qemu_write=$(grep "^write_bytes:" /proc/$qemu_pid/io | awk "{print \$2}")
                    # Calculate rates from previous state
                    if [[ -f "$STATE_FILE" ]] && grep -q "PREV_QEMU_READ" "$STATE_FILE" 2>/dev/null; then
                        source "$STATE_FILE"
                        if [[ $elapsed -gt 0 && -n "$PREV_QEMU_READ" ]]; then
                            qemu_read_rate=$(( (qemu_read - PREV_QEMU_READ) / elapsed / 1024 / 1024 ))
                            qemu_write_rate=$(( (qemu_write - PREV_QEMU_WRITE) / elapsed / 1024 / 1024 ))
                        fi
                    fi
                fi
            fi

            # Save state for next iteration (include QEMU I/O)
            cat > "$STATE_FILE" << EOF
PREV_TIME=$NOW
PREV_DISK_READ=$disk_read_sectors
PREV_DISK_WRITE=$disk_write_sectors
PREV_DISK_READS=$disk_reads
PREV_DISK_WRITES=$disk_writes
PREV_NET_RX=$net_rx
PREV_NET_TX=$net_tx
PREV_QEMU_READ=$qemu_read
PREV_QEMU_WRITE=$qemu_write
EOF

            # Output JSON with rates (use QEMU I/O for disk/net during VM build)
            cat << EOF
{
  "cpu_user":$cpu_user,"cpu_sys":$cpu_sys,"cpu_idle":$cpu_idle,"cpu_iowait":$cpu_iowait,
  "mem_total":$mem_total,"mem_used":$mem_used,"mem_free":$mem_free,
  "disk_read_mb":$qemu_read_rate,"disk_write_mb":$qemu_write_rate,"iops":$iops,
  "net_rx_mb":$qemu_read_rate,"net_tx_mb":$qemu_write_rate,
  "net_rx_total":$qemu_read,"net_tx_total":$qemu_write,
  "load":$load,"qemu_cpu":"$qemu_cpu","qemu_mem":"$qemu_mem"
}
EOF
        ' 2>/dev/null || echo '{}')

        # Also get Packer internal steps from log with telemetry metrics
        packer_steps=$(ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no root@github-runner '
            LOG="/tmp/packer-build.log"
            [[ ! -f "$LOG" ]] && echo "[]" && exit 0

            # Extract telemetry data from log
            declare -A starts
            declare -A ends
            declare -A cpu
            declare -A mem
            declare -A disk_read
            declare -A disk_write
            declare -A disk_util
            declare -A await
            declare -A queue

            # Parse ANSI-stripped log
            while IFS= read -r line; do
                # Strip ANSI
                line=$(echo "$line" | sed "s/\x1b\[[0-9;]*m//g")

                # Extract step name from START/END markers
                if [[ "$line" =~ \[([A-Za-z0-9_]+)\]\ START:\ ([0-9T:+-]+) ]]; then
                    step="${BASH_REMATCH[1]}"
                    starts["$step"]="${BASH_REMATCH[2]}"
                    current_step="$step"
                elif [[ "$line" =~ \[([A-Za-z0-9_]+)\]\ END:\ ([0-9T:+-]+) ]]; then
                    step="${BASH_REMATCH[1]}"
                    ends["$step"]="${BASH_REMATCH[2]}"
                fi

                # Extract metrics for current step
                if [[ -n "$current_step" ]]; then
                    if [[ "$line" =~ CPU:\ ~?([0-9.]+)% ]]; then
                        cpu["$current_step"]="${BASH_REMATCH[1]}"
                    fi
                    if [[ "$line" =~ Memory:\ ([0-9]+)MB ]]; then
                        mem["$current_step"]="${BASH_REMATCH[1]}"
                    fi
                    if [[ "$line" =~ "Disk Read:"\ ([0-9]+)MB ]]; then
                        disk_read["$current_step"]="${BASH_REMATCH[1]}"
                    fi
                    if [[ "$line" =~ "Disk Write:"\ ([0-9]+)MB ]]; then
                        disk_write["$current_step"]="${BASH_REMATCH[1]}"
                    fi
                    if [[ "$line" =~ util=([0-9]+)% ]]; then
                        disk_util["$current_step"]="${BASH_REMATCH[1]}"
                    fi
                    if [[ "$line" =~ await=([0-9]+)ms ]]; then
                        await["$current_step"]="${BASH_REMATCH[1]}"
                    fi
                    if [[ "$line" =~ queue=([0-9.]+) ]]; then
                        queue["$current_step"]="${BASH_REMATCH[1]}"
                    fi
                fi
            done < "$LOG"

            # Build JSON array (sorted by start time)
            echo -n "["
            first=true
            for step in $(for s in "${!starts[@]}"; do echo "${starts[$s]}|$s"; done | sort | cut -d"|" -f2); do
                [[ "$first" == "true" ]] || echo -n ","
                first=false
                start="${starts[$step]}"
                end="${ends[$step]:-}"
                status="in_progress"
                [[ -n "$end" ]] && status="completed"
                echo -n "{\"name\":\"$step\",\"status\":\"$status\""
                echo -n ",\"started_at\":\"$start\""
                [[ -n "$end" ]] && echo -n ",\"completed_at\":\"$end\""
                [[ -n "${cpu[$step]}" ]] && echo -n ",\"cpu_percent\":${cpu[$step]}"
                [[ -n "${mem[$step]}" ]] && echo -n ",\"memory_mb\":${mem[$step]}"
                [[ -n "${disk_read[$step]}" ]] && echo -n ",\"disk_read_mb\":${disk_read[$step]}"
                [[ -n "${disk_write[$step]}" ]] && echo -n ",\"disk_write_mb\":${disk_write[$step]}"
                [[ -n "${disk_util[$step]}" ]] && echo -n ",\"disk_util_percent\":${disk_util[$step]}"
                [[ -n "${await[$step]}" ]] && echo -n ",\"await_ms\":${await[$step]}"
                [[ -n "${queue[$step]}" ]] && echo -n ",\"queue_depth\":${queue[$step]}"
                echo -n "}"
            done
            echo "]"
        ' 2>/dev/null || echo '[]')
    fi

    # Combine status, logs, metrics and packer steps
    local packer_steps_json="${packer_steps:-[]}"
    echo "$status_json" | jq --arg rid "$id" --argjson logs "$logs_array" --argjson metrics "$metrics_json" --argjson packer_steps "$packer_steps_json" '{
        run_id: $rid,
        job: "Build Appliance",
        version: .headBranch,
        status: .status,
        conclusion: .conclusion,
        started_at: .createdAt,
        updated_at: (now | todate),
        url: .url,
        logs: $logs,
        metrics: $metrics,
        packer_steps: $packer_steps,
        steps: [.jobs[] | select(.name=="Build Appliance") | .steps[] | {
            name: .name,
            status: .status,
            conclusion: .conclusion,
            started_at: .startedAt,
            completed_at: .completedAt
        }]
    }' > "$OUTPUT_FILE" 2>/dev/null || echo '{"error": "Failed to fetch"}' > "$OUTPUT_FILE"
}

while true; do
    update_status
    status=$(jq -r '.status // "error"' "$OUTPUT_FILE" 2>/dev/null)
    step=$(jq -r '.steps[] | select(.status=="in_progress") | .name' "$OUTPUT_FILE" 2>/dev/null | head -1)

    echo "[$(date '+%H:%M:%S')] Status: $status | Step: ${step:-waiting}"

    if [[ "$status" == "completed" ]]; then
        conclusion=$(jq -r '.conclusion' "$OUTPUT_FILE")
        echo ""
        echo "Build finished: $conclusion"
        # One final update
        update_status
        break
    fi

    sleep "$INTERVAL"
done
