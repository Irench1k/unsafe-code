# Unsafe Code Lab: Orchestration Guide

> **Mission**: Educational security content with intentionally vulnerable code. Vulnerabilities are features, not bugs.

---

## ⛔ .HTTP FILE RESTRICTION - READ THIS FIRST ⛔

**.http files require specialized agents.** No orchestrator, command runner, or general agent may:
- Edit `.http` files directly
- Analyze `.http` syntax or assertions
- Propose changes to `.http` files
- Make assumptions about `.http` syntax

### Blessed Agents ONLY

| File Pattern | Analyze | Edit | Agent |
|--------------|---------|------|-------|
| `spec/**/*.http` | spec-debugger | spec-author | E2E specs |
| `vulnerabilities/**/*.http` | demo-debugger | demo-author | Interactive demos |

### What To Do Instead

If you encounter `.http` files or need to work with them:
1. **STOP** - Do not analyze or edit
2. **IDENTIFY** - Is it `spec/` (E2E) or `vulnerabilities/` (demo)?
3. **DELEGATE** - Spawn the appropriate debugger agent to analyze
4. **TRUST** - Let the specialized agent handle syntax

### Why This Matters

httpyac/uctest `.http` syntax has counterintuitive rules that LLMs consistently get wrong:
- ❌ `== "value"` causes SYNTAX ERROR (no quotes on RHS!)
- ❌ `?? js expr` without operator becomes request body → 500 error
- ❌ Assuming cookie handling works like browsers

The blessed agents load `http-syntax` and `http-gotchas` skills that prevent these mistakes.

---

## Health Check
```bash
uclogs --since 30m | grep -c error  # Any recent errors?
```

## Commands

### Exercise Workflow
| Command | Purpose |
|---------|---------|
| `/exercise/scope r03 e01-e03` | **Dialog first** - clarify before execution |
| `/exercise/brainstorm "idea"` | New vulnerability ideation |
| `/exercise/extend r03 v308` | Add next exercise |
| `/exercise/fix r03 e01-e07` | Implement with TDD |
| `/exercise/review r03 all` | Review and fix |

### Spec Workflow
| Command | Purpose |
|---------|---------|
| `/spec/scope v301/` | **Dialog first** - clarify before execution |
| `/spec/run v301/` | Run specs |
| `/spec/fix v301/` | Debug failures |
| `/spec/inheritance v302` | Check inheritance health |
| `/spec/maximize v201` | Backport specs |

### Demo Workflow
| Command | Purpose |
|---------|---------|
| `/demo/scope r02` | **Dialog first** - clarify before execution |
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

## Delegation Philosophy

**Maximize delegation.** The main session should orchestrate, not execute:

### Subagent Delegation
- Use **specialized agents** for their domains (see Agent Routing above)
- Spawn agents **in parallel** when tasks are independent
- Keep context fresh by isolating work in subagents

### External AI Delegation
For tasks beyond the codebase or needing external knowledge:

| Tool | Use Case | Example |
|------|----------|---------|
| `gemini -p "..."` | Web research, best practices | `gemini -p "Real-world examples of auth confusion"` |
| `codex exec "..."` | Large context analysis, verification | `codex exec "Analyze spec inheritance in: ..."` |

### When to Use `/*/scope` Commands
Use scope commands when:
- Task is vague or has multiple interpretations
- You want to clarify before expensive execution
- There are trade-offs to discuss

Pattern: `/demo/scope r02` → dialog → approval → `/demo/improve r02`
