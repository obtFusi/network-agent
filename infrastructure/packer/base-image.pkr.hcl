# Base Image - Debian + Docker + Ollama
# Build once, reuse for all appliance versions
#
# Contains:
#   - Debian 13 (Trixie) minimal
#   - Docker CE
#   - Ollama + qwen3:30b-a3b model (~20GB)
#   - Network/SSH/Kernel configuration
#
# Output: Uploads to MinIO appliance-base/ bucket
# Usage: appliance.pkr.hcl uses this as starting point
#
# Build (rarely needed):
#   packer init .
#   packer build base-image.pkr.hcl

packer {
  required_plugins {
    qemu = {
      version = ">= 1.1.0"
      source  = "github.com/hashicorp/qemu"
    }
  }
}

# Variables
variable "debian_iso_url" {
  type        = string
  description = "URL to Debian netinst ISO"
  default     = "https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/debian-13.3.0-amd64-netinst.iso"
}

variable "debian_iso_checksum" {
  type        = string
  description = "SHA256 checksum of Debian ISO"
  default     = "sha256:c9f09d24b7e834e6834f2ffa565b33d6f1f540d04bd25c79ad9953bc79a8ac02"
}

variable "disk_size" {
  type        = string
  description = "VM disk size"
  default     = "100G"
}

variable "memory" {
  type        = number
  description = "VM memory in MB"
  default     = 16384
}

variable "cpus" {
  type        = number
  description = "Number of CPUs"
  default     = 4
}

variable "ollama_model" {
  type        = string
  description = "Ollama model to embed"
  default     = "qwen3:30b-a3b"
}

variable "nfs_server_ip" {
  type        = string
  description = "IP of NFS server (10.0.2.2 = QEMU user-mode host)"
  default     = "10.0.2.2"
}

# Local variables
locals {
  timestamp   = formatdate("YYYYMMDD", timestamp())
  output_name = "debian-docker-ollama-${local.timestamp}"
}

# QEMU Builder
source "qemu" "base" {
  iso_url          = var.debian_iso_url
  iso_checksum     = var.debian_iso_checksum
  output_directory = "output-base"

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

  shutdown_command = ""

  headless = true
  display  = "none"

  http_port_min = 8080
  http_port_max = 8080

  vnc_bind_address = "127.0.0.1"
  vnc_port_min     = 5900
  vnc_port_max     = 5999

  qemuargs = [
    ["-cpu", "host"]
  ]
}

