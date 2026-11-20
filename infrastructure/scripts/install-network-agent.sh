#!/bin/bash
# install-network-agent.sh - One-Click Installer for Proxmox
# Downloads, verifies, and creates a Network Agent VM
#
# Usage: curl -sSL https://get.network-agent.dev | bash -s -- <VMID> [STORAGE]
# Or:    ./install-network-agent.sh <VMID> [STORAGE]

set -euo pipefail

PACKAGED_VERSION=""
VERSION="${VERSION:-$PACKAGED_VERSION}"
VERSION="${VERSION#v}"
VMID="${1:-}"
STORAGE="${2:-local-lvm}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }
info() { echo -e "${BLUE}[i]${NC} $1"; }

# Header
echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║          NETWORK AGENT INSTALLER v${VERSION}                      ║"
echo "║          AI-Powered Network Security Scanner                  ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# 1. Check arguments
if [[ -z "$VMID" ]]; then
    echo "Usage: $0 <VMID> [STORAGE]"
    echo ""
    echo "Arguments:"
    echo "  VMID:    VM ID for the new appliance (e.g., 200)"
    echo "  STORAGE: Proxmox storage name (default: local-lvm)"
    echo ""
    echo "Examples:"
    echo "  $0 200                    # Create VM 200 on local-lvm"
    echo "  $0 200 ceph-pool          # Create VM 200 on ceph-pool"
    echo ""
    echo "Environment Variables:"
    echo "  VERSION: Appliance release to install. Released installers select their own version."
    echo ""
    exit 1
fi
[[ "$VMID" =~ ^[1-9][0-9]*$ ]] || error "Specify a numeric VM ID."
[[ "$STORAGE" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || error "Specify a valid Proxmox storage name."
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[A-Za-z0-9.-]+)?(\+[A-Za-z0-9.-]+)?$ ]] ||
    error "Set VERSION to a published appliance version or use the installer from that release."
[[ "$VERSION" != "0.9.0" ]] || error "Appliance v0.9.0 was withdrawn. Select a supported release."
BASE_URL="https://github.com/obtFusi/network-agent/releases/download/v${VERSION}"

# 2. Check Proxmox
info "Checking Proxmox environment..."
if ! command -v pveversion &> /dev/null; then
    error "Proxmox VE not found. This script must run on a Proxmox host."
fi
PVE_VERSION=$(pveversion | head -1)
log "Detected: $PVE_VERSION"

# 3. Check if VMID is available
if qm status "$VMID" &>/dev/null; then
    error "VM $VMID already exists! Choose a different ID or remove existing VM."
fi
log "VMID $VMID is available"

# 4. Check storage
info "Checking storage '$STORAGE'..."
if ! pvesm status -storage "$STORAGE" &>/dev/null; then
    error "Storage '$STORAGE' not found. Available storages:"
    pvesm status
    exit 1
fi

# Check free space (need ~50GB)
REQUIRED_GB=50
FREE_KIB=$(pvesm status -storage "$STORAGE" 2>/dev/null | awk 'NR==2 {print $6}')
FREE_GB=$((FREE_KIB / 1024 / 1024))

if [[ "$FREE_GB" -lt "$REQUIRED_GB" ]]; then
    error "Not enough space on $STORAGE (${FREE_GB}GB free, ${REQUIRED_GB}GB required)"
fi
log "${FREE_GB}GB available on $STORAGE"

# 5. Check required tools
for tool in curl zstd sha256sum jq; do
    if ! command -v "$tool" &>/dev/null; then
        warn "Installing missing tool: $tool"
        apt-get update -qq && apt-get install -y -qq "$tool"
    fi
done
command -v qemu-img >/dev/null || error "qemu-img is required to check the downloaded appliance."

