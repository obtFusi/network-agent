# Appliance build and first boot

Use the build wrapper after `packer init` for the selected template. It creates a fresh provisioning password for each invocation and supplies only the hash to the Debian installer. The image finalizer discards provisioning access before poweroff.

- For a direct QEMU build use `make build VERSION=VERSION` from the infrastructure directory.
- For the reusable base use `./build.sh base-image.pkr.hcl` from the Packer directory. The secure base has a locked root password when stored. Keep the image and its checksum together.
- For the final image on that base use `./build.sh appliance.pkr.hcl /absolute/path/to/secure-base.qcow2 -var "version=VERSION"`. It uses an offline private copy and requires qemu-img, jq, virt-cat and virt-customize. Build a fresh base for this path.

## New appliance

Import a tested release with its own installer and checksum manifest. Open the VM console on first boot and sign in with the initial root password displayed there. Change it with `passwd` and keep the new value in your private credential store. The web login credentials are in `/root/network-agent-credentials.txt` inside the appliance. Password authentication over SSH is disabled.

## An existing v0.9.0 appliance

1. Open the hypervisor console and verify you can recover access there. Take a verified backup of the appliance, its Compose volumes and its configuration. Record the currently running services and one existing application record to check after the repair.
2. Set a new unique root password with `passwd` and verify it at a separate authenticated console prompt, for example on another virtual terminal. Keep the recovery console open. Administrators who use SSH should separately verify their existing key-based access.
3. Download the release's `repair-appliance-v0.9.0.sh` and `SHA256SUMS.scripts`. Verify the script against its entry in the manifest, then copy it into the guest and run it as root from the recovery console. The script removes the original Packer SSH exception and TTY1 autologin override, checks the effective OpenSSH policy and reloads SSH if it is running. It leaves locally customized overrides for the operator to review.
4. Verify the service state and the previously recorded application data. During the agreed restart window reboot the VM, verify an authenticated console login, then check `systemctl is-active network-agent.service`, the service health from `docker compose ps` in `/opt/network-agent`, and the same application data again. Verify the chosen SSH access method in a separate session if you use it.

Keep the initialization marker, application configuration and Compose volumes. The first-boot initializer is reserved for new appliances.