# Build configuration - BASE IMAGE ONLY
build {
  name    = "base"
  sources = ["source.qemu.base"]

  # Step 1: Base packages
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "echo '=== Step 1: Base packages ==='",
      "apt-get update",
      "apt-get install -y --no-install-recommends curl wget ca-certificates gnupg lsb-release sudo vim-tiny htop jq zstd qemu-guest-agent bc nfs-common",
      "systemctl enable qemu-guest-agent"
    ]
    environment_vars = ["DEBIAN_FRONTEND=noninteractive"]
  }

  # Step 2: Docker CE
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "echo '=== Step 2: Docker CE ==='",
      "install -m 0755 -d /etc/apt/keyrings",
      "curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg",
      "echo \"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian trixie stable\" > /etc/apt/sources.list.d/docker.list",
      "apt-get update",
      "apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
      "systemctl enable docker"
    ]
    environment_vars = ["DEBIAN_FRONTEND=noninteractive"]
  }

  # Step 3: Network Configuration (systemd-networkd)
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "echo '=== Step 3: Network Config ==='",
      "echo 'network-agent' > /etc/hostname",
      "echo '127.0.0.1   localhost' > /etc/hosts",
      "echo '127.0.1.1   network-agent' >> /etc/hosts",
      "mv /etc/network/interfaces /etc/network/interfaces.save 2>/dev/null || true",
      "mv /etc/network/interfaces.d /etc/network/interfaces.d.save 2>/dev/null || true",
      "systemctl disable networking.service 2>/dev/null || true",
      "mkdir -p /etc/systemd/network",
      "cat > /etc/systemd/network/20-wired.network << 'EOF'",
      "[Match]",
      "Type=ether",
      "",
      "[Network]",
      "DHCP=yes",
      "",
      "[DHCPv4]",
      "ClientIdentifier=mac",
      "EOF",
      "systemctl enable systemd-networkd"
    ]
  }

  # Step 4: SSH Hardening
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "echo '=== Step 4: SSH Hardening ==='",
      "cat > /etc/ssh/sshd_config.d/99-hardening.conf << 'EOF'",
      "PermitRootLogin prohibit-password",
      "PasswordAuthentication no",
      "PubkeyAuthentication yes",
      "AuthenticationMethods publickey",
      "X11Forwarding no",
      "AllowTcpForwarding no",
      "MaxAuthTries 3",
      "EOF"
    ]
  }

  # Step 5: Kernel Tuning
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "echo '=== Step 5: Kernel Tuning ==='",
      "cat > /etc/sysctl.d/99-network-agent.conf << 'EOF'",
      "net.ipv4.ping_group_range = 0 65535",
      "fs.file-max = 1000000",
      "net.core.somaxconn = 65535",
      "net.ipv4.tcp_tw_reuse = 1",
      "net.ipv4.tcp_fin_timeout = 15",
      "net.core.rmem_max = 16777216",
      "net.core.wmem_max = 16777216",
      "net.ipv4.neigh.default.gc_thresh3 = 16384",
      "EOF",
      "sysctl --system"
    ]
  }

  # Step 6: User Limits
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "echo '=== Step 6: User Limits ==='",
      "cat > /etc/security/limits.d/99-network-agent.conf << 'EOF'",
      "* soft nofile 1000000",
      "* hard nofile 1000000",
      "EOF"
    ]
  }

  # Step 7a: Transfer Ollama models via NFS
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "echo '=== Step 7a: Transfer Ollama models via NFS ==='",
      "mkdir -p /mnt/nfs-cache",
      "echo 'Mounting NFS from ${var.nfs_server_ip}...'",
      "mount -t nfs -o ro,vers=4 ${var.nfs_server_ip}:/opt/ollama-cache /mnt/nfs-cache",
      "ls -lh /mnt/nfs-cache/",
      "df -h /var/tmp",
      "echo 'Copying models...'",
      "cp -v /mnt/nfs-cache/ollama-models.tar.zst /var/tmp/",
      "umount /mnt/nfs-cache",
      "ls -lh /var/tmp/ollama-models.tar.zst",
      "zstd -t /var/tmp/ollama-models.tar.zst && echo 'Integrity OK'"
    ]
    environment_vars = ["DEBIAN_FRONTEND=noninteractive"]
  }

  # Step 7b: Extract Ollama models (space-optimized)
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "echo '=== Step 7b: Extracting Ollama models ==='",
      "df -h /",
      "mkdir -p /tmp/ollama-cache",
      "exec 3</var/tmp/ollama-models.tar.zst && rm /var/tmp/ollama-models.tar.zst && echo 'Freed archive space' && df -h / && zstd -dc <&3 | tar -xf - -C /tmp/ollama-cache && exec 3<&-",
      "ls -lh /tmp/ollama-cache/",
      "df -h /"
    ]
  }

  # Step 7c: Install Ollama + import models from cache
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

  # Step 8: Create placeholder for Network Agent
  provisioner "shell" {
    inline_shebang = "/bin/bash -e"
    inline = [
      "echo '=== Step 8: Prepare for Network Agent ==='",
      "mkdir -p /opt/network-agent",
      "echo 'BASE_IMAGE' > /opt/network-agent/VERSION",
      "echo 'This base image contains Debian + Docker + Ollama.'",
      "echo 'Network Agent will be added when building the appliance.'"
    ]
  }

  # Final cleanup - keep SSH enabled for appliance build to connect
  provisioner "shell" {
    skip_clean        = true
    expect_disconnect = true
    inline_shebang = "/bin/bash -e"
    inline = [
      "echo '=== Final Cleanup ==='",
      "systemctl stop docker",
      "apt-get clean && rm -rf /var/lib/apt/lists/*",
      "journalctl --vacuum-time=1s",
      "rm -f /etc/ssh/ssh_host_*",
      "truncate -s 0 /etc/machine-id",
      "rm -rf /tmp/* /var/tmp/*",
      "dd if=/dev/zero of=/EMPTY bs=1M count=2048 2>/dev/null || true",
      "rm -f /EMPTY",
      "sync",
      "echo '=== Base Image Complete ==='",
      "shutdown -P now"
    ]
  }
}
