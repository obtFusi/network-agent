# Network Agent Appliance - Uses Pre-built Base Image
# Fast build: Only adds Network Agent layer to existing base
#
# Prerequisites:
#   - Base image in MinIO: appliance-base/debian-docker-ollama-YYYYMMDD.qcow2
#   - Or local: output-base/debian-docker-ollama-*.qcow2
#
# Build (~5 min instead of ~40 min):
#   packer init .
#   packer build -var "version=0.10.1" -var "base_image_url=file://output-base/debian-docker-ollama-20260125.qcow2" appliance.pkr.hcl

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

variable "base_image_url" {
  type        = string
  description = "URL to base image (MinIO or local file://)"
  # Default: latest from MinIO (workflow sets this dynamically)
  default     = ""
}

variable "base_image_checksum" {
  type        = string
  description = "SHA256 checksum of base image (optional, skip with 'none')"
  default     = "none"
}

variable "disk_size" {
  type        = string
  description = "VM disk size (must match base image)"
  default     = "100G"
}

variable "memory" {
  type        = number
  description = "VM memory in MB"
  default     = 8192
}

variable "cpus" {
  type        = number
  description = "Number of CPUs"
  default     = 4
}

# Local variables
locals {
  output_name = "network-agent-${var.version}"
}

# QEMU Builder - starts from base image
source "qemu" "appliance" {
  # Use base image as starting disk (not ISO)
  iso_url      = var.base_image_url
  iso_checksum = var.base_image_checksum
  disk_image   = true

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

  # No boot command needed - base image already installed
  boot_wait    = "30s"
  boot_command = []

  # SSH to base image (root with temp password from preseed)
  ssh_username     = "root"
  ssh_password     = "packer-build-temp"
  ssh_timeout      = "5m"
  ssh_port         = 22

  shutdown_command = ""

  headless = true
  display  = "none"

  vnc_bind_address = "127.0.0.1"
  vnc_port_min     = 5900
  vnc_port_max     = 5999

  qemuargs = [
    ["-cpu", "host"]
  ]
}

# Build configuration - NETWORK AGENT LAYER ONLY
build {
  name    = "appliance"
  sources = ["source.qemu.appliance"]

  # Step 0: Install telemetry helpers
  provisioner "file" {
    source      = "scripts/packer-telemetry.sh"
    destination = "/usr/local/bin/telemetry.sh"
  }

  provisioner "shell" {
    inline = [
      "chmod +x /usr/local/bin/telemetry.sh",
      "echo '=== Building Network Agent v${var.version} on Base Image ==='"
    ]
  }

  # Step 1: Verify base image
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "source /usr/local/bin/telemetry.sh",
      "telemetry_start 'Step1_Verify_Base'",
      "echo '=== Verifying Base Image ==='",
      "cat /opt/network-agent/VERSION",
      "docker --version",
      "ollama --version",
      "systemctl status ollama --no-pager || true",
      "telemetry_end 'Step1_Verify_Base'"
    ]
  }

  # Step 2: Copy Docker Compose files
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "source /usr/local/bin/telemetry.sh",
      "telemetry_start 'Step2_Copy_Compose'"
    ]
  }
  provisioner "file" {
    source      = "../docker/"
    destination = "/opt/network-agent/"
  }
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "source /usr/local/bin/telemetry.sh",
      "telemetry_end 'Step2_Copy_Compose'"
    ]
  }

  # Step 3: Copy first-boot script
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "source /usr/local/bin/telemetry.sh",
      "telemetry_start 'Step3_Copy_FirstBoot'"
    ]
  }
  provisioner "file" {
    source      = "../scripts/first-boot.sh"
    destination = "/opt/network-agent/first-boot.sh"
  }
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "source /usr/local/bin/telemetry.sh",
      "telemetry_end 'Step3_Copy_FirstBoot'"
    ]
  }

  # Step 4: Write version file
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "source /usr/local/bin/telemetry.sh",
      "telemetry_start 'Step4_Write_Version'",
      "echo '${var.version}' > /opt/network-agent/VERSION",
      "cat /opt/network-agent/VERSION",
      "telemetry_end 'Step4_Write_Version'"
    ]
  }

  # Step 5: Pull Docker images from ghcr.io
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "source /usr/local/bin/telemetry.sh",
      "telemetry_start 'Step5_Docker_Pull'",
      "systemctl start docker",
      "sleep 5",
      "cd /opt/network-agent && VERSION=${var.version} docker compose pull",
      "docker images",
      "telemetry_end 'Step5_Docker_Pull'"
    ]
  }

  # Step 6: First-boot setup + Firewall
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "source /usr/local/bin/telemetry.sh",
      "telemetry_start 'Step6_FirstBoot_Firewall'"
    ]
  }
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
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "source /usr/local/bin/telemetry.sh",
      "telemetry_end 'Step6_FirstBoot_Firewall'"
    ]
  }

  # Step 7: Final cleanup + Shutdown
  provisioner "shell" {
    skip_clean        = true
    expect_disconnect = true
    inline_shebang = "/bin/bash -e"
    inline = [
      "source /usr/local/bin/telemetry.sh",
      "telemetry_start 'Step7_Cleanup_Shutdown'",
      "systemctl stop docker",
      "cp /etc/apt/sources.list /etc/apt/sources.list.backup 2>/dev/null || true",
      "echo '# Disabled for offline mode' > /etc/apt/sources.list",
      "mv /etc/apt/sources.list.d/docker.list /etc/apt/sources.list.d/docker.list.disabled 2>/dev/null || true",
      "apt-get clean && rm -rf /var/lib/apt/lists/*",
      "journalctl --vacuum-time=1s",
      "rm -f /etc/ssh/ssh_host_*",
      "truncate -s 0 /etc/machine-id",
      "telemetry_end 'Step7_Cleanup_Shutdown'",
      "telemetry_summary",
      "rm -rf /tmp/* /var/tmp/*",
      "dd if=/dev/zero of=/EMPTY bs=1M count=1024 2>/dev/null || true",
      "rm -f /EMPTY",
      "sync",
      "echo '=== Network Agent v${var.version} Appliance Complete ==='",
      "shutdown -P now"
    ]
  }
}
