# Network Agent

[![Version](https://img.shields.io/badge/version-0.10.0-blue.svg)](CHANGELOG.md)

> **For Developers:** [CI/CD Documentation](docs/CICD.md) - Pipeline, GitHub Actions, Claude Code Skills

An AI-powered network scanner. Instead of learning complex terminal commands, just ask questions like *"What devices are on my network?"* - the agent handles the rest.

## What does this tool do?

Network Agent combines:
- **Natural Language**: Ask what you want to know in plain English
- **AI Processing**: Any OpenAI-compatible API understands your request
- **Network Tools**: nmap performs the actual scans
- **Clear Answers**: Results are presented in an understandable format

**Example:**
```
> What devices are online in network 192.168.1.0/24?

I found 7 active devices:
- 192.168.1.1 (Router)
- 192.168.1.10 (Desktop PC)
- 192.168.1.15 (Smartphone)
...
```

## Supported LLM Providers

Network Agent works with any **OpenAI-compatible API**. This includes:

| Provider | API Endpoint | Example Models |
|----------|-------------|-----------------|
| [OpenAI](https://openai.com) | `https://api.openai.com/v1` | gpt-4, gpt-3.5-turbo |
| [Venice.ai](https://venice.ai) | `https://api.venice.ai/api/v1` | llama-3.3-70b, mistral-large |
| [Together.ai](https://together.ai) | `https://api.together.xyz/v1` | llama-3-70b, mixtral-8x7b |
| [Groq](https://groq.com) | `https://api.groq.com/openai/v1` | llama-3.3-70b, mixtral-8x7b |
| [Ollama](https://ollama.com) | `http://localhost:11434/v1` | llama3, mistral, codellama |
| [LM Studio](https://lmstudio.ai) | `http://localhost:1234/v1` | Any local models |

**Requirement:** The provider must support the [OpenAI Chat Completions API](https://platform.openai.com/docs/api-reference/chat) with Tool/Function Calling.

## Prerequisites

1. **Docker** - [Download Docker Desktop](https://www.docker.com/products/docker-desktop/)
2. **API Key** from a supported provider (see above)
3. **Git** (optional) - [Download Git](https://git-scm.com/downloads)

## Installation

### 1. Download the repository

```bash
git clone https://github.com/obtFusi/network-agent.git
cd network-agent
```

Or: [Download ZIP](https://github.com/obtFusi/network-agent/archive/refs/heads/main.zip) and extract.

### 2. Configure LLM Provider

**Step A: Set API Key**

Copy the template and enter your API key:

```bash
cp .env.example .env
```

Edit `.env`:
```
LLM_API_KEY=your_api_key_here
```

**Step B: Configure Provider and Model**

Edit `config/settings.yaml`:

```yaml
llm:
  provider:
    model: "gpt-4"                        # <-- Your model
    base_url: "https://api.openai.com/v1" # <-- Your API URL
    temperature: 0.7
    max_tokens: 4096
```

<details>
<summary><strong>Example configurations for different providers</strong></summary>

**OpenAI:**
```yaml
model: "gpt-4"
base_url: "https://api.openai.com/v1"
```

**Venice.ai:**
```yaml
model: "llama-3.3-70b"
base_url: "https://api.venice.ai/api/v1"
```

**Groq (fast & affordable):**
```yaml
model: "llama-3.3-70b-versatile"
base_url: "https://api.groq.com/openai/v1"
```

**Ollama (local):**
```yaml
model: "llama3"
base_url: "http://host.docker.internal:11434/v1"
```
*Note: `host.docker.internal` allows Docker to access host services*

</details>

<details>
<summary><strong>Customize scan settings (Optional)</strong></summary>

**Exclude specific devices from scans:**

Want to exclude certain IPs from scanning (e.g., critical servers, printers)? Add them to `config/settings.yaml`:

```yaml
scan:
  exclude_ips:
    - "192.168.1.1"       # Don't scan router
    - "192.168.1.100"     # Exclude NAS
    - "10.0.0.0/24"       # Ignore entire management network
```

**Increase scan timeout:**

For slow networks or many hosts, the scan might timeout. Increase the limit:

```yaml
scan:
  timeout: 300  # 5 minutes instead of default 2 minutes
```

**Scan larger networks:**

By default, port scans are limited to /24 (256 hosts). For larger networks:

```yaml
scan:
  max_hosts_portscan: 1024  # Allows /22 networks
```

*Note: Larger scans take correspondingly longer!*

</details>

### 3. Build Docker Image

```bash
docker build -t network-agent:latest .
```

### 4. Start the Agent

**With Web Search (recommended):**

```bash
# Linux (LAN scans + web search):
docker compose up

# macOS/Windows (web search, limited network scans):
docker compose -f docker-compose.macos.yml up
```

**Without Web Search (classic mode):**

```bash
# Linux:
docker run -it --rm --network host --env-file .env network-agent:latest

# Windows with WSL2:
docker run -it --rm --network host --env-file .env network-agent:latest

# Windows without WSL / macOS:
docker run -it --rm --env-file .env network-agent:latest
```

> **Note:** Docker Compose automatically starts SearXNG for web searches. Without `--network host`, LAN scanning is limited.

### Alternative: Proxmox Appliance

For a turnkey solution, there's a preconfigured **Proxmox VM** with everything preinstalled:

<details>
<summary><strong>One-Click Installation on Proxmox</strong></summary>

**What's included?**
- Network Agent (preinstalled)
- Ollama with Qwen3 (local LLM, no API key needed)
  - **Standard:** Qwen3 4B Instruct (~3GB, optimized for CPU-only)
  - **Optional:** Qwen3 30B-A3B (~20GB, better quality with more RAM)
- Caddy Reverse Proxy (HTTPS + Basic Auth)
- PostgreSQL (Database)
- Offline-capable (no external dependencies at runtime)

**System Requirements:**

| Mode | RAM | CPU | Disk | Model |
|------|-----|-----|------|-------|
| Standard (CPU) | 8-16 GB | 4+ Cores | 50 GB | Qwen3 4B Instruct |
| High-Quality | 24-32 GB | 4-8 Cores | 100 GB | Qwen3 30B-A3B |

**Installation (One-Click):**

```bash
# Run on the Proxmox host:
curl -sSL https://github.com/obtFusi/network-agent/releases/latest/download/install-network-agent.sh | bash -s -- 200

# Or with custom storage:
curl -sSL https://github.com/obtFusi/network-agent/releases/latest/download/install-network-agent.sh | bash -s -- 200 ceph-pool
```

The script:
1. Downloads the image (~8GB compressed, 14 parts)
2. Verifies SHA256 checksums
3. Decompresses to ~22GB qcow2
4. Creates VM 200 with optimal settings
5. Ready to start!

**Manual Download:**

```bash
# Download all parts + checksums
VERSION="0.10.0"
for part in aa ab ac ad ae af ag ah ai aj ak al am an; do
  wget "https://github.com/obtFusi/network-agent/releases/download/v${VERSION}/network-agent-${VERSION}.qcow2.zst.part-${part}"
done
wget "https://github.com/obtFusi/network-agent/releases/download/v${VERSION}/SHA256SUMS"

# Verify checksums (IMPORTANT!)
sha256sum -c SHA256SUMS

# Combine and decompress
cat network-agent-${VERSION}.qcow2.zst.part-* | zstd -d -o network-agent.qcow2

# Create VM
qm create 200 --name network-agent --memory 16384 --cores 4 --cpu host
qm importdisk 200 network-agent.qcow2 local-lvm --format qcow2
qm set 200 --scsi0 local-lvm:vm-200-disk-0 --boot order=scsi0
qm set 200 --net0 virtio,bridge=vmbr0
```

**First Boot:**

```bash
qm start 200
qm terminal 200
```

On first login:
1. Automatic first-boot starts
2. Set new root password (required!)
3. Web credentials are generated and displayed
4. Services start automatically

**Access:**
- Web UI: `https://<VM-IP>` (credentials from first-boot)
- SSH: `ssh root@<VM-IP>`

**Scan Mode (Host Network for L2/L3):**

```bash
ssh root@<VM-IP>
cd /opt/network-agent
docker compose down
docker compose -f docker-compose.yml -f docker-compose.scan-mode.yml up -d
```

**Online Mode (with Web Search via SearXNG):**

```bash
ssh root@<VM-IP>
cd /opt/network-agent
docker compose down
docker compose -f docker-compose.yml -f docker-compose.online.yml up -d
```

**Ports:**
- 443: HTTPS Web Interface (Caddy)
- 22: SSH

</details>

## Usage

After starting, you'll see:
```
Network Agent starting...
   Model: gpt-4
   Context limit: 8,192 tokens
   Type /help for available commands

>
```

### What can I ask?

**Find devices on the network:**
- `What devices are on network 192.168.1.0/24?`
- `Scan my home network 192.168.178.0/24`
- `Who is currently online?` *(if you've scanned a network before)*
- `Show me all active hosts in 10.0.0.0/24`

**DNS queries:**
- `What IP does example.com have?`
- `Show me the MX records for gmail.com`
- `Reverse DNS for 8.8.8.8`
- `Which nameserver is responsible for heise.de?`

> **Good to know:**
> - MX = Mail servers, NS = Nameservers, TXT = Text records (e.g., SPF)
> - "Reverse DNS" finds the hostname for an IP address
> - DNS queries also work for public domains

**Port scans:**
- `Scan ports 22, 80, 443 on 192.168.1.1`
- `What ports are open on the router?`
- `Check ports 1-1000 on 192.168.1.10`
- `Quick port scan on 192.168.1.0/24` *(with T4 timing)*

> **Good to know:**
> - Without port specification, the 100 most common ports are checked
> - You can specify individual ports (`22,80,443`) or ranges (`1-1000`)
> - "Fast" or "slow" controls scan speed
> - Some devices don't respond to ping - then say "even without ping"

**Service detection:**
- `What services are running on 192.168.1.1?`
- `Detect versions on the router`
- `What web server is running on 192.168.1.10:80?`
- `Thorough service detection on 192.168.1.5` *(with high intensity)*

> **Good to know:**
> - Detects service names and versions (e.g., "OpenSSH 8.9", "Apache 2.4")
> - Slower than port scan, but more details
> - "Thorough" or "intensive" for better detection, "quick" for superficial
> - Without port specification, the 20 most common ports are checked

**Web search (only with Docker Compose):**
- `Search for nmap scripting documentation`
- `What is SearXNG?`
- `Find tutorials on Python network programming`

> **Good to know:**
> - Web search only works with Docker Compose (`docker compose up`)
> - All search queries stay local (no external API key needed)
> - Categories available: general, images, news, science, it, files

**Follow-up questions:**
- `Which of these have open ports?`
- `What's running on 192.168.1.10?`
- `Are there web servers on the network?`

**Tips:**
- For network scans, you need a network specification (e.g., `192.168.1.0/24`)
- DNS queries work with any hostname or IP
- The agent remembers previous results - you can ask follow-up questions
- Phrase it like you would ask a colleague

### Commands
- `/help` - Show available commands
- `/tools` - List available tools (name + description)
- `/config` - Show LLM configuration (model, base URL, context limit)
- `/status` - Show session statistics (tokens, context usage, truncations)
- `/version` - Show version
- `/clear` - Clear session memory
- `/exit` - Exit

## Platform Compatibility

| System | LAN Scan | Method | How to start? |
|--------|----------|--------|---------------|
| Linux | Full | ICMP Ping | `--network host` |
| Windows + WSL2 | Full | ICMP Ping | In WSL terminal |
| Windows (PowerShell) | Yes | TCP-Connect | Start normally |
| macOS | Yes | TCP-Connect | Start normally |

**Automatic Detection:** The agent automatically detects if ICMP ping is possible. If not (Docker on Windows/macOS), TCP-Connect scan is used automatically.

## Security

Network Agent is designed for **local network analysis**:

| What's allowed? | What's blocked? |
|-----------------|-----------------|
| Private IPs (192.168.x.x, 10.x.x.x, 172.16-31.x.x) | Public IPs (Internet) |
| Loopback (127.0.0.1) | IPv6 addresses |
| Your local network | Link-Local (169.254.x.x) |

**Why these restrictions?**
- Prevents accidental scanning of external systems on the internet
- Protects against misuse as an attack tool
- Focuses on the actual use case: home network analysis

**Want to scan a specific network anyway?**
Configure exceptions in `config/settings.yaml` (see scan settings above).

<details>
<summary><strong>Technical details about the tools</strong></summary>

### Host Limits

| Tool | Max Hosts | Network | Reason |
|------|-----------|---------|--------|
| ping_sweep | 65,536 | /16 | Fast: 1 probe per host |
| port_scanner | 256 | /24 | Slow: many probes per port |
| service_detect | 256 | /24 | Very slow: multiple probes per service |
| dns_lookup | 1 | Single | DNS queries are always individual |

**Why the difference?** Discovery (ping_sweep) sends only one probe per host and is therefore fast. Port and service scans send many probes per host and would take very long for large networks.

### Port Defaults

| Tool | Default Ports | Configurable? |
|------|---------------|---------------|
| ping_sweep | 22, 80, 443, 8080 | No (fixed) |
| port_scanner | Top 100 | Yes (`ports` parameter) |
| service_detect | Top 20 | Yes (`ports` parameter) |

### IPv6 Support

**Status:** Not supported (not planned)

All tools reject IPv6 addresses (e.g., `::1`, `fe80::1`, `2001:db8::1`). The focus is on IPv4 home networks.

### DNS Lookup Exception

The `dns_lookup` tool is the only tool allowed to query public domains. This is intentional because DNS queries are not scans - they only query DNS servers.

</details>

## Updating

To update to the latest version:

```bash
# 1. Get latest code
cd network-agent
git pull

# 2. Rebuild Docker image (IMPORTANT!)
docker build -t network-agent:latest .

# 3. Start agent
docker run -it --rm --network host --env-file .env network-agent:latest
```

**When to rebuild?**
- After every `git pull` (code changes)
- After changes to `requirements.txt`
- After changes to `Dockerfile`

**Tip:** The convenience scripts (`start.sh`, `start.bat`) only build the image if it doesn't exist. After updates, you must run `docker build` manually or delete the old image:
```bash
docker rmi network-agent:latest
./start.sh
```

## Troubleshooting

> **For Developers:** Project structure and how to add custom tools can be found [at the end of this page](#for-developers-project-structure--custom-tools).

<details>
<summary><strong>"LLM_API_KEY environment variable not set"</strong></summary>

The `.env` file is missing or doesn't contain a key.

**Solution:**
```bash
cp .env.example .env
# Then edit .env and enter your API key
```
</details>

<details>
<summary><strong>"Error: Scan timeout"</strong></summary>

The scan takes too long and aborts.

**Possible causes:**
- Network too large (e.g., /16 instead of /24)
- Network not reachable
- Firewall blocking packets

**Solutions:**
1. Try smaller subnet: `/28` (16 hosts) instead of `/24` (256 hosts)
2. Increase timeout in `config/settings.yaml`: `timeout: 300`
3. Check if you're in the correct network
</details>

<details>
<summary><strong>No devices found</strong></summary>

The scan completes but finds nothing.

**On Windows/macOS:**
TCP-Connect scan only finds devices with open standard ports (22, 80, 443...).
→ For complete detection: Use WSL2 on Windows

**On Linux:**
- Are you in the correct network? Check with `ip addr`
- Is `--network host` set when starting Docker?
- Check firewall on the host system
</details>

<details>
<summary><strong>"Validation error: Public IP not allowed"</strong></summary>

You're trying to scan a public IP or internet network.

**Why?** The agent is only intended for local networks.

**Solution:** Use private IP ranges:
- `192.168.x.x/24` (home networks)
- `10.x.x.x/24` (corporate networks)
- `172.16-31.x.x/24` (Docker, VPNs)
</details>

<details>
<summary><strong>Model not found / API Error</strong></summary>

The LLM provider responds with an error.

**Check in `config/settings.yaml`:**
- Is `model` spelled correctly? (e.g., `gpt-4` not `GPT-4`)
- Is `base_url` correct for your provider?
- Does your provider support Tool/Function Calling?

**Check your API key:**
- Is the key in `.env` correct?
- Does the key have enough balance/credits?
- Is the key authorized for the selected model?
</details>

<details>
<summary><strong>Agent doesn't respond sensibly</strong></summary>

The AI doesn't understand your question or gives strange answers.

**Tips:**
- Be more specific: `Scan 192.168.1.0/24` instead of `Scan my network`
- Always specify the network
- Use `/clear` to reset the session
- Try a different/larger model (e.g., gpt-4 instead of gpt-3.5)
</details>

---

<details>
<summary><strong>For Developers: Project Structure & Custom Tools</strong></summary>

### Files in the project

```
network-agent/
├── cli.py              # Main program (REPL)
├── agent/
│   ├── core.py         # AI agent with tool loop + session memory
│   └── llm.py          # LLM client (OpenAI-compatible)
├── tools/
│   ├── base.py         # Tool base class
│   ├── config.py       # Scan configuration (singleton)
│   ├── validation.py   # Input validation
│   ├── network/        # Network tools
│   │   ├── ping_sweep.py
│   │   ├── dns_lookup.py
│   │   ├── port_scanner.py
│   │   └── service_detect.py
│   └── web/            # Web tools
│       └── web_search.py   # SearXNG web search
├── config/
│   ├── settings.yaml   # Provider & scan configuration
│   └── prompts/
│       └── system.md   # System prompt for AI
├── searxng/            # SearXNG configuration
│   └── settings.yml    # Search engine configuration
├── docker-compose.yml  # Linux (with host network)
├── docker-compose.macos.yml  # macOS/Windows (with bridge network)
├── Dockerfile          # Container definition
├── requirements.txt    # Python dependencies
└── .env.example        # API key template
```

### Adding custom tools

1. Create new file under `tools/`
2. Inherit from `BaseTool` and implement `name`, `description`, `parameters`, `execute`
3. Register in `tools/__init__.py`

See `tools/network/ping_sweep.py` for an example.

</details>

## License

MIT
