#!/usr/bin/env bash
set +x
set -euo pipefail
umask 077
cd -- "$(dirname -- "$0")"

usage() {
    echo "Usage: $0 network-agent.pkr.hcl|base.pkr.hcl|base-image.pkr.hcl [Packer arguments]" >&2
    echo "       $0 appliance.pkr.hcl /absolute/path/to/secure-base.qcow2 [Packer arguments]" >&2
    exit 2
}

template=${1:-}
[[ -n "$template" ]] || usage
shift
case "$template" in
    network-agent.pkr.hcl|base.pkr.hcl|base-image.pkr.hcl) ;;
    appliance.pkr.hcl) [[ $# -ge 1 ]] || usage ;;
    *) usage ;;
esac

# Packer emits provisioning output. Detailed logs must not record build credentials.
unset PACKER_LOG PACKER_LOG_PATH
export PKR_VAR_build_root_password
PKR_VAR_build_root_password=$(openssl rand -hex 32)
if [[ "$template" != appliance.pkr.hcl ]]; then
    export PKR_VAR_build_root_hash
    PKR_VAR_build_root_hash=$(printf '%s\n' "$PKR_VAR_build_root_password" | openssl passwd -6 -stdin)
    packer build "$@" "$template"
    exit
fi

base_image=$1
shift
[[ "$base_image" = /* && -f "$base_image" ]] || usage
base_config=$(qemu-img info -f qcow2 --output=json "$base_image")
if ! jq -e '(.format == "qcow2") and (has("backing-filename") | not) and
            (.["format-specific"].data["data-file"] == null)' >/dev/null <<<"$base_config"; then
    echo "Base image must be a standalone qcow2 disk" >&2
    exit 1
fi
if [[ "$(virt-cat --format qcow2 -a "$base_image" /etc/network-agent/build-base-version)" != 2 ]]; then
    echo "Build a new secure base image before building the appliance" >&2
    exit 1
fi

# Provision a private copy. The reusable base must retain its locked root account.
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
printf '%s\n' "$PKR_VAR_build_root_password" > "$scratch/password"
# Override the reusable base's public-key-only policy for this build connection.
printf '%s\n' 'PermitRootLogin yes' 'PasswordAuthentication yes' \
    'AuthenticationMethods password' > "$scratch/00-packer.conf"
qemu-img convert -f qcow2 -O qcow2 "$base_image" "$scratch/base.qcow2"
virt-customize --no-network --format qcow2 -a "$scratch/base.qcow2" \
    --root-password "file:$scratch/password" \
    --upload "$scratch/00-packer.conf:/etc/ssh/sshd_config.d/00-packer.conf"
rm -f -- "$scratch/password" "$scratch/00-packer.conf"
packer build "$@" -var "base_image_url=file://$scratch/base.qcow2" "$template"
