#!/bin/bash
# create-runner-lxc.sh - Create dedicated LXC for GitHub Actions Runner
#
# Run this script ON THE PROXMOX HOST to create the runner LXC.
#
# Requirements:
#   - Proxmox VE 8.x
#   - Debian 12 LXC template available
#   - ~80GB storage on local-lvm
#
# Usage:
#   ssh root@proxmox ./create-runner-lxc.sh

set -euo pipefail

# Configuration
VMID=150
HOSTNAME="github-runner"
MEMORY=8192  # 8GB
CORES=4
DISK_SIZE=80  # GB
STORAGE="local-lvm"
TEMPLATE="debian-13-standard_13.1-2_amd64.tar.zst"
RUNNER_VERSION="2.321.0"

echo "=== Creating GitHub Actions Runner LXC ==="
echo "VMID: $VMID"
echo "Hostname: $HOSTNAME"
echo "Memory: ${MEMORY}MB"
echo "Cores: $CORES"
echo "Disk: ${DISK_SIZE}GB on $STORAGE"

# Download template if not present
echo "Checking for LXC template..."
if ! pveam list local | grep -q "$TEMPLATE"; then
    echo "Downloading template..."
    pveam update
    pveam download local "$TEMPLATE"
fi

# Check if LXC already exists
if pct status $VMID &>/dev/null; then
    echo "ERROR: LXC $VMID already exists!"
    echo "To recreate, run: pct destroy $VMID --purge"
    exit 1
fi

# Create LXC
echo "Creating LXC container..."
pct create $VMID "local:vztmpl/$TEMPLATE" \
    --hostname "$HOSTNAME" \
    --memory $MEMORY \
    --cores $CORES \
    --rootfs "${STORAGE}:${DISK_SIZE}" \
    --net0 "name=eth0,bridge=vmbr0,ip=dhcp" \
    --features "nesting=1" \
    --onboot 1 \
    --unprivileged 0 \
    --start 0

echo "LXC container created."

# Start container
echo "Starting container..."
pct start $VMID

# Wait for container to be ready
echo "Waiting for container to be ready..."
sleep 10

# Install packages inside container
echo "Installing packages..."
pct exec $VMID -- bash -c '
set -euo pipefail

echo "Updating package lists..."
apt-get update

echo "Installing required packages..."
apt-get install -y \
    curl \
    jq \
    git \
    docker.io \
    qemu-system-x86 \
    qemu-utils \
    ovmf \
    ca-certificates \
    gnupg

echo "Enabling Docker..."
systemctl enable docker
systemctl start docker

echo "Installing Packer..."
curl -fsSL https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" > /etc/apt/sources.list.d/hashicorp.list
apt-get update
apt-get install -y packer
'

# Create runner user
echo "Creating runner user..."
pct exec $VMID -- bash -c '
useradd -m -s /bin/bash runner
usermod -aG docker runner
'

# Download and setup GitHub Actions Runner
echo "Setting up GitHub Actions Runner..."
pct exec $VMID -- bash -c "
set -euo pipefail

mkdir -p /opt/actions-runner
cd /opt/actions-runner

echo 'Downloading runner ${RUNNER_VERSION}...'
curl -o actions-runner.tar.gz -L \
    'https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz'

echo 'Extracting runner...'
tar xzf actions-runner.tar.gz
rm actions-runner.tar.gz

echo 'Installing dependencies...'
./bin/installdependencies.sh

echo 'Setting ownership...'
chown -R runner:runner /opt/actions-runner
"

# Create systemd service for runner wrapper
echo "Creating systemd service..."
pct exec $VMID -- bash -c '
cat > /etc/systemd/system/github-runner.service << EOF
[Unit]
Description=GitHub Actions Runner (Ephemeral)
After=network-online.target docker.service
Wants=network-online.target
Requires=docker.service

[Service]
Type=simple
User=runner
WorkingDirectory=/opt/actions-runner
EnvironmentFile=/opt/actions-runner/.env
ExecStart=/opt/actions-runner/runner-wrapper.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create empty .env file with correct permissions
touch /opt/actions-runner/.env
chown runner:runner /opt/actions-runner/.env
chmod 600 /opt/actions-runner/.env
'

# Get container IP
IP=$(pct exec $VMID -- hostname -I | awk '{print $1}')

echo ""
echo "=== LXC Setup Complete ==="
echo ""
echo "Container ID: $VMID"
echo "Container IP: $IP"
echo ""
echo "Next steps:"
echo ""
echo "1. Copy the runner-wrapper.sh script to the container:"
echo "   pct push $VMID /path/to/runner-wrapper.sh /opt/actions-runner/runner-wrapper.sh"
echo "   pct exec $VMID -- chown runner:runner /opt/actions-runner/runner-wrapper.sh"
echo "   pct exec $VMID -- chmod +x /opt/actions-runner/runner-wrapper.sh"
echo ""
echo "2. Create a GitHub Fine-grained PAT:"
echo "   - Repository: obtFusi/network-agent"
echo "   - Permissions: Administration (Read & Write)"
echo ""
echo "3. Configure the PAT (stored in .env file, not in service):"
echo "   pct exec $VMID -- bash -c 'echo \"GITHUB_PAT=github_pat_xxx\" > /opt/actions-runner/.env'"
echo "   pct exec $VMID -- systemctl daemon-reload"
echo "   pct exec $VMID -- systemctl enable github-runner"
echo "   pct exec $VMID -- systemctl start github-runner"
echo ""
echo "4. Check runner status:"
echo "   pct exec $VMID -- systemctl status github-runner"
echo "   pct exec $VMID -- journalctl -u github-runner -f"
echo ""
echo "The runner will appear at:"
echo "https://github.com/obtFusi/network-agent/settings/actions/runners"
