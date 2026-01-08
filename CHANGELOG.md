# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
