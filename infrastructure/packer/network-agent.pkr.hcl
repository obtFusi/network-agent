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
  default     = "https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/debian-13.3.0-amd64-netinst.iso"
}

variable "debian_iso_checksum" {
  type        = string
  description = "SHA256 checksum of Debian ISO"
  # Debian 13.3.0 (Trixie) amd64 netinst
  default     = "sha256:c9f09d24b7e834e6834f2ffa565b33d6f1f540d04bd25c79ad9953bc79a8ac02"
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

  # Create target directory first (file provisioner cannot create directories)
  provisioner "shell" {
    inline = ["mkdir -p /opt/network-agent"]
  }

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

  # Step 1: Base packages
  provisioner "shell" {
    inline = [
      "apt-get update",
      "apt-get install -y --no-install-recommends curl ca-certificates gnupg lsb-release sudo vim-tiny htop jq zstd qemu-guest-agent",
      "systemctl enable qemu-guest-agent"
    ]
    environment_vars = ["DEBIAN_FRONTEND=noninteractive"]
  }

  # Step 2: Docker CE from docker.com
  provisioner "shell" {
    inline = [
      "install -m 0755 -d /etc/apt/keyrings",
      "curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg",
      "echo \"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian trixie stable\" > /etc/apt/sources.list.d/docker.list",
      "apt-get update",
      "apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
      "systemctl enable docker"
    ]
    environment_vars = ["DEBIAN_FRONTEND=noninteractive"]
  }

  # Step 3: Hostname & Network
  provisioner "shell" {
    inline = [
      "echo 'network-agent' > /etc/hostname",
      "cat > /etc/hosts << 'EOF'\n127.0.0.1   localhost\n127.0.1.1   network-agent\nEOF",
      "cat > /etc/systemd/network/20-wired.network << 'EOF'\n[Match]\nName=ens18\n[Network]\nDHCP=yes\nEOF",
      "systemctl enable systemd-networkd"
    ]
  }

  # Step 4: SSH Hardening
  provisioner "shell" {
    inline = [
      "cat > /etc/ssh/sshd_config.d/99-hardening.conf << 'EOF'\nPermitRootLogin prohibit-password\nPasswordAuthentication no\nPubkeyAuthentication yes\nAuthenticationMethods publickey\nX11Forwarding no\nAllowTcpForwarding no\nMaxAuthTries 3\nEOF"
    ]
  }

  # Step 5: Kernel Tuning
  provisioner "shell" {
    inline = [
      "cat > /etc/sysctl.d/99-network-agent.conf << 'EOF'\nnet.ipv4.ping_group_range = 0 65535\nfs.file-max = 1000000\nnet.core.somaxconn = 65535\nnet.ipv4.tcp_tw_reuse = 1\nnet.ipv4.tcp_fin_timeout = 15\nnet.core.rmem_max = 16777216\nnet.core.wmem_max = 16777216\nnet.ipv4.neigh.default.gc_thresh3 = 16384\nEOF",
      "sysctl --system"
    ]
  }

  # Step 6: User Limits
  provisioner "shell" {
    inline = [
      "cat > /etc/security/limits.d/99-network-agent.conf << 'EOF'\n* soft nofile 1000000\n* hard nofile 1000000\nEOF"
    ]
  }

  # Step 8: Pull Docker images for offline use
  provisioner "shell" {
    inline = [
      "cd /opt/network-agent && docker compose pull"
    ]
  }

  # Step 9: Systemd Service (disabled - enabled by first-boot)
  provisioner "shell" {
    inline = [
      "cat > /etc/systemd/system/network-agent.service << 'EOF'\n[Unit]\nDescription=Network Agent Docker Compose Stack\nRequires=docker.service\nAfter=docker.service network-online.target\n\n[Service]\nType=oneshot\nRemainAfterExit=yes\nWorkingDirectory=/opt/network-agent\nExecStart=/usr/bin/docker compose up -d\nExecStop=/usr/bin/docker compose down\nTimeoutStartSec=300\n\n[Install]\nWantedBy=multi-user.target\nEOF",
      "systemctl daemon-reload"
    ]
  }

  # Run additional provisioning scripts
  provisioner "shell" {
    scripts = [
      "scripts/03-pull-ollama-model.sh",
      "scripts/05-first-boot-setup.sh",
      "scripts/06-configure-firewall.sh"
    ]
    environment_vars = [
      "DEBIAN_FRONTEND=noninteractive",
      "VERSION=${var.version}",
      "OLLAMA_MODEL=${var.ollama_model}"
    ]
    execute_command = "chmod +x {{ .Path }}; {{ .Vars }} {{ .Path }}"
  }

  # Step 7: APT Offline + Step 10: Cleanup (must be last!)
  provisioner "shell" {
    inline = [
      "# APT Offline",
      "cp /etc/apt/sources.list /etc/apt/sources.list.backup 2>/dev/null || true",
      "echo '# Disabled for offline mode' > /etc/apt/sources.list",
      "mv /etc/apt/sources.list.d/docker.list /etc/apt/sources.list.d/docker.list.disabled",
      "apt-get clean && rm -rf /var/lib/apt/lists/*",
      "# Cleanup",
      "journalctl --vacuum-time=1s",
      "rm -rf /tmp/* /var/tmp/*",
      "rm -f /etc/ssh/ssh_host_*",
      "truncate -s 0 /etc/machine-id",
      "dd if=/dev/zero of=/EMPTY bs=1M 2>/dev/null || true",
      "rm -f /EMPTY"
    ]
  }

  # No post-processor needed - qcow2 is our target format
  # Compression and splitting happens in CI
}
