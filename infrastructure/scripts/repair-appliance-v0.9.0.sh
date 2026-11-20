#!/usr/bin/env bash
set -euo pipefail
umask 077

if [[ $EUID != 0 ]]; then
    echo "Run from an independent root management console." >&2
    exit 1
fi
if [[ ! -f /var/lib/network-agent/.initialized || ! -s /opt/network-agent/.env ]]; then
    echo "The appliance has no complete existing initialization. Stop and inspect it from the management console." >&2
    exit 1
fi

# Accept the original v0.9.0 files or a machine already repaired. An operator
# must review custom files before removing or replacing them.
packer=/etc/ssh/sshd_config.d/00-packer.conf
autologin=/etc/systemd/system/getty@tty1.service.d/override.conf
if [[ -e "$packer" || -L "$packer" ]]; then
    if [[ -L "$packer" ]] || ! cmp -s "$packer" <(printf '%s\n' 'PermitRootLogin yes' 'PasswordAuthentication yes'); then
        echo "The Packer SSH drop-in has local changes. Review it at the console." >&2
        exit 1
    fi
fi
if [[ -e "$autologin" || -L "$autologin" ]]; then
    if [[ -L "$autologin" ]] || ! cmp -s "$autologin" <(cat <<'EOF'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin root --noclear %I $TERM
EOF
    ); then
        echo "The console drop-in has local changes. Review it at the console." >&2
        exit 1
    fi
fi

backup=$(mktemp -d /etc/.network-agent-repair.XXXXXXXX)
restore_on_failure() {
    local failure=$?
    trap - EXIT HUP INT TERM
    if (( failure != 0 )); then
        if [[ -f "$backup/packer" ]]; then
            mv -- "$backup/packer" "$packer" || true
        fi
        if [[ -f "$backup/autologin" ]]; then
            mv -- "$backup/autologin" "$autologin" || true
        fi
        systemctl daemon-reload || true
        if systemctl is-active --quiet ssh.service; then
            systemctl reload ssh.service || true
        fi
        echo "Repair failed. Keep the console open and check the configuration and $backup." >&2
    fi
    rmdir -- "$backup" 2>/dev/null || true
    exit "$failure"
}
trap restore_on_failure EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

if [[ -f "$packer" ]]; then
    mv -- "$packer" "$backup/packer"
fi
if [[ -f "$autologin" ]]; then
    mv -- "$autologin" "$backup/autologin"
fi
/usr/sbin/sshd -t
effective=$(/usr/sbin/sshd -T)
grep -Fxq 'passwordauthentication no' <<<"$effective"
grep -Eq '^permitrootlogin (no|prohibit-password|without-password)$' <<<"$effective"
systemctl daemon-reload
getty=$(systemctl show getty@tty1.service --property=ExecStart --value)
if [[ -z "$getty" || "$getty" == *--autologin* ]]; then
    echo "TTY1 still has no verified interactive login configuration." >&2
    exit 1
fi
if systemctl is-active --quiet ssh.service; then
    systemctl reload ssh.service
fi

rm -f -- "$backup/packer" "$backup/autologin"
echo "SSH and future console logins are hardened. Verify the new root password and service health before closing the management console."
