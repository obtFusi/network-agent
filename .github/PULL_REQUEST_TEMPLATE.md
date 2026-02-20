## Summary
<!-- Brief description of changes (1-3 bullet points) -->

-

Closes #<!-- issue number -->

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature causing existing functionality to change)
- [ ] Documentation update
- [ ] CI/CD change
- [ ] Dependency update

## Evidence
### Test Results
| Test | Command | Result |
|------|---------|--------|
| Lint | `ruff format --check . && ruff check .` | pass/fail |
| Unit Tests | `pytest --cov=agent --cov=tools` | pass/fail |
| Docker Build | `docker build -t network-agent:test .` | pass/fail |
| Manual Test | (describe what was tested) | pass/fail |

### NOT Tested
<!-- What was NOT tested and why? Be honest! -->
-

## Checklist
- [ ] CHANGELOG.md updated (if user-facing change)
- [ ] README.md updated (if needed)
- [ ] Version bumped in cli.py (if release-worthy)
- [ ] No secrets/credentials committed
- [ ] Local CI passed (`act push`)
