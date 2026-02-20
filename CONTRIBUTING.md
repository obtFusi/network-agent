# Contributing

Thank you for considering contributing to Network Agent!

## How to Contribute

### Reporting Bugs
- Use the [Bug Report](../../issues/new?template=bug_report.yml) template
- Include steps to reproduce
- Include expected vs actual behavior

### Suggesting Features
- Use the [Feature Request](../../issues/new?template=feature_request.yml) template
- Describe the problem you're trying to solve

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes
4. Run required quality gates:
   - `ruff format --check .` (formatting)
   - `ruff check agent/ tools/ cli.py` (linting)
   - `pytest --cov=agent --cov=tools --cov-report=term-missing` (tests)
   - `docker build -t network-agent:test .` (Docker build)
5. Commit using [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat: add new feature`
   - `fix: resolve bug`
   - `docs: update documentation`
6. Push and create a Pull Request

### Code Style
- Run `ruff format .` before committing
- Follow existing code patterns
- Add tests for new functionality
- Python 3.12+, type hints encouraged

### Commit Messages
We use [Conventional Commits](https://www.conventionalcommits.org/).
Your PR title must follow this format: `type: description`

Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`, `deps`, `security`

### Security
- Never commit secrets, API keys, or credentials
- Use RFC 5737 test IPs (192.0.2.0/24) in tests, not real addresses
- See [SECURITY.md](SECURITY.md) for vulnerability reporting
