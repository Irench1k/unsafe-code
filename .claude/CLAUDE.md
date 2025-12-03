# Unsafe Code Lab: Orchestration Guide

> **Mission**: Educational security content with intentionally vulnerable code. Vulnerabilities are features, not bugs.

## Health Check
```bash
uclogs --since 30m | grep -c error  # Any recent errors?
```

## Commands

### Exercise Workflow
| Command | Purpose |
|---------|---------|
| `/exercise/brainstorm "idea"` | New vulnerability ideation |
| `/exercise/extend r03 v308` | Add next exercise |
| `/exercise/fix r03 e01-e07` | Implement with TDD |
| `/exercise/review r03 all` | Review and fix |

### Spec Workflow
| Command | Purpose |
|---------|---------|
| `/spec/run v301/` | Run specs |
| `/spec/fix v301/` | Debug failures |
| `/spec/inheritance v302` | Check inheritance health |
| `/spec/maximize v201` | Backport specs |

### Demo Workflow
| Command | Purpose |
|---------|---------|
| `/demo/validate e01` | Check demo quality |
| `/demo/improve r02` | Enhance demos (assertions, state, clarity) |

### Meta
| Command | Purpose |
|---------|---------|
| `/meta/health v301` | Quick verification |
| `/meta/context` | Dump current state |
| `/meta/align` | Improve .claude/ config based on feedback |

## Command Sequences

| Workflow | Sequence |
|----------|----------|
| **Fix then verify** | `/spec/fix v301` → `/meta/health v301` |
| **Add exercise** | `/exercise/brainstorm "idea"` → `/exercise/extend r03 v308` |
| **Full review** | `/exercise/review r03 all` → `/meta/health v301...` |
| **Improve demos** | `/demo/improve r02` → `/demo/validate r02` |
| **Config feedback** | `/meta/align` after frustrating interaction |

## Agent Routing

| Task | Agent |
|------|-------|
| Review exercises | uc-maintainer |
| Run/sync specs | spec-runner |
| Debug spec failures | spec-debugger |
| Write/fix specs | spec-author |
| Write/fix demos | demo-author |
| Debug demos | demo-debugger |
| Implement vuln code | code-author |
| Design vulns | content-planner |
| Edit docs | docs-author |
| Commit | commit-agent |

## Spec vs Demo

| Aspect | Spec (`spec/**/*.http`) | Demo (`http/**/*.http`) |
|--------|-------------------------|-------------------------|
| Runner | uctest | httpyac |
| Response | `$(response).field()` | `response.parsedBody.field` |
| Auth | `auth.basic()` helpers | Raw `Authorization:` header |
| Purpose | Automated testing | Student learning |
| Editor | spec-author | demo-author |

## Key Rules

- **Inherited test fails** → investigate source code first (may have accidentally fixed vuln)
- **Never edit `~` files** → run ucsync instead
- **Attacker uses OWN credentials** → never victim's password
- **ONE concept per exercise** → progressive complexity

## Decision: Fix Code or Fix Test?

| Situation | Action |
|-----------|--------|
| Inherited test fails | Investigate code first |
| New test for new feature | Verify assertion logic |
| Test expects old behavior | Check README for intent |

## Quality Gates

Before delegating:
- [ ] Read section README
- [ ] ONE new concept only
- [ ] Character logic correct
- [ ] Variety in impacts

Red flags:
- SpongeBob as attacker
- Victim's password in exploit
- Technical jargon in demos
- Same impact 4+ times
