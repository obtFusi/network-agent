# Build Telemetry System

**Purpose:** Bottleneck analysis and optimization of appliance builds through detailed resource monitoring.

---

## Overview

The telemetry system tracks resource usage during CI/CD builds to identify bottlenecks and enable optimization. Data is captured in real-time during builds and stored persistently in MinIO for historical analysis and comparison.

**Data Flow:**
```
GitHub Actions Steps → telemetry.sh → JSON → MinIO
Packer VM Steps → packer-telemetry.sh → Log Output (real-time)
```

---

## Scripts

| Script | Runs Where | Purpose |
|--------|------------|---------|
| `infrastructure/scripts/telemetry.sh` | GitHub Actions Runner | Tracks GitHub Actions workflow steps |
| `infrastructure/packer/scripts/packer-telemetry.sh` | Inside Packer VM | Tracks Packer provisioner steps |
| `infrastructure/scripts/telemetry-report.sh` | Local machine | Report tool for stored telemetry |

---

## Captured Metrics

### Per-Step Metrics

| Metric | Description | Data Source | Bottleneck Indicator |
|--------|-------------|-------------|---------------------|
| `duration_s` | Step duration in seconds | Wall clock | >60s = long step |
| `cpu_percent` | Average CPU utilization | `/proc/stat` | >80% = CPU-bound |
| `memory_used_mb` | RAM consumption | `/proc/meminfo` | >8GB = memory-intensive |
| `disk_read_mb` | Bytes read from disk | `/proc/diskstats` | - |
| `disk_write_mb` | Bytes written to disk | `/proc/diskstats` | >1GB = I/O-intensive |
| `disk_read_ops` | Number of read operations | `/proc/diskstats` | - |
| `disk_write_ops` | Number of write operations | `/proc/diskstats` | - |
| `disk_read_rate_mbs` | Read throughput (MB/s) | Calculated | - |
| `disk_write_rate_mbs` | Write throughput (MB/s) | Calculated | - |
| `disk_util_percent` | Disk utilization (io_time/elapsed) | `/proc/diskstats` field 13 | >80% = disk saturated |
| `await_ms` | Average I/O wait time per operation | `/proc/diskstats` fields 7,11 | >10ms = slow disk |
| `queue_depth` | Average I/O queue depth | `/proc/diskstats` field 14 | >4 = I/O congestion |
| `net_rx_mb` | Network bytes received | `/proc/net/dev` | >500MB = download-heavy |
| `net_tx_mb` | Network bytes transmitted | `/proc/net/dev` | - |
| `net_rx_rate_mbs` | Download throughput (MB/s) | Calculated | - |
| `net_tx_rate_mbs` | Upload throughput (MB/s) | Calculated | - |

### System Metrics (once per job)

| Metric | Description |
|--------|-------------|
| `cpus` | Number of CPU cores |
| `memory_total_mb` | Total system RAM |
| `disk_total_gb` | Total disk space |

---

## Data Sources (Linux /proc filesystem)

### CPU (`/proc/stat`)
```
cpu  user nice system idle iowait irq softirq steal guest guest_nice
```
- We track `idle` ticks between start and end
- CPU usage = 100 - (idle_delta / duration)

### Memory (`/proc/meminfo`)
```
MemTotal:       32000000 kB
MemAvailable:   24000000 kB
```
- `used_mb` = (MemTotal - MemAvailable) / 1024

### Disk (`/proc/diskstats`)
```
Fields: major minor name reads_completed reads_merged sectors_read read_time_ms
        writes_completed writes_merged sectors_written write_time_ms
        ios_in_progress io_time_ms weighted_io_time_ms
```
- Bytes = sectors * 512
- `disk_util_percent` = (io_time_delta_ms / duration_ms) * 100
- `await_ms` = (read_time + write_time) / (reads + writes)
- `queue_depth` = weighted_io_time_ms / duration_ms

