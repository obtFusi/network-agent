---
name: pr
description: Pull Request Workflow - erstellt PR, wartet auf CI, merged. Trigger: "erstelle PR", "create PR", "merge this"
---

# PR SKILL

**Auto-activates when user says:** "erstelle PR", "create PR", "merge this", "PR erstellen"

**Your task:** Execute the complete PR workflow from current changes to merged main.

---

## WORKFLOW

### Step 1: Prepare Branch
```bash
# Check current branch
git branch --show-current

# If on main, create feature branch
git checkout -b feature/<name>

# Stage and commit
git add <files>
git commit -m "feat: ..."
```

### Step 2: Local CI (MANDATORY)
```bash
act push
```
Runs all 4 required jobs: `lint`, `test`, `security`, `docker`
- **If ANY job fails:** STOP and report errors
- **Do NOT proceed** without green local CI

### Step 3: Push & Create PR
```bash
git push -u origin <branch>
gh pr create --title "..." --body "..."
```

PR body template:
```markdown
## Summary
- Change 1
- Change 2

## Test Plan
- [x] Local CI passed (lint, test, security, docker)
- [ ] Manual testing

Closes #N
```

### Step 4: Wait for GitHub Actions
```bash
gh pr checks <number>
```
- Poll every 15 seconds until complete
- If failed: Report and STOP

### Step 5: Update Issues
For each linked issue:
```bash
gh issue edit <number> --body "..."  # Check boxes
```

### Step 6: Merge
```bash
gh pr merge <number> --merge --delete-branch --auto
git checkout main && git pull
```

---

## OUTPUT FORMAT

Report each step:
```
[1/6] Branch: feature/xyz
[2/6] Local CI: lint, docker
[3/6] PR: https://github.com/.../pull/N
[4/6] GitHub Actions: all passed
[5/6] Issues: #N updated
[6/6] Merged: main @ abc1234
```

---

## ERROR HANDLING

- On ANY failure: Stop, report error, suggest fix
- Never skip steps
- Never merge with failing checks
