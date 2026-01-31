# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.11.0] - 2026-01-31

### Added
- **Open WebUI**: Chat interface at `/chat` for direct model interaction and parameter tuning (#85)
- **Ollama CPU Optimization**: 7 new environment variables for CPU-only appliance (#85)
  - `OLLAMA_FLASH_ATTENTION=1` - Flash attention for KV cache quantization
  - `OLLAMA_KV_CACHE_TYPE=q8_0` - Halves KV cache RAM usage
  - `OLLAMA_MAX_LOADED_MODELS=1` - Prevents loading multiple models (default was 3)
  - `OLLAMA_KEEP_ALIVE=-1` - Model stays permanently loaded (no cold-starts)
  - `OLLAMA_CONTEXT_LENGTH=8192` - Doubled context window
  - `OLLAMA_LOAD_TIMEOUT=10m` - Prevents timeout on slow CPU
  - `OLLAMA_NOPRUNE=true` - Protects pre-baked models from cleanup

### Changed
- **Context Window**: 4k to 8k tokens (same RAM usage via q8_0 KV cache quantization)
- **Batch Size**: 512 to 128 (optimized for 4-core CPU)
- **Inference**: Explicit CPU-only mode (`num_gpu: 0`)

## [0.10.0] - 2026-01-20

### Changed
- **Default Model**: Qwen3 4B Instruct replaces 30B-A3B as default (optimized for CPU-only)
- **Context Window**: Reduced from 32k to 4k tokens for faster CPU inference
- **First-Boot**: Fully automatic process with transparent credential generation

### Added
- **CPU Optimization**: Ollama tuning parameters (num_thread, num_batch, num_ctx)
- **Documentation**: Updated README with dual-mode system requirements (CPU/High-RAM)

## [0.9.0] - 2026-01-17

### Added
- **HTTP API Server**: FastAPI-based REST API for appliance mode (#57)
  - Session management with thread-safe in-memory store
  - `/health` and `/ready` endpoints for Docker healthchecks
  - `/sessions` CRUD endpoints for multi-user support
  - `/sessions/{id}/chat` endpoint with async wrapper for sync agent
  - Structured logging with `structlog`
  - Middleware: Request ID tracking, timing, error handling
- **CLI Server Mode**: New `--serve`, `--host`, `--port` flags
- **Proxmox Appliance Infrastructure**: Docker Compose stack, Packer templates, security scripts (#53)
- **Self-hosted GitHub Actions Runner**: Dedicated LXC on Proxmox for appliance builds (#43)
- **Appliance Build Workflow**: `appliance-build.yml` for qcow2 VM builds

## [0.8.0] - 2026-01-12

### Added
- **Web Search Tool**: New `web_search` tool for searching the web using SearXNG (#34)
- **SearXNG Integration**: Self-hosted meta-search engine, no API key required
- **Docker Compose**: New deployment option with `docker compose up` for full functionality
- **Platform Support**: Separate compose files for Linux (host network) and macOS/Windows (bridge network)

### Changed
- **Deployment**: Docker Compose now recommended for web search functionality

## [0.7.0] - 2026-01-12

### Changed
- **English Messages**: All CLI messages, docstrings, and system prompt switched to English (#27)
- **Breaking Change**: Users wanting German responses should add `Always respond in German.` to system.md

### Added
- **Technical Documentation**: README now includes host limits, port defaults, IPv6 status
- **DNS Exception**: Documented that dns_lookup can query public domains
- **skip_discovery Guide**: Documented when to use -Pn flag and its risks

## [0.6.0] - 2026-01-12

### Added
- **Service Detection Tool**: New `service_detect` tool to identify services and versions (#26)
- **Version Probing**: Detects service names and versions (e.g., "OpenSSH 8.9", "Apache 2.4")
- **Intensity Control**: Probe intensity 1-9 for balance between speed and accuracy
- **Extended Timeout**: Default 300s timeout (service detection is slower than port scanning)

## [0.5.0] - 2026-01-12

### Added
- **Port Scanner Tool**: New `port_scanner` tool for TCP port scanning (#25)
- **Flexible Port Specification**: Port lists (22,80,443) and ranges (1-1000), max 1000 ports
- **Timing Templates**: T0 (slowest) to T5 (fastest) for scan speed control
- **Skip Discovery**: `-Pn` flag support for hosts that block ping
- **Configurable Defaults**: Default ports from config or --top-ports 100

## [0.4.0] - 2026-01-12

### Added
- **DNS Lookup Tool**: New `dns_lookup` tool for DNS queries - A, AAAA, MX, TXT, PTR, NS, SOA, CNAME, SRV records (#24)
- **Auto-Detect Record Type**: IP addresses auto-detect to PTR, hostnames to A record
- **Policy Exception**: DNS lookups allowed on public targets (query DNS servers, not scan targets)

## [0.3.7] - 2026-01-12

### Added
- **Enhanced Validation Layer**: Centralized `resolve_and_validate()` function with hostname resolution, IPv6 blocking, and exclude list support (#23)
- **Config Module**: `tools/config.py` with lazy-loaded singleton pattern for scan configuration
- **Security Hardening**: Block Link-Local (169.254.x.x) and CGNAT (100.64.x.x) addresses
- **Type Guards**: Reject non-string inputs from LLM to prevent type confusion attacks
- **Split Host Limits**: Separate limits for discovery (65536) and port scan (256) operations

### Changed
- **Error Messages**: Consistent "Validation error:" prefix across all validation functions
- **nmap Check Order**: `require_nmap()` called before validation to fail fast

### Fixed
- **Hostname Bypass**: Hostnames resolving to public IPs are now properly blocked
- **Config Crash**: `--list-tools` no longer crashes on invalid config (lazy loading)

## [0.3.6] - 2026-01-09

### Added
- **Config Command**: `/config` displays current LLM configuration (Model, Base URL, Context Limit) (#21)

## [0.3.5] - 2026-01-09

### Added
- **Tools Command**: `/tools` lists all available tools with name and description (#19)

## [0.3.4] - 2026-01-09

### Added
- **Status Command**: `/status` displays session statistics (tokens used, context usage, truncations) (#17)

## [0.3.3] - 2026-01-09

### Added
- **Version Command**: `/version` displays current version in CLI (#14)

## [0.3.2] - 2026-01-09

### Added
- **Slash Commands**: CLI commands now use `/` prefix (`/help`, `/clear`, `/exit`)
- **Help Command**: `/help` shows available commands

### Changed
- **Startup Message**: Now shows "Type /help for available commands"

## [0.3.1] - 2026-01-09

### Added
- **CLI Version Flag**: `--version` / `-V` displays current version

## [0.3.0] - 2026-01-08

### Added
- **Session Memory with Truncation**: Messages persist between runs, automatic cleanup at 80% context limit
- **Context Limit Detection**: Queries /models API, falls back to known defaults or config
- **First-Run Setup Guide**: Detects missing configuration and shows helpful setup instructions
- **Provider Examples**: Documentation for OpenAI, Groq, Venice.ai, Ollama, and more

### Changed
- **Provider-Agnostic Config**: Renamed `VENICE_API_KEY` → `LLM_API_KEY`
- **Flexible LLM Backend**: Works with any OpenAI-compatible API
- **Empty Config Defaults**: User must configure their own provider (no hardcoded values)

### Fixed
- EOF infinite loop in CLI (Ctrl+D now exits cleanly)
- Unused import warning in ping_sweep.py
- Bare except clause in ping_sweep.py

## [0.2.0] - 2026-01-08

### Added
- **Token Usage Display**: Shows tokens per response and session total
- **Cross-Platform Support**: TCP-Connect fallback for macOS/Windows (no raw sockets needed)
- **Input Validation Guardrails**: CIDR validation, injection protection, host limits
- **Convenience Scripts**: `start.sh` (Linux/macOS) and `start.bat` (Windows)
- **GitHub Actions CI**: Automated linting with ruff
- **GitHub Issue Templates**: Bug report and feature request templates

### Security
- Network input sanitization prevents shell injection
- Configurable scan limits (max hosts, allowed networks)

## [0.1.0] - 2026-01-08

### Added
- Initial PoC release
- Venice.ai LLM integration (llama-3.3-70b)
- Ping Sweep tool with nmap backend
- Docker-based deployment
- Basic CLI REPL interface
- Session memory (conversation context)
