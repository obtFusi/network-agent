#!/bin/bash
# 99-cleanup.sh - Clean up and shrink image
set -euo pipefail

echo "=== Cleaning up for smaller image ==="

# Clean apt cache
apt-get clean
apt-get autoremove -y
rm -rf /var/lib/apt/lists/*

# Clear logs
find /var/log -type f -name "*.log" -delete
find /var/log -type f -name "*.gz" -delete
journalctl --vacuum-time=1d

# Clear temp files
rm -rf /tmp/*
rm -rf /var/tmp/*

# Clear bash history
history -c
rm -f /root/.bash_history
rm -f /home/*/.bash_history 2>/dev/null || true

# Clear SSH host keys (will be regenerated on first boot)
rm -f /etc/ssh/ssh_host_*

# Create first-boot script to regenerate SSH keys
cat > /etc/systemd/system/regenerate-ssh-keys.service << 'EOF'
[Unit]
Description=Regenerate SSH host keys on first boot
Before=ssh.service
ConditionPathExists=!/etc/ssh/ssh_host_ed25519_key

[Service]
Type=oneshot
ExecStart=/usr/sbin/dpkg-reconfigure openssh-server
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

systemctl enable regenerate-ssh-keys.service

# Zero out free space for better compression (optional, takes time)
# Uncomment for smaller OVA files:
# dd if=/dev/zero of=/zero.fill bs=1M 2>/dev/null || true
# rm -f /zero.fill

# Final sync
sync

echo "=== Cleanup complete ==="
echo "Image is ready for export"