# 6. Create temp directory
# Use TMPDIR env var if set, otherwise /var/tmp (not /tmp which is often tmpfs)
TEMP_BASE="${TMPDIR:-/var/tmp}"
workdir=$(mktemp -d -p "$TEMP_BASE" network-agent-XXXXXX)
trap 'rm -rf -- "$workdir"' EXIT
cd -- "$workdir"
info "Working directory: $workdir"

# Check temp directory has enough space
# Peak requirement: ~27GB parts + ~50GB decompressed = ~77GB
REQUIRED_TEMP_GB=78
TMPDIR_FREE=$(df -BG "$workdir" | awk 'NR==2 {gsub(/G/,"",$4); print $4}')
if [[ "$TMPDIR_FREE" -lt "$REQUIRED_TEMP_GB" ]]; then
    error "Not enough temp space: ${TMPDIR_FREE}GB available, ${REQUIRED_TEMP_GB}GB required.

The appliance image requires ~80GB of temporary space for:
  - Compressed parts: ~27GB
  - Decompressed image: ~50GB

Please either:
  1. Free up space on the root filesystem
  2. Or specify a different temp location by setting TMPDIR environment variable:
     TMPDIR=/path/to/large/storage $0 $VMID $STORAGE"
fi
log "${TMPDIR_FREE}GB available for temporary files"

# 7. Download image parts
echo ""
info "Downloading Network Agent v${VERSION}..."
echo "    Source: $BASE_URL"
echo ""

# Download SHA256SUMS first
if ! curl --proto '=https' --proto-redir '=https' -# -fL -o "SHA256SUMS" "$BASE_URL/SHA256SUMS"; then
    error "Failed to download SHA256SUMS. Check if version v${VERSION} exists."
fi

# Validate all manifest entries before using any file name.
declare -A manifest_parts=()
part_prefix="network-agent-${VERSION}.qcow2.zst.part-"
while read -r checksum file extra || [[ -n "$checksum$file$extra" ]]; do
    file="${file#\*}"
    suffix="${file#"$part_prefix"}"
    if [[ ! "$checksum" =~ ^[0-9a-fA-F]{64}$ || -n "$extra" ||
          "$file" != "$part_prefix"* || ! "$suffix" =~ ^[a-z]{2}$ ]]; then
        error "Invalid appliance checksum manifest."
    fi
    [[ ! -v 'manifest_parts[$suffix]' ]] || error "Duplicate appliance part in checksum manifest."
    manifest_parts["$suffix"]="$file"