### Network (`/proc/net/dev`)
```
Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets
 eth0: 12345678  123456    0    0    0     0          0         0 87654321   65432
```
- Track `rx_bytes` and `tx_bytes` deltas

---

## Telemetry Workflow

### 1. Initialization
```bash
source telemetry.sh
telemetry_init "build" "0.10.2"
```
- Creates JSON file with job metadata
- Records system specs

### 2. Step Tracking
```bash
telemetry_step_start "packer_build"
# ... actual work happens here ...
# Metrics are output in real-time to the log
telemetry_step_end "packer_build"
```
- Start: Saves baseline metrics to temp files
- End: Calculates deltas, outputs to console, appends to JSON

### 3. Finalization
```bash
telemetry_finalize
```
- Calculates total job duration
- Outputs summary table
- JSON file is complete and ready for upload

---

## Real-Time Output Format

During builds, telemetry appears in GitHub Actions logs:

```
═══════════════════════════════════════════════════════════════════════
⏱️  [packer_build] START: 2026-01-24T12:00:00+00:00
───────────────────────────────────────────────────────────────────────
... step output ...
───────────────────────────────────────────────────────────────────────
⏱️  [packer_build] END: 2026-01-24T12:35:00+00:00

  Duration:      2100.5s
  CPU:           ~45% avg
  Memory:        4200MB used (delta 1500MB)
  Disk Read:     150MB (4MB/s, 12000 ops)
  Disk Write:    25600MB (12MB/s, 89000 ops)
  Disk I/O:      util=65%, await=3ms, queue=1.2
  Net RX:        890MB (0MB/s)
  Net TX:        5MB (0MB/s)
═══════════════════════════════════════════════════════════════════════
```

---

## MinIO Storage Structure

```
minio/appliance-telemetry/
├── latest/
│   ├── build_0.10.2.json      # Most recent build telemetry
│   └── e2e_0.10.2.json        # Most recent E2E test telemetry
└── 0.10.2/
    └── 20260124_120000/       # Timestamp-based directory
        ├── build_20260124_120000.json
        ├── packer_steps.txt   # Packer internal telemetry (grep'd from logs)
        └── step_*             # Temp files (intermediate state)
```

### JSON Schema

```json
{
  "job": "build",
  "version": "0.10.2",
  "timestamp": "2026-01-24T12:00:00+00:00",
  "runner": "github-runner",
  "git_sha": "abc123...",
  "git_ref": "refs/heads/main",
  "run_id": "12345678",
  "run_number": "42",
  "job_start": 1769257179.067,
  "job_end": 1769259279.123,
  "job_duration_s": 2100.056,
  "steps": [
    {
      "name": "packer_build",
      "start_time": 1769257200.000,
      "end_time": 1769259200.000,
      "duration_s": 2000.0,
      "cpu_percent": 45,
      "memory_used_mb": 4200,
      "memory_delta_mb": 1500,
      "disk_read_mb": 150,
      "disk_write_mb": 25600,
      "disk_read_ops": 12000,
      "disk_write_ops": 89000,
      "disk_read_rate_mbs": 4,
      "disk_write_rate_mbs": 12,
      "disk_util_percent": 65,
      "await_ms": 3,
      "queue_depth": 1.2,
      "net_rx_mb": 890,
      "net_tx_mb": 5,
      "net_rx_rate_mbs": 0,
      "net_tx_rate_mbs": 0
    }
  ],
  "system": {
    "cpus": 4,
    "memory_total_mb": 32000,
    "disk_total_gb": 120
  }
}
```

---

## Report Tool Usage

### Show Latest Build Telemetry
```bash
./infrastructure/scripts/telemetry-report.sh latest
```
Displays:
- Job metadata (version, timestamp, runner)
- Step-by-step breakdown with all metrics
- Bottleneck analysis (slowest step, highest I/O, etc.)

### Show Latest E2E Test Telemetry
```bash
./infrastructure/scripts/telemetry-report.sh latest e2e
```

