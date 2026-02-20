# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.12.x  | Yes       |
| < 0.12  | No        |

## Reporting a Vulnerability

If you discover a security vulnerability in Network Agent, please report it responsibly:

1. **DO NOT** create a public GitHub issue for security vulnerabilities
2. Use GitHub's private vulnerability reporting:
   **Settings > Security > Advisories > Report a vulnerability**

### What to Report

Please report vulnerabilities in the Network Agent tool itself, such as:
- Authorization bypass (tools executing without required authorization level)
- Input validation bypass (scanning outside allowed scope)
- Credential leakage (passwords/hashes stored unredacted in database)
- Command injection via tool parameters
- Information disclosure via API endpoints

**Not in scope:** Findings from targets you scan with the tool. Those are findings about *your* network, not vulnerabilities in Network Agent.

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Affected version(s)
- Suggested fix (if any)

### Response Timeline

| Severity | Acknowledgment | Assessment | Fix |
|----------|---------------|------------|-----|
| Critical | 24 hours | 3 days | 72 hours |
| High     | 48 hours | 7 days | 2 weeks |
| Medium   | 72 hours | 14 days | Next release |
| Low      | 1 week | 30 days | Best effort |

## Security Measures

- **Authorization System**: 3-tier authorization (passive/active/destructive) prevents accidental execution of offensive tools
- **Human-in-the-Loop**: Destructive tools require CLI confirmation that cannot be automated by the LLM
- **Credential Redaction**: Passwords, NTLM hashes, and API keys are automatically stripped from database entries
- **Input Validation**: All tool parameters are validated against injection patterns and scope restrictions
- **Private-IP-Only**: Default policy blocks scanning of public IP addresses
- **Scope Enforcement**: Optional `--scope-file` restricts targets to explicitly allowed CIDRs/hosts
- **Supply Chain**: Dependencies locked with hashes via `pip-compile`, audited with `pip-audit`
- **Container Security**: Docker images scanned with Trivy, containers run with `no-new-privileges`
- **API Security**: API binds to `127.0.0.1` by default, remote access requires API key

## Deprecation Policy

Deprecated features are announced 2 minor versions before removal:
- **Deprecated**: Feature marked as deprecated, warning logged at startup
- **Warning**: Deprecation warning on each use
- **Removed**: Feature removed in the target version

Migration paths are documented in the CHANGELOG for each deprecation.
