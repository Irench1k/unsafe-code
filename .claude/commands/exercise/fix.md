---
description: "Implement exercises using TDD: failing tests → fix code → verify"
model: opus
argument-hint: [section] [exercise-range|all]
---

# Fix Exercises: $ARGUMENTS

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

- ❌ Read source code or test files directly
- ❌ Read skill or reference files
- ❌ Run tests directly (delegate to spec-runner)
- ❌ Fix code myself (delegate to code-author)

### 4. ALLOWED AGENTS (ONLY THESE)

| Task | Agent |
|------|-------|
| Write demos | `demo-author` |
| Write specs | `spec-author` |
| Run specs/ucsync | `spec-runner` |
| Debug failures | `spec-debugger` |
| Implement vuln code | `code-author` |
| Final commit | `commit-agent` |

---

TDD workflow for exercise implementation. Tests fail first, then code fixes them.

## Parse Arguments

- **Section**: First word (e.g., `r02`, `r03`)
- **Range**: Second word (e.g., `e01-e03`, `e07`, `all`)
- **Path**: `vulnerabilities/python/flask/confusion/webapp/{section}_*/`

## Health Check

!`(cd vulnerabilities/python/flask/confusion/ && uclogs --since 30m 2>/dev/null | grep -c -i error || echo "0 recent errors")`

## Definition of Done (Per Exercise)

**Source Code**:

- [ ] Vulnerability implemented (matches README)
- [ ] Previous vuln fixed
- [ ] `@unsafe` annotations on vulnerable code

**Demos** (`http/eXX/`):

- [ ] `.exploit.http` demonstrates vuln
- [ ] `.fixed.http` shows previous fix works
- [ ] Assertions catch regressions
- [ ] `ucdemo` passes for all demos

**Specs** (`spec/vXXX/`):

- [ ] `vuln-*.http` tests current vuln
- [ ] `vXXX.http` tests previous fix
- [ ] Inheritance works (ucsync → ~vXXX.http)

## TDD Workflow

### 1. Understand

Read section README. Identify:

- What vuln SHOULD exist?
- What previous vuln SHOULD be fixed?
- What endpoints involved?

### 2. Write Failing Tests

```bash
# Demo tests (use ucdemo)
ucdemo r03/e01  # expect FAIL initially

# E2E specs (use uctest)
uctest v301/endpoint/vuln-*.http              # expect FAIL
uctest v302/endpoint/v302.http                # expect FAIL
```

**If tests pass immediately → they're testing the WRONG thing!**

### 3. Implement Vulnerability

1. Find route handlers (`routes/`)
2. Introduce intentional vuln
3. Add `@unsafe` annotation
4. Run `.exploit.http` → should PASS
5. Run `vuln-*.http` → should PASS

### 4. Fix Previous Vulnerability

1. Patch previous exercise's vuln
2. Run `.fixed.http` → should PASS
3. Run `vXXX.http` → should PASS
4. Run previous `vuln-*.http` → should FAIL (vuln gone)

### 5. Verify Inheritance

```bash
ucsync
uctest vXXX+1/  # inherited ~vXXX.http should pass
```

### 6. Final Validation

```bash
ucdemo r03/eXX              # Run all demos for exercise
uctest vXXX/                # Run all specs for version
uclogs --since 30m | grep -i error
```

## Agent Delegation

| Task                | Agent         |
| ------------------- | ------------- |
| Write demos         | demo-author   |
| Write specs         | spec-author   |
| Run specs/ucsync    | spec-runner   |
| Debug failures      | spec-debugger |
| Implement vuln code | code-author   |
| Commit              | commit-agent  |

## Pitfalls

❌ Tests pass against broken code (wrong assertions)
❌ Attacker uses victim's credentials
❌ Technical jargon in demos
❌ Skip inheritance testing
❌ Commit without full validation

## File Structure

```
r{NN}_{category}/
├── README.md           # Vuln descriptions
├── v{XXX}/             # Source code
│   └── routes/
├── http/               # Demos
│   └── e{XX}/
│       ├── *.exploit.http
│       └── *.fixed.http
└── spec/               # E2E specs
    └── v{XXX}/
        └── endpoint/
```
