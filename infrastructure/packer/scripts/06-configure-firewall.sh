#!/bin/bash
# 06-configure-firewall.sh - Configure nftables firewall (Offline-First)
set -euo pipefail

echo "=== Configuring firewall (Offline-First mode) ==="

# Create nftables configuration
# SECURITY: Default DENY outbound for offline operation
cat > /etc/nftables.conf << 'EOF'
#!/usr/sbin/nft -f

flush ruleset

table inet filter {
    chain input {
        type filter hook input priority 0; policy drop;

        # Accept loopback
        iif lo accept

        # Accept established/related connections
        ct state established,related accept

        # Accept ICMP (ping)
        ip protocol icmp accept
        ip6 nexthdr icmpv6 accept

        # Accept DHCP responses (server -> client)
        udp sport 67 udp dport 68 accept

        # Accept SSH (port 22) for management
        tcp dport 22 accept

        # Accept HTTPS (port 443) - Caddy reverse proxy
        tcp dport 443 accept

        # Accept HTTP (port 80) - redirect to HTTPS
        tcp dport 80 accept

        # Drop everything else with logging
        counter log prefix "nftables-drop: " drop
    }

    chain forward {
        type filter hook forward priority 0; policy drop;

        # Accept established/related connections
        ct state established,related accept

        # Accept Docker bridge network forwarding
        iifname "docker*" oifname "docker*" accept
        iifname "br-*" oifname "br-*" accept

        # Docker to host and back
        iifname "docker*" accept
        oifname "docker*" accept
    }

    chain output {
        type filter hook output priority 0; policy drop;

        # Accept loopback
        oif lo accept

        # Accept established/related connections
        ct state established,related accept

        # Accept Docker internal traffic
        oifname "docker*" accept
        oifname "br-*" accept

        # DHCP requests (client -> server) - required for IP assignment
        udp sport 68 udp dport 67 accept

        # DNS only to local resolvers (not external!)
        udp dport 53 ip daddr { 127.0.0.1, 127.0.0.53, 172.20.0.0/16 } accept

        # OFFLINE-FIRST: Block ALL other outbound traffic
        # Uncomment lines below to enable internet access:
        # tcp dport { 80, 443 } accept  # HTTP/HTTPS
        # udp dport 53 accept           # External DNS

        # Log and drop everything else
        counter log prefix "nftables-outbound-blocked: " drop
    }
}
EOF

# Enable and start nftables
systemctl enable nftables
systemctl start nftables

# Verify firewall rules
echo ""
echo "=== Firewall rules (Offline-First) ==="
nft list ruleset

echo ""
echo "NOTE: Outbound traffic is blocked by default (Offline-First)."
echo "To enable internet access, edit /etc/nftables.conf and restart nftables."
echo ""

echo "=== Firewall configuration complete ==="
