---
description: "Comprehensive review and fix of Unsafe Code Lab exercises - validates and implements code, specs, and demos using TDD"
model: opus
argument-hint: [section] [exercise-range|all]
---

# Review Exercises: $ARGUMENTS

Think carefully and methodically about how to coordinate this multi-step review and fix process.

**This command**: Thoroughly review AND FIX the specified exercises using Test-Driven Development.

**Arguments**: `[section] [exercise-range]` or `[section] in [path/to/http/]`
- Examples: `r03 e01-e07`, `r03 in vulnerabilities/python/flask/confusion/webapp/r03_authorization_confusion/http/`

**For NEW command** that only implements (doesn't review): Use `/fix-exercises` instead.

**Scope**: This command IMPLEMENTS fixes, not just reviews. Use TDD approach.

## Health Check
!`docker compose ps 2>/dev/null | head -5 || echo "Docker status unknown"`
!`uclogs --since 30m 2>/dev/null | grep -c -i error || echo "0 recent errors"`

## Required Context

Load these files before proceeding:
- [AGENTS.md](AGENTS.md) - Single source of truth for invariants
- [docs/ai/runbooks.md](docs/ai/runbooks.md) - Workflow checklists
- Section README based on $ARGUMENTS (e.g., `r03_authorization_confusion/README.md`)

## Definition of Done

For each exercise, ALL must be complete:
- [ ] Source code implements vulnerability correctly
- [ ] Source code fixes previous vulnerability
- [ ] `.exploit.http` works and demonstrates vuln
- [ ] `.fixed.http` works and demonstrates previous fix
- [ ] `vuln-*.http` e2e spec tests vulnerability
- [ ] `vXXX.http` e2e spec tests previous fix
- [ ] All httpyac demos pass with correct assertions
- [ ] All uctest specs pass
- [ ] Inheritance works (ucsync + test)
- [ ] No server errors in uclogs
- [ ] No technical jargon in demos
- [ ] Character logic correct (attacker uses own credentials)

## Workflow

### Step 1: Understand Context
- Read the section README (e.g., `vulnerabilities/.../r03_authorization_confusion/README.md`)
- Identify which vulnerabilities and fixes are expected in each version
- Note the natural SaaS evolution narrative

### Step 2: Validate E2E Specs
- Run `uctest {version}/` for each version specified
- If tests fail, delegate to `uc-spec-debugger` for diagnosis
- Check inheritance health: most specs should inherit from previous version
- If inheritance is broken, investigate source code first (refactoring may have accidentally fixed vulns)

### Step 3: Validate Interactive Demos
- Check `vulnerabilities/.../http/eXX/` directories
- Each exercise has `.exploit.http` (demonstrates vuln) and `.fixed.http` (shows fix works)
- Run demos with `httpyac {file}.http -a`
- Verify: Character logic sound? Business impact clear? Fun without being cringe?

### Step 4: Cross-Reference
- Compare source code changes between versions (`diff -r eXX eXX+1`)
- Ensure documented vulnerabilities match actual code
- Verify fixes actually fix the vulnerability
- Check that new features follow natural evolution

### Step 5: Report
Provide structured summary:
- Versions reviewed
- Specs passed/failed
- Demos validated/issues found
- Inheritance health
- Recommendations

## Agent Delegation

| Task | Delegate To |
|------|-------------|
| Run e2e specs | uc-spec-runner |
| Diagnose spec failures | uc-spec-debugger |
| Fix spec test code | uc-spec-author |
| Manage inheritance | uc-spec-sync |
| Review demo quality | uc-docs-editor |

## Red Flags to Watch For

- Specs that need to be excluded (usually means source code bug)
- Interactive demos using victim's password (character logic error)
- Same business impact repeated 3+ times (needs variety)
- Technical jargon in demo annotations (should be behavioral)
- Multiple new concepts in single example (violates ONE concept rule)