### List All Available Telemetry
```bash
./infrastructure/scripts/telemetry-report.sh list
```

### Compare Two Versions
```bash
./infrastructure/scripts/telemetry-report.sh compare 0.10.1 0.10.2
```
Shows side-by-side comparison of:
- Total duration
- Per-step duration differences

### Show Build History
```bash
./infrastructure/scripts/telemetry-report.sh history 5
```
Lists last N builds with version, timestamp, and duration.

---

## Bottleneck Diagnosis Guide

| Symptom | Root Cause | Solution |
|---------|------------|----------|
| `disk_util=100%` | Disk fully saturated | Reduce parallel I/O, use faster SSD |
| `await>20ms` | Slow disk or excessive queueing | Enable caching, reduce concurrent operations |
| `queue>8` | I/O congestion, too many parallel ops | Write sequentially instead of parallel |
| High `net_rx_mb` | Many downloads during build | Implement local caching (like Ollama cache) |
| `cpu=100%` + long `duration` | CPU-bound operation | Parallelize or use faster CPU |
| High `memory_delta_mb` | Memory-intensive step | Increase RAM or optimize memory usage |
| Low throughput (`*_rate_mbs`) | Bottleneck elsewhere | Check if CPU or network is limiting |

### Common Optimization Patterns

1. **Ollama Model Download** (~15GB)
   - Problem: High `net_rx_mb`, long duration
   - Solution: Cache models on runner, restore from tarball

2. **Docker Layer Build**
   - Problem: High `disk_write_mb`, sequential layers
   - Solution: Multi-stage builds, layer caching

3. **Package Installation** (apt-get)
   - Problem: High `net_rx_mb` + `disk_write_mb`
   - Solution: Use package mirrors, cache apt lists

4. **qcow2 Compression**
   - Problem: High `cpu_percent`, long duration
   - Solution: Use zstd instead of gzip, balance compression level

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEMETRY_DIR` | `/tmp/telemetry` | Directory for telemetry files |
| `TELEMETRY_BUCKET` | `appliance-telemetry` | MinIO bucket name |
| `MINIO_ENDPOINT` | `http://10.0.0.165:9000` | MinIO server URL |
| `MINIO_ACCESS_KEY` | (from secrets) | MinIO access credentials |
| `MINIO_SECRET_KEY` | (from secrets) | MinIO secret credentials |

---

## Extending Telemetry

### Adding New Metrics

1. Add data collection in `telemetry_step_start()`:
   ```bash
   get_new_metric > "${STEP_FILE}_start_newmetric"
   ```

2. Calculate delta in `telemetry_step_end()`:
   ```bash
   local NEW_START=$(cat "${STEP_FILE}_start_newmetric")
   local NEW_END=$(get_new_metric)
   local NEW_DELTA=$((NEW_END - NEW_START))
   ```

3. Add to console output:
   ```bash
   printf '  %-14s %s\n' 'New Metric:' "$NEW_DELTA"
   ```

4. Add to JSON:
   ```bash
   "new_metric": $NEW_DELTA,
   ```

### Adding New Steps

Simply wrap your code with start/end calls:
```bash
telemetry_step_start "my_new_step"
# ... your code ...
telemetry_step_end "my_new_step"
```

---

## Troubleshooting

### Telemetry Not Appearing
- Check if `telemetry.sh` is sourced before use
- Verify `TELEMETRY_DIR` exists and is writable
- Check for bash vs dash issues (`inline_shebang = "/bin/bash -e"`)

### Missing Disk Metrics
- Ensure device name matches pattern: `vda|sda|nvme0n1`
- Check if `/proc/diskstats` is accessible

### MinIO Upload Fails
- Verify MinIO credentials in GitHub secrets
- Check MinIO container status: `systemctl status minio`
- Test connectivity: `mc ls minio/`

### Zero Values for Metrics
- Duration too short (< 1 second)
- No I/O activity during step
- Device name mismatch in `/proc` patterns
