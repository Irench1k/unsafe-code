---
description: "Diagnose and fix failing e2e specs with proper code-vs-test analysis"
model: opus
argument-hint: [version-or-path]
---

# Fix Failing Specs: $ARGUMENTS

---

## ⛔⛔⛔ CRITICAL RESTRICTIONS - READ FIRST ⛔⛔⛔

### 1. PLAN MODE CHECK

**IF Plan Mode is active → STOP IMMEDIATELY.**

```
ERROR: This command is incompatible with Plan Mode.
Please restart without Plan Mode enabled.
```

### 2. BUILT-IN AGENTS ARE BANNED

**I MUST NEVER spawn these built-in subagent types:**

| Banned Agent | Why |
|--------------|-----|
| `Explore` | ❌ Bypasses our specialized agents |
| `Plan` | ❌ Interferes with command workflow |
| `general-purpose` | ❌ No domain skills |

### 3. I AM A DUMB ROUTER

**My ONLY job is to delegate to project agents.** I do NOT:

- ❌ Read `.http` spec files directly
- ❌ Read skill or reference files
- ❌ Diagnose failures myself
- ❌ Run uctest or bash commands directly

### 4. ALLOWED AGENTS (ONLY THESE)

| Task | Agent |
|------|-------|
| Run tests | `spec-runner` |
| Diagnose failures | `spec-debugger` |
| Fix spec files | `spec-author` |
| Fix source code | `code-author` |
| Manage inheritance | `spec-runner` (ucsync) |

---

Analyze deeply before acting. Consider all possible root causes before concluding on a diagnosis.

Diagnose and fix failing e2e specs for the specified version(s) or path.

## Server Health Check

!`(cd vulnerabilities/python/flask/confusion/ && uclogs --since 10m 2>/dev/null | grep -Ei "error|exception" | head -10 || echo "No recent errors")`

## Key Decision

**If inherited test fails → CODE IS SUSPECT (not the test)**

Unless README explicitly documents behavior change.

## Required Context

Load these files before proceeding:

- [AGENTS.md](AGENTS.md) - Invariants, especially "inherited test fails → code suspect"
- [docs/ai/decision-trees.md](docs/ai/decision-trees.md) - Diagnosis flow charts

## Workflow

### Step 1: Run Tests

Delegate to **spec-runner**:

```bash
uctest $ARGUMENTS
```

If all pass → Done!

### Step 2: Diagnose Failures

Delegate to **spec-debugger** with the failure output.

For each failure, classify:

| Error Type                     | Likely Cause          | Fix Agent                           |
| ------------------------------ | --------------------- | ----------------------------------- |
| "ref X not found"              | Import chain or scope | spec-runner (ucsync) or spec-author |
| Assertion mismatch (inherited) | Code regression       | code-author                         |
| Assertion mismatch (new test)  | Wrong assertion       | spec-author                         |
| Vuln test passes unexpectedly  | Test too weak         | spec-author                         |
| Vuln test fails unexpectedly   | Accidentally fixed    | Add exclusion via spec-runner       |

### Step 3: Apply Fixes

Based on diagnosis:

**If code issue:**

- code-author fixes source to match intended behavior
- Compare to README and previous version

**If spec issue:**

- spec-author adjusts test
- Verify against README intent

**If inheritance issue:**

- spec-runner runs ucsync, updates spec.yml
- Check import chains

### Step 4: Verify

Delegate to **spec-runner**:

- Re-run failed tests
- If still failing, return to Step 2

### Step 5: Broader Verification

Once targeted tests pass:

```bash
uctest $VERSION/  # Full version
```

Ensure no regressions.

## Special Cases

### "ref X not found"

1. Try tag-based execution: `uctest @tag vNNN/`
2. If works → path scope too narrow
3. If still fails → check import chain with spec-debugger

### Vuln Accidentally Fixed

When refactoring accidentally fixes a vulnerability:

1. Verify vuln is actually fixed (run exploit manually)
2. Add exclusion to spec.yml
3. Document WHY in comment

### Multiple Versions Affected

If fix should propagate:

1. Fix in base version
2. Run ucsync
3. Verify inheritance chain: `uctest v201 v202 v203 ...`

## Anti-Patterns to Avoid

- ❌ Immediately "fixing" inherited tests without investigating code
- ❌ Weakening assertions to make tests pass
- ❌ Adding exclusions without understanding why test fails
- ❌ Editing ~ prefixed files directly (run ucsync instead)
