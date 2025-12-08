---
description: "Add next exercise to current section with full pipeline (design → code → specs → demos)"
model: opus
argument-hint: [section] [version]
---

# Extend Exercise: $ARGUMENTS

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

- ❌ Read source code or spec files directly
- ❌ Read skill or reference files
- ❌ Implement code myself
- ❌ Run tests directly

### 4. ALLOWED AGENTS (ONLY THESE)

| Task | Agent |
|------|-------|
| Design vuln | `content-planner` |
| Implement code | `code-author` |
| Run specs/ucsync | `spec-runner` |
| Write specs | `spec-author` |
| Write demos | `demo-author` |
| Edit docs | `docs-author` |
| Final commit | `commit-agent` |
| Complex orchestration | `uc-maintainer` |

---

Think carefully and methodically about how to coordinate this full pipeline: design → code → specs → demos.

Add the next exercise version to the specified section.

## Health Check

!`(cd vulnerabilities/python/flask/confusion/ && docker compose ps 2>/dev/null | head -5 || echo "Docker status unknown")`
!`(cd vulnerabilities/python/flask/confusion/ && uclogs --since 30m 2>/dev/null | grep -c -i error || echo "0 recent errors")`

## Workflow

Use `uc-maintainer` to orchestrate, or follow this sequence:

### Step 1: Design

Delegate to **content-planner**:

- Read section README
- Design: What vuln is fixed from previous? What new vuln introduced?
- Output: Design spec with attack chain, character mapping, business impact

### Step 2: Implement

Delegate to **code-author**:

- Clone previous exercise directory
- Implement design spec
- Add @unsafe annotations
- Maintain backward compatibility (unless README says otherwise)

### Step 3: Specs

1. **spec-runner**: Update spec.yml with new version, run ucsync
2. **spec-author**: Create specs for new endpoints/behavior
3. **spec-runner**: Run uctest until green

### Step 4: Demos

Delegate to **demo-author**:

- Create .exploit.http (demonstrates vuln)
- Create .fixed.http (shows fix works)
- Follow character rules (see spongebob-characters skill)
- ONE assert per test

### Step 5: Docs

1. `uv run docs generate --target [path]`
2. **docs-author**: Polish README if needed

### Step 6: Finalize

Delegate to **commit-agent**:

- Run full verification
- Commit with descriptive message

## Quality Checks

Before completing, verify:

- [ ] Section README describes this exercise's goals?
- [ ] ONE new concept only?
- [ ] Vuln is exploitable, fix works?
- [ ] Specs inherit maximally from previous version?
- [ ] Character logic sound in demos?
- [ ] Business impact clear and varied?
