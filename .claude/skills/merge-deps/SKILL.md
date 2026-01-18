---
name: merge-deps
description: Dependabot PR Merge - prüft und merged alle Dependabot PRs. Trigger: "merge dependabot", "update deps", "merge deps"
---

# MERGE-DEPS SKILL

**Auto-activates when user says:** "merge dependabot", "update deps", "merge deps", "dependency updates"

**Your task:** Check and merge all open Dependabot PRs with passing CI.

---

## WORKFLOW

### Step 1: List Dependabot PRs
```bash
gh pr list --author "app/dependabot"
```
- If no PRs: Report "No Dependabot PRs pending" and exit

### Step 2: Check Each PR
For each PR:
```bash
gh pr checks <number>
```

Categorize:
- ✅ Ready: All checks passed
- ⏳ Pending: Checks still running
- ❌ Failed: One or more checks failed

### Step 3: Merge Ready PRs
For each ready PR:
```bash
gh pr merge <number> --merge --delete-branch --auto
```

### Step 4: Sync Local
```bash
git checkout main
git pull
```

---

## OUTPUT FORMAT

```
Dependabot PRs: 3 found

#6 actions/checkout v4 → v6
   Checks: ✅ lint, ✅ test, ✅ security, ✅ docker
   Status: MERGED

#7 github/codeql-action v3 → v4
   Checks: ❌ test (failed)
   Status: SKIPPED - CI failed

#8 actions/setup-python v5 → v6
   Checks: ⏳ pending
   Status: SKIPPED - checks not complete

Summary: 1 merged, 2 skipped
Local main synced to abc1234
```

---

## RULES

- Only merge PRs with ALL checks passing
- Skip pending PRs (user can retry later)
- Skip failed PRs (report which check failed)
- Never force-merge or bypass CI
