# Network Agent Appliance - Packer Template
# Builds a COMPLETE qcow2 appliance image with everything included:
#   - Debian 13 (Trixie) + Docker CE
#   - Ollama + Models (from cache)
#   - Network Agent Docker Images (from ghcr.io)
#   - First-boot setup + Firewall
#
# ONE-CLICK SOLUTION: User starts VM and gets ready-to-use appliance
#
# Prerequisites:
#   - KVM/QEMU with hardware virtualization
#   - Packer >= 1.11.0
#   - Ollama model cache at http/ollama-models.tar.zst
#
# Build:
#   packer init .
#   packer build -var "version=0.10.1" base.pkr.hcl

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
  default     = 16384
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
source "qemu" "appliance" {
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

  # Shutdown handled by cleanup provisioner
  shutdown_command = ""

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
  name    = "appliance"
  sources = ["source.qemu.appliance"]

  # Step 0: Copy and install telemetry helpers
  provisioner "file" {
    source      = "scripts/packer-telemetry.sh"
    destination = "/usr/local/bin/telemetry.sh"
  }

  provisioner "shell" {
    inline = [
      "chmod +x /usr/local/bin/telemetry.sh",
      "echo 'Telemetry helpers installed'"
    ]
  }

  # Step 1: Base packages
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "source /usr/local/bin/telemetry.sh",
      "telemetry_start 'Step1_Base_packages'",
      "apt-get update",
      "apt-get install -y --no-install-recommends curl ca-certificates gnupg lsb-release sudo vim-tiny htop jq zstd qemu-guest-agent bc",
      "systemctl enable qemu-guest-agent",
      "telemetry_end 'Step1_Base_packages'"
    ]
    environment_vars = ["DEBIAN_FRONTEND=noninteractive"]
  }

  # Step 2: Docker CE from docker.com
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "source /usr/local/bin/telemetry.sh",
      "telemetry_start 'Step2_Docker_CE'",
      "install -m 0755 -d /etc/apt/keyrings",
      "curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg",
      "echo \"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian trixie stable\" > /etc/apt/sources.list.d/docker.list",
      "apt-get update",
      "apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
      "systemctl enable docker",
      "telemetry_end 'Step2_Docker_CE'"
    ]
    environment_vars = ["DEBIAN_FRONTEND=noninteractive"]
  }

  # Step 3: Hostname & Network (systemd-networkd replaces ifupdown)
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "source /usr/local/bin/telemetry.sh",
      "telemetry_start 'Step3_Network_Config'",
      "echo 'network-agent' > /etc/hostname",
      "echo '127.0.0.1   localhost' > /etc/hosts",
      "echo '127.0.1.1   network-agent' >> /etc/hosts",
      "mv /etc/network/interfaces /etc/network/interfaces.save 2>/dev/null || true",
      "mv /etc/network/interfaces.d /etc/network/interfaces.d.save 2>/dev/null || true",
      "systemctl disable networking.service 2>/dev/null || true",
      "mkdir -p /etc/systemd/network",
      "echo '[Match]' > /etc/systemd/network/20-wired.network",
      "echo 'Type=ether' >> /etc/systemd/network/20-wired.network",
      "echo '' >> /etc/systemd/network/20-wired.network",
      "echo '[Network]' >> /etc/systemd/network/20-wired.network",
      "echo 'DHCP=yes' >> /etc/systemd/network/20-wired.network",
      "echo '' >> /etc/systemd/network/20-wired.network",
      "echo '[DHCPv4]' >> /etc/systemd/network/20-wired.network",
      "echo 'ClientIdentifier=mac' >> /etc/systemd/network/20-wired.network",
      "systemctl enable systemd-networkd",
      "telemetry_end 'Step3_Network_Config'"
    ]
  }

  # Step 4: SSH Hardening
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "source /usr/local/bin/telemetry.sh",
      "telemetry_start 'Step4_SSH_Hardening'",
      "echo 'PermitRootLogin prohibit-password' > /etc/ssh/sshd_config.d/99-hardening.conf",
      "echo 'PasswordAuthentication no' >> /etc/ssh/sshd_config.d/99-hardening.conf",
      "echo 'PubkeyAuthentication yes' >> /etc/ssh/sshd_config.d/99-hardening.conf",
      "echo 'AuthenticationMethods publickey' >> /etc/ssh/sshd_config.d/99-hardening.conf",
      "echo 'X11Forwarding no' >> /etc/ssh/sshd_config.d/99-hardening.conf",
      "echo 'AllowTcpForwarding no' >> /etc/ssh/sshd_config.d/99-hardening.conf",
      "echo 'MaxAuthTries 3' >> /etc/ssh/sshd_config.d/99-hardening.conf",
      "telemetry_end 'Step4_SSH_Hardening'"
    ]
  }

  # Step 5: Kernel Tuning
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "source /usr/local/bin/telemetry.sh",
      "telemetry_start 'Step5_Kernel_Tuning'",
      "echo 'net.ipv4.ping_group_range = 0 65535' > /etc/sysctl.d/99-network-agent.conf",
      "echo 'fs.file-max = 1000000' >> /etc/sysctl.d/99-network-agent.conf",
      "echo 'net.core.somaxconn = 65535' >> /etc/sysctl.d/99-network-agent.conf",
      "echo 'net.ipv4.tcp_tw_reuse = 1' >> /etc/sysctl.d/99-network-agent.conf",
      "echo 'net.ipv4.tcp_fin_timeout = 15' >> /etc/sysctl.d/99-network-agent.conf",
      "echo 'net.core.rmem_max = 16777216' >> /etc/sysctl.d/99-network-agent.conf",
      "echo 'net.core.wmem_max = 16777216' >> /etc/sysctl.d/99-network-agent.conf",
      "echo 'net.ipv4.neigh.default.gc_thresh3 = 16384' >> /etc/sysctl.d/99-network-agent.conf",
      "sysctl --system",
      "telemetry_end 'Step5_Kernel_Tuning'"
    ]
  }

  # Step 6: User Limits
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "source /usr/local/bin/telemetry.sh",
      "telemetry_start 'Step6_User_Limits'",
      "echo '* soft nofile 1000000' > /etc/security/limits.d/99-network-agent.conf",
      "echo '* hard nofile 1000000' >> /etc/security/limits.d/99-network-agent.conf",
      "telemetry_end 'Step6_User_Limits'"
    ]
  }

  # Step 7a: Download Ollama models via HTTP (FAST: parallel, ~500MB/s vs SCP ~100MB/s)
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "source /usr/local/bin/telemetry.sh",
      "telemetry_start 'Step7a_Download_Models'",
      "echo '=== Downloading Ollama models via HTTP ==='",
      "cd /var/tmp",
      "wget -q --show-progress http://{{ .HTTPIP }}:{{ .HTTPPort }}/ollama-models.tar.zst -O ollama-models.tar.zst",
      "ls -lh ollama-models.tar.zst",
      "telemetry_end 'Step7a_Download_Models'"
    ]
  }

  # Step 7b: Extract Ollama models
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "source /usr/local/bin/telemetry.sh",
      "telemetry_start 'Step7b_Extract_Models'",
      "echo '=== Extracting Ollama models ==='",
      "mkdir -p /tmp/ollama-cache",
      "zstd -d /var/tmp/ollama-models.tar.zst -o /var/tmp/ollama-models.tar",
      "tar -xf /var/tmp/ollama-models.tar -C /tmp/ollama-cache",
      "rm /var/tmp/ollama-models.tar /var/tmp/ollama-models.tar.zst",
      "ls -lh /tmp/ollama-cache/",
      "telemetry_end 'Step7b_Extract_Models'"
    ]
  }

  # Step 7c: Ollama + Models (uses cache if available)
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "source /usr/local/bin/telemetry.sh",
      "telemetry_start 'Step7c_Ollama_Install'"
    ]
  }
  provisioner "shell" {
    scripts = [
      "scripts/03-pull-ollama-model.sh"
    ]
    environment_vars = [
      "DEBIAN_FRONTEND=noninteractive",
      "OLLAMA_MODEL=${var.ollama_model}"
    ]
    execute_command = "chmod +x {{ .Path }}; {{ .Vars }} {{ .Path }}"
  }
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "source /usr/local/bin/telemetry.sh",
      "telemetry_end 'Step7c_Ollama_Install'"
    ]
  }

  # ═══════════════════════════════════════════════════════════════════════════
  # NETWORK AGENT LAYER (everything needed for one-click appliance)
  # ═══════════════════════════════════════════════════════════════════════════

  # Step 8: Create target directory
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "source /usr/local/bin/telemetry.sh",
      "telemetry_start 'Step8_Create_Dir'",
      "mkdir -p /opt/network-agent",
      "telemetry_end 'Step8_Create_Dir'"
    ]
  }

  # Step 9: Copy Docker Compose files and configs
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "source /usr/local/bin/telemetry.sh",
      "telemetry_start 'Step9_Copy_Compose'"
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
      "telemetry_end 'Step9_Copy_Compose'"
    ]
  }

  # Step 10: Copy first-boot script
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "source /usr/local/bin/telemetry.sh",
      "telemetry_start 'Step10_Copy_FirstBoot'"
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
      "telemetry_end 'Step10_Copy_FirstBoot'"
    ]
  }

  # Step 11: Write version file
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "source /usr/local/bin/telemetry.sh",
      "telemetry_start 'Step11_Write_Version'",
      "echo '${var.version}' > /opt/network-agent/VERSION",
      "telemetry_end 'Step11_Write_Version'"
    ]
  }

  # Step 12: Pull Docker images from ghcr.io for offline use
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "source /usr/local/bin/telemetry.sh",
      "telemetry_start 'Step12_Docker_Pull'",
      "systemctl start docker",
      "sleep 5",
      "cd /opt/network-agent && VERSION=${var.version} docker compose pull",
      "telemetry_end 'Step12_Docker_Pull'"
    ]
  }

  # Step 13: First-boot setup + Firewall configuration
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "source /usr/local/bin/telemetry.sh",
      "telemetry_start 'Step13_FirstBoot_Firewall'"
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
      "telemetry_end 'Step13_FirstBoot_Firewall'"
    ]
  }

  # Step 14: Final cleanup + Shutdown
  provisioner "shell" {
    skip_clean        = true
    expect_disconnect = true
    inline_shebang = "/bin/bash -e"
    inline = [
      "source /usr/local/bin/telemetry.sh",
      "telemetry_start 'Step14_Cleanup_Shutdown'",
      "systemctl stop docker",
      "cp /etc/apt/sources.list /etc/apt/sources.list.backup 2>/dev/null || true",
      "echo '# Disabled for offline mode' > /etc/apt/sources.list",
      "mv /etc/apt/sources.list.d/docker.list /etc/apt/sources.list.d/docker.list.disabled",
      "apt-get clean && rm -rf /var/lib/apt/lists/*",
      "journalctl --vacuum-time=1s",
      "rm -f /etc/ssh/ssh_host_*",
      "truncate -s 0 /etc/machine-id",
      "telemetry_end 'Step14_Cleanup_Shutdown'",
      "telemetry_summary",
      "rm -rf /tmp/* /var/tmp/*",
      "dd if=/dev/zero of=/EMPTY bs=1M count=2048 2>/dev/null || true",
      "rm -f /EMPTY",
      "sync",
      "shutdown -P now"
    ]
  }
}
