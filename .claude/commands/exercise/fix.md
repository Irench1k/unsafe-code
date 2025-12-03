---
description: "Implement exercises using TDD: failing tests → fix code → verify"
model: opus
argument-hint: [section] [exercise-range|all]
---

# Fix Exercises: $ARGUMENTS

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
- [ ] `httpyac file.http -a --all` passes

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
# Demo tests
httpyac http/e01/e01_*.exploit.http -a --all  # expect FAIL
httpyac http/e01/e01_*.fixed.http -a --all    # expect FAIL

# E2E specs
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
httpyac http/eXX/*.http -a --all
uctest vXXX/
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
