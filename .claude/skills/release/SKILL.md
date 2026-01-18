---
name: release
description: Release Workflow - erstellt Version-Tag und GitHub Release. Trigger: "release", "neue version", "tag erstellen"
---

# RELEASE SKILL

**Auto-activates when user says:** "release", "neue version", "tag erstellen", "publish version"

**Your task:** Create a complete release with version tag and GitHub Release.

---

## INPUT

User provides version as:
- Explicit: `0.4.0` or `v0.4.0`
- Semantic: `patch` (0.3.0 → 0.3.1), `minor` (0.3.0 → 0.4.0), `major` (0.3.0 → 1.0.0)

---

## WORKFLOW

### Step 1: Determine Version
```bash
# Read current version from CHANGELOG
grep -m1 "## \[" CHANGELOG.md
```
Calculate new version based on input.

### Step 2: Verify CHANGELOG
- Check CHANGELOG.md has entry for new version
- **If missing:** STOP and ask user to update CHANGELOG first
- Entry must have: Added, Changed, or Fixed section

### Step 3: Update Version Badge
Edit README.md:
```markdown
[![Version](https://img.shields.io/badge/version-X.Y.Z-blue.svg)](CHANGELOG.md)
```

### Step 4: Update cli.py Version
Edit cli.py:
```python
__version__ = "X.Y.Z"
```

### Step 5: Commit
```bash
git add README.md cli.py
git commit -m "chore: Release vX.Y.Z

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
git push
```

### Step 6: Create & Push Tag
```bash
git tag vX.Y.Z
git push --tags
```

### Step 7: Verify Release
```bash
sleep 10
gh release view vX.Y.Z
```

---

## OUTPUT FORMAT

```
[1/7] Version: 0.3.0 → 0.4.0
[2/7] CHANGELOG: Entry exists
[3/7] README Badge: Updated
[4/7] cli.py: __version__ updated
[5/7] Commit: abc1234
[6/7] Tag: v0.4.0 pushed
[7/7] Release: https://github.com/.../releases/tag/v0.4.0
```

---

## ERROR HANDLING

- Missing CHANGELOG entry → Stop, request update
- Tag already exists → Stop, report conflict
- Release workflow fails → Report, suggest manual check
