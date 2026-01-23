# Network Agent Layer - Packer Template
# Builds on top of base image, adding network-agent specific content
# Fast build (~10 min) for per-release updates
#
# Prerequisites:
#   - Base image from MinIO (appliance-base bucket)
#   - KVM/QEMU with hardware virtualization
#   - Packer >= 1.11.0
#
# Build:
#   # Download base image first
#   mc cp minio/appliance-base/base-2026-01.qcow2 input/
#   packer build -var "version=0.10.1" -var "base_image=input/base-2026-01.qcow2" layer.pkr.hcl

packer {
  required_plugins {
    qemu = {
      version = ">= 1.1.0"
      source  = "github.com/hashicorp/qemu"
    }
  }
}

# Variables
variable "version" {
  type        = string
  description = "Appliance version (e.g., 0.10.1)"
}

variable "base_image" {
  type        = string
  description = "Path to base qcow2 image"
  default     = "input/base.qcow2"
}

variable "disk_size" {
  type        = string
  description = "VM disk size (must match base image)"
  default     = "100G"
}

variable "memory" {
  type        = number
  description = "VM memory in MB (for build only)"
  default     = 16384
}

variable "cpus" {
  type        = number
  description = "Number of CPUs (for build only)"
  default     = 4
}

# Local variables
locals {
  output_name = "network-agent-${var.version}"
}

# QEMU Builder - starts from base image (not ISO)
source "qemu" "layer" {
  # Use existing disk image as base (NOT ISO install)
  disk_image   = true
  iso_url      = var.base_image
  iso_checksum = "none"

  output_directory = "output"
  vm_name          = "${local.output_name}.qcow2"
  format           = "qcow2"
  disk_size        = var.disk_size
  disk_compression = true

  memory = var.memory
  cpus   = var.cpus

  # Modern QEMU settings
  machine_type   = "q35"
  accelerator    = "kvm"
  net_device     = "virtio-net"
  disk_interface = "virtio-scsi"

  # No boot_command needed - boots from disk
  boot_wait    = "30s"
  boot_command = []

  # SSH for provisioning (same creds as base)
  ssh_username     = "root"
  ssh_password     = "packer-build-temp"
  ssh_timeout      = "10m"
  ssh_port         = 22

  # Shutdown handled by cleanup provisioner
  shutdown_command = ""

  # Headless build
  headless = true
  display  = "none"

  # VNC for debugging
  vnc_bind_address = "127.0.0.1"
  vnc_port_min     = 5900
  vnc_port_max     = 5999

  # CPU passthrough
  qemuargs = [
    ["-cpu", "host"]
  ]
}

# Build configuration
build {
  name    = "layer"
  sources = ["source.qemu.layer"]

  # Step 1: Create target directory
  provisioner "shell" {
    inline = ["mkdir -p /opt/network-agent"]
  }

  # Step 2: Copy Docker Compose files and configs
  provisioner "file" {
    source      = "../docker/"
    destination = "/opt/network-agent/"
  }

  # Step 3: Copy first-boot script
  provisioner "file" {
    source      = "../scripts/first-boot.sh"
    destination = "/opt/network-agent/first-boot.sh"
  }

  # Step 4: Write version file
  provisioner "shell" {
    inline = [
      "echo '${var.version}' > /opt/network-agent/VERSION"
    ]
  }

  # Step 5: Pull Docker images from ghcr.io for offline use
  provisioner "shell" {
    inline = [
      "# Start Docker (may not be running in base image)",
      "systemctl start docker",
      "sleep 5",
      "# Pull images",
      "cd /opt/network-agent && VERSION=${var.version} docker compose pull"
    ]
  }

  # Step 6: First-boot setup + Firewall configuration
  provisioner "shell" {
    scripts = [
      "scripts/05-first-boot-setup.sh",
      "scripts/06-configure-firewall.sh"
    ]
    environment_vars = [
      "DEBIAN_FRONTEND=noninteractive",
      "VERSION=${var.version}"
    ]
    execute_command = "chmod +x {{ .Path }}; {{ .Vars }} {{ .Path }}"
  }

  # Step 7: Final cleanup + Shutdown (must be last!)
  # This step prepares the image for deployment
  provisioner "shell" {
    skip_clean        = true
    expect_disconnect = true
    inline = [
      "# Stop Docker cleanly",
      "systemctl stop docker",
      "# Final cleanup",
      "journalctl --vacuum-time=1s",
      "rm -rf /tmp/* /var/tmp/*",
      "# Reset machine identity (unique per deployment)",
      "rm -f /etc/ssh/ssh_host_*",
      "truncate -s 0 /etc/machine-id",
      "# Zero free space for better compression",
      "dd if=/dev/zero of=/EMPTY bs=1M count=2048 2>/dev/null || true",
      "rm -f /EMPTY",
      "sync",
      "# Shutdown",
      "shutdown -P now"
    ]
  }
}
