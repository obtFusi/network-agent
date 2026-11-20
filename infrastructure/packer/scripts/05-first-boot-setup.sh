#!/bin/bash
# 05-first-boot-setup.sh - Configure first-boot initialization
set -euo pipefail

echo "=== Configuring first-boot setup ==="

# Make first-boot script executable
chmod +x /opt/network-agent/first-boot.sh

# Create systemd service for first-boot initialization
cat > /etc/systemd/system/network-agent-first-boot.service << 'EOF'
[Unit]
Description=Network Agent First Boot Setup
Documentation=https://github.com/obtFusi/network-agent
After=network-online.target docker.service
Before=getty@tty1.service
Wants=network-online.target
Requires=docker.service
ConditionPathExists=!/var/lib/network-agent/.initialized

[Service]
Type=oneshot
RemainAfterExit=no
ExecStart=/opt/network-agent/first-boot.sh
StandardInput=null
StandardOutput=tty
StandardError=tty
TTYPath=/dev/tty1
TTYReset=yes
TTYVHangup=yes
TTYVTDisallocate=no

[Install]
WantedBy=multi-user.target
EOF

# Create systemd service for ongoing operation (after first-boot)
cat > /etc/systemd/system/network-agent.service << 'EOF'
[Unit]
Description=Network Agent Appliance
Documentation=https://github.com/obtFusi/network-agent
Requires=docker.service
After=docker.service network-online.target network-agent-first-boot.service
Wants=network-online.target
ConditionPathExists=/var/lib/network-agent/.initialized

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/network-agent
EnvironmentFile=/opt/network-agent/.env
ExecStart=/usr/bin/docker compose up -d --wait
ExecStop=/usr/bin/docker compose down
ExecReload=/usr/bin/docker compose restart
TimeoutStartSec=300
TimeoutStopSec=120

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable services
systemctl daemon-reload
systemctl enable network-agent-first-boot.service
systemctl enable network-agent.service

echo "=== First-boot setup configured ==="

# Create MOTD for appliance
cat > /etc/motd << 'EOF'

╔══════════════════════════════════════════════════════════════════╗
║                    NETWORK AGENT APPLIANCE                       ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  First Boot:                                                     ║
║    The VM console displays a unique one-time setup password.     ║
║    Sign in as root locally and change the password with passwd.  ║
║    Read the web credentials from the root-only credentials file. ║
║                                                                  ║
║  After Setup:                                                    ║
║    Web Interface:  https://<IP>  (credentials from first boot)  ║
║                                                                  ║
║  Commands:                                                       ║
║    systemctl status network-agent   # Check status               ║
║    docker compose logs              # View logs                  ║
║    docker compose restart           # Restart services           ║
║                                                                  ║
║  Documentation: https://github.com/obtFusi/network-agent         ║
╚══════════════════════════════════════════════════════════════════╝

EOF

# Preserve the initial credential prompt on the console until the operator can
# read it. The getty prompts for authentication from its very first invocation.
mkdir -p /etc/systemd/system/getty@tty1.service.d/
cat > /etc/systemd/system/getty@tty1.service.d/90-network-agent-console.conf << 'EOF'
[Service]
TTYVTDisallocate=no
EOF
