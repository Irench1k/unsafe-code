---
description: "Review and fix exercises: validate specs, demos, code using TDD"
model: opus
argument-hint: [section] [exercise-range|all]
---

# Review Exercises: $ARGUMENTS

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
- ❌ Review demos directly (delegate to demo-debugger)

### 4. ALLOWED AGENTS (ONLY THESE)

| Task | Agent |
|------|-------|
| Run specs | `spec-runner` |
| Debug failures | `spec-debugger` |
| Fix specs | `spec-author` |
| Review demos | `demo-debugger` |
| Fix demos | `demo-author` |
| Fix source code | `code-author` |

---

Review AND fix exercises. Use TDD approach.

## Parse Arguments

- **Section**: First word (e.g., `r02`, `r03`)
- **Range**: Second word (e.g., `e01-e07`, `e07`, `all`)
- **Path**: `vulnerabilities/python/flask/confusion/webapp/{section}_*/`

## Health Check

!`(cd vulnerabilities/python/flask/confusion/ && uclogs --since 30m 2>/dev/null | grep -c -i error || echo "0 recent errors")`

## Definition of Done (Per Exercise)

- [ ] Source code implements vuln correctly
- [ ] Source code fixes previous vuln
- [ ] `.exploit.http` demonstrates vuln
- [ ] `.fixed.http` demonstrates previous fix
- [ ] `vuln-*.http` spec tests vuln
- [ ] `vXXX.http` spec tests fix
- [ ] httpyac demos pass
- [ ] uctest specs pass
- [ ] Inheritance works (ucsync)
- [ ] No server errors
- [ ] No technical jargon in demos
- [ ] Attacker uses own credentials

## Workflow

### 1. Understand Context

- Read section README
- Identify expected vulns and fixes per version
- Note SaaS evolution narrative

### 2. Validate E2E Specs

```bash
uctest {version}/
```

- If failures → delegate to `spec-debugger`
- Check inheritance health
- If broken → investigate source code first (may have accidentally fixed vuln)

### 3. Validate Demos

```bash
httpyac vulnerabilities/.../http/eXX/*.http -a --all
```

- Check character logic
- Verify business impact is clear

### 4. Cross-Reference

- Compare source code between versions
- Ensure documented vulns match actual code
- Verify fixes work

### 5. Report

Summary of:

- Versions reviewed
- Specs passed/failed
- Demo issues
- Inheritance health
- Recommendations

## Agent Delegation

| Task           | Agent         |
| -------------- | ------------- |
| Run specs      | spec-runner   |
| Debug failures | spec-debugger |
| Fix specs      | spec-author   |
| Review demos   | demo-author   |

## Red Flags

- Specs need exclusion → source code bug
- Victim's password in demo → character logic error
- Same impact 3+ times → needs variety
- Technical jargon → should be behavioral
- Multiple concepts → ONE concept rule