done < SHA256SUMS
part_count=${#manifest_parts[@]}
(( part_count > 0 )) || error "No appliance parts listed in checksum manifest."
parts=()
alphabet=abcdefghijklmnopqrstuvwxyz
for (( index=0; index<part_count; index++ )); do
    suffix="${alphabet:index/26:1}${alphabet:index%26:1}"
    [[ -v 'manifest_parts[$suffix]' ]] || error "Missing appliance part in checksum manifest."
    parts+=("${manifest_parts[$suffix]}")
done

if command -v aria2c >/dev/null; then
    log "Downloading $part_count parts with aria2c (parallel)..."
    for file in "${parts[@]}"; do
        printf '%s\n  out=%s\n' "$BASE_URL/$file" "$file"
    done > aria2-input.txt
    aria2c -x 16 -s 16 -j 4 --console-log-level=warn --summary-interval=10 \
        --file-allocation=none -i aria2-input.txt || error "Download failed. Check the network and retry."
else
    log "Downloading $part_count parts with curl..."
    for file in "${parts[@]}"; do
        curl --proto '=https' --proto-redir '=https' -# -fL -o "$file" "$BASE_URL/$file" ||
            error "Download failed: $file"
    done
fi

# 8. Verify checksums
echo ""
info "Verifying checksums..."
if sha256sum -c SHA256SUMS --strict --quiet 2>/dev/null; then
    log "All checksums verified"
else
    error "Checksum verification failed! Download may be corrupted."
fi

# 9. Reassemble and decompress (streaming to save disk space)
echo ""
info "Reassembling and decompressing image..."
echo "    This may take a few minutes for the 50GB image..."
echo "    Using streaming decompression to minimize disk usage..."

# Stream decompress: parts -> zstd -> qcow2 (no intermediate file)
# This saves ~27GB disk space compared to creating .zst first
if cat -- "${parts[@]}" | zstd -d -o network-agent.qcow2; then
    FINAL_SIZE=$(du -h network-agent.qcow2 | cut -f1)
    log "Decompressed: $FINAL_SIZE"
    # Remove parts after successful decompression
    rm -f -- "${parts[@]}"
else
    error "Decompression failed"
fi
if ! image_info=$(qemu-img info -f qcow2 --output=json network-agent.qcow2) ||
    ! jq -e '.format == "qcow2" and .["virtual-size"] > 0 and
             .["backing-filename"] == null and .["full-backing-filename"] == null and
             .["format-specific"].data["data-file"] == null' >/dev/null <<< "$image_info" ||
    ! qemu-img check -q -f qcow2 network-agent.qcow2; then
    error "The downloaded appliance is not a self-contained, valid QCOW2 image."
fi

# 10. Create VM
echo ""
info "Creating VM $VMID..."

qm create "$VMID" \
    --name "network-agent" \
    --description "Network Agent Appliance v${VERSION} - AI-Powered Security Scanner" \
    --memory 32768 \
    --cores 8 \
    --cpu host \
    --ostype l26 \
    --agent enabled=1 \
    --net0 virtio,bridge=vmbr0 \
    --onboot 0 \
    --tablet 0

log "VM $VMID created"

# 11. Import disk
info "Importing disk to $STORAGE..."
echo "    This may take a few minutes..."

if ! IMPORT_OUTPUT=$(qm importdisk "$VMID" network-agent.qcow2 "$STORAGE" --format qcow2 2>&1); then
    error "Disk import failed: $IMPORT_OUTPUT"
fi
log "Disk imported to $STORAGE"

# 12. Configure VM
info "Configuring VM..."

# Find the imported disk
DISK_NAME=$(pvesm list "$STORAGE" 2>/dev/null | grep "vm-${VMID}-disk" | awk '{print $1}' | head -1)
if [[ -z "$DISK_NAME" ]]; then
    error "Could not find imported disk"
fi

qm set "$VMID" \
    --scsi0 "$DISK_NAME" \
    --boot order=scsi0 \
    --scsihw virtio-scsi-single

log "VM configured with disk: $DISK_NAME"

# 13. Done!
echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                    INSTALLATION COMPLETE!                     ║"
echo "╠═══════════════════════════════════════════════════════════════╣"
echo "║                                                               ║"
printf "║  %-60s ║\n" "VM ID:    $VMID"
printf "║  %-60s ║\n" "Name:     network-agent"
printf "║  %-60s ║\n" "Memory:   32 GB"
printf "║  %-60s ║\n" "CPUs:     8 cores"
printf "║  %-60s ║\n" "Storage:  $STORAGE"
echo "║                                                               ║"
echo "╠═══════════════════════════════════════════════════════════════╣"
echo "║  NEXT STEPS:                                                  ║"
echo "║                                                               ║"
printf "║  1. Start the VM:     %-40s ║\n" "qm start $VMID"
printf "║  2. Open console:     %-40s ║\n" "qm terminal $VMID"
echo "║  3. Complete first-boot setup:                                ║"
echo "║     - Set new root password                                   ║"
echo "║     - Save generated web credentials                          ║"
echo "║                                                               ║"
echo "║  The VM will display web interface credentials after setup.   ║"
echo "║                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Optional: Ask to start VM
REPLY=""
read -p "Start VM $VMID now? [y/N] " -n 1 -r || true
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    info "Starting VM $VMID..."
    qm start "$VMID"
    log "VM started. Connect with: qm terminal $VMID"
fi
