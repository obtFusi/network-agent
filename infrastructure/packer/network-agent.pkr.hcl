# Network Agent Appliance - Packer Template
# Builds a qcow2 image for Proxmox deployment
#
# Prerequisites:
#   - KVM/QEMU with hardware virtualization
#   - Packer >= 1.11.0
#   - Internet access for Debian install
#
# Build:
#   packer init .
#   packer build -var "version=0.4.0" network-agent.pkr.hcl

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
  description = "Appliance version (e.g., 0.4.0)"
  default     = "0.4.0"
}

variable "debian_iso_url" {
  type        = string
  description = "URL to Debian netinst ISO"
  default     = "https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/debian-12.9.0-amd64-netinst.iso"
}

variable "debian_iso_checksum" {
  type        = string
  description = "SHA256 checksum of Debian ISO"
  # Debian 12.9.0 amd64 netinst
  default     = "sha256:1536d182c739e8b48102c9e76d0dc8cf3e1bb12c925a9f3c0c1d44fb35fef50a"
}

variable "disk_size" {
  type        = string
  description = "VM disk size"
  default     = "100G"
}

variable "memory" {
  type        = number
  description = "VM memory in MB (for build only)"
  default     = 8192
}

variable "cpus" {
  type        = number
  description = "Number of CPUs (for build only)"
  default     = 4
}

variable "ollama_model" {
  type        = string
  description = "Ollama model to embed"
  default     = "qwen3:30b-a3b"
}

# Local variables
locals {
  output_name = "network-agent-${var.version}"
}

# QEMU Builder - produces qcow2 directly
source "qemu" "network-agent" {
  iso_url          = var.debian_iso_url
  iso_checksum     = var.debian_iso_checksum
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

  # Debian preseed for unattended install
  http_directory = "http"
  boot_wait      = "5s"
  boot_command = [
    "<esc><wait>",
    "auto url=http://{{ .HTTPIP }}:{{ .HTTPPort }}/preseed.cfg ",
    "hostname=network-agent ",
    "domain=local ",
    "debian-installer/language=en ",
    "debian-installer/country=US ",
    "debian-installer/locale=en_US.UTF-8 ",
    "keyboard-configuration/xkb-keymap=us ",
    "<enter>"
  ]

  # SSH for provisioning
  ssh_username     = "root"
  ssh_password     = "packer-build-temp"
  ssh_timeout      = "30m"
  ssh_port         = 22

  # Shutdown
  shutdown_command = "shutdown -P now"

  # Headless build
  headless = true
  display  = "none"

  # VNC for debugging (set headless=false to use)
  vnc_bind_address = "127.0.0.1"
  vnc_port_min     = 5900
  vnc_port_max     = 5999

  # CPU passthrough for better build performance
  qemuargs = [
    ["-cpu", "host"]
  ]
}

# Build configuration
build {
  name    = "network-agent"
  sources = ["source.qemu.network-agent"]

  # Copy Docker Compose files
  provisioner "file" {
    source      = "../docker/"
    destination = "/opt/network-agent/"
  }

  # Copy first-boot script
  provisioner "file" {
    source      = "../scripts/first-boot.sh"
    destination = "/opt/network-agent/first-boot.sh"
  }

  # Write version file
  provisioner "shell" {
    inline = [
      "echo '${var.version}' > /opt/network-agent/VERSION"
    ]
  }

  # Run provisioning scripts
  provisioner "shell" {
    scripts = [
      "scripts/01-base-setup.sh",
      "scripts/02-pull-images.sh",
      "scripts/03-pull-ollama-model.sh",
      "scripts/04-configure-compose.sh",
      "scripts/05-first-boot-setup.sh",
      "scripts/06-configure-firewall.sh",
      "scripts/99-cleanup.sh"
    ]
    environment_vars = [
      "DEBIAN_FRONTEND=noninteractive",
      "VERSION=${var.version}",
      "OLLAMA_MODEL=${var.ollama_model}"
    ]
    execute_command = "chmod +x {{ .Path }}; {{ .Vars }} {{ .Path }}"
  }

  # No post-processor needed - qcow2 is our target format
  # Compression and splitting happens in CI
}
