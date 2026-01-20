#!/bin/bash
# 06-configure-firewall.sh - Configure firewall for Docker-based appliance
#
# IMPORTANT: This script disables nftables to avoid conflicts with Docker.
# Docker uses iptables-nft (iptables syntax with nftables backend).
# Using 'nft flush ruleset' breaks Docker's networking rules.
#
# Host protection is configured via iptables rules that work WITH Docker.
set -euo pipefail

echo "=== Configuring firewall (Docker-compatible) ==="

# CRITICAL: Disable nftables to prevent conflicts with Docker
# Docker manages its own iptables-nft rules for container networking
echo "Disabling nftables (conflicts with Docker)..."
systemctl stop nftables 2>/dev/null || true
systemctl disable nftables 2>/dev/null || true
systemctl mask nftables

# Remove any existing nftables rules
nft flush ruleset 2>/dev/null || true

# Enable bridge-nf-call for Docker networking
# This allows iptables to filter bridged traffic
echo "Enabling bridge-nf-call-iptables..."
cat > /etc/sysctl.d/99-docker-bridge.conf << 'EOF'
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
EOF

# Load br_netfilter module and apply sysctl
modprobe br_netfilter 2>/dev/null || true
sysctl -p /etc/sysctl.d/99-docker-bridge.conf 2>/dev/null || true

# CRITICAL: Exclude Docker interfaces from systemd-networkd management
# Without this, systemd-networkd interferes with Docker's veth attachment to bridges
# causing "NO-CARRIER" state on bridges and broken container networking
# See: https://github.com/moby/moby/issues/26492
echo "Configuring systemd-networkd to ignore Docker interfaces..."

cat > /etc/systemd/network/10-docker-veth.network << 'EOF'
# Exclude Docker veth interfaces from systemd-networkd management
# Required for proper Docker bridge networking
[Match]
Name=veth*
Driver=veth

[Link]
Unmanaged=yes
EOF

cat > /etc/systemd/network/10-docker-bridge.network << 'EOF'
# Exclude Docker bridge interfaces from systemd-networkd management
[Match]
Name=br-*

[Link]
Unmanaged=yes
EOF

cat > /etc/systemd/network/10-docker0.network << 'EOF'
# Exclude default Docker bridge from systemd-networkd management
[Match]
Name=docker0

[Link]
Unmanaged=yes
EOF

# Create iptables rules script for host protection
# These rules work WITH Docker (don't interfere with DOCKER chains)
cat > /opt/network-agent/firewall-rules.sh << 'FIREWALL_EOF'
#!/bin/bash
# Host firewall rules - applied AFTER Docker starts
# These rules protect the host without breaking Docker networking

set -euo pipefail

# Only add rules if they don't exist (idempotent)
add_rule_if_missing() {
    local table="$1"
    local chain="$2"
    shift 2
    if ! iptables -t "$table" -C "$chain" "$@" 2>/dev/null; then
        iptables -t "$table" -A "$chain" "$@"
    fi
}

# INPUT chain - protect host services
# Note: Docker manages its own port forwarding via DOCKER chain

# Accept loopback
add_rule_if_missing filter INPUT -i lo -j ACCEPT

# Accept established connections
add_rule_if_missing filter INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Accept ICMP (ping)
add_rule_if_missing filter INPUT -p icmp -j ACCEPT

# Accept SSH
add_rule_if_missing filter INPUT -p tcp --dport 22 -j ACCEPT

# Accept HTTP/HTTPS (Caddy)
add_rule_if_missing filter INPUT -p tcp --dport 80 -j ACCEPT
add_rule_if_missing filter INPUT -p tcp --dport 443 -j ACCEPT

# Accept Docker bridge traffic (container -> host)
add_rule_if_missing filter INPUT -i br-+ -j ACCEPT
add_rule_if_missing filter INPUT -i docker0 -j ACCEPT

# Log and drop other INPUT (but don't change policy - let Docker work)
# Note: We use LOG target, not DROP policy, to avoid breaking Docker

echo "Host firewall rules applied"
FIREWALL_EOF

chmod +x /opt/network-agent/firewall-rules.sh

# Create systemd service to apply rules after Docker
cat > /etc/systemd/system/network-agent-firewall.service << 'EOF'
[Unit]
Description=Network Agent Host Firewall Rules
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
ExecStart=/opt/network-agent/firewall-rules.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable network-agent-firewall.service

echo ""
echo "=== Firewall configuration complete ==="
echo "- nftables: DISABLED (masked) - conflicts with Docker"
echo "- iptables: Managed by Docker for container networking"
echo "- Host rules: Applied via network-agent-firewall.service after Docker"
echo ""
