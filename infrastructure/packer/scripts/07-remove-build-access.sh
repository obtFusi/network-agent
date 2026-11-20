#!/usr/bin/env bash
set -euo pipefail

# Run on the existing build connection immediately before powering off the image.
usermod --password '!' root
rm -f /etc/shadow- /etc/ssh/sshd_config.d/00-packer.conf
rm -f /root/.ssh/authorized_keys /root/.ssh/authorized_keys2
rm -f /var/log/installer/cdebconf/passwords.dat

IFS=: read -r _ marker _ < <(getent shadow root)
if [[ "$marker" != '!' ]]; then
    echo "Root build credential was not removed" >&2
    exit 1
fi

mkdir -p /run/sshd
effective_config=$(/usr/sbin/sshd -T)
grep -Fqx 'passwordauthentication no' <<<"$effective_config"
grep -Eq '^permitrootlogin (no|prohibit-password|without-password)$' <<<"$effective_config"
