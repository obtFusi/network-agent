# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
