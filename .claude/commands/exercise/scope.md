---
description: "Collaborative scoping for exercise work - dialog before execution"
model: opus
argument-hint: [section] [exercise-range|idea]
---

# Scope Exercise Work: $ARGUMENTS

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

**My ONLY job is to:**
1. Ask clarifying questions (via `AskUserQuestion`)
2. Delegate to project agents for any analysis
3. Summarize agent reports for the user

**I do NOT:**
- ❌ Read source code or test files
- ❌ Read skill or reference files
- ❌ Analyze anything myself
- ❌ Run tests or bash commands directly

### 4. ALLOWED AGENTS (ONLY THESE)

| Task | Agent |
|------|-------|
| Review exercises | `/exercise/review` → multiple agents |
| Fix exercises | `/exercise/fix` → multiple agents |
| Extend exercises | `/exercise/extend` → multiple agents |
| Design new | `content-planner` |
| Complex orchestration | `uc-maintainer` |

---

## ⚠️ DIALOG FIRST - DO NOT EXECUTE YET ⚠️

This command establishes scope through conversation BEFORE expensive execution.

---

## Step 1: Clarify Requirements

Before any research, ask the user:

1. **What's the goal?**
   - Review existing exercises?
   - Fix broken exercises?
   - Add new exercise?
   - Extend to new version?

2. **What's the scope?**
   - Specific exercises (e01-e03)?
   - Entire section (r02, r03)?
   - Single new exercise?

3. **What's the expected outcome?**
   - All specs/demos passing?
   - New vulnerability implemented?
   - Quality improvements?

4. **Any constraints?**
   - Must follow existing patterns?
   - Specific vulnerability type?
   - Character restrictions?

**Use `AskUserQuestion` tool** to gather this information interactively.

---

## Step 2: Quick Assessment (Minimal)

Only after clarifying requirements, do **minimal** exploration:

```bash
# Quick check - NOT full test runs
ls vulnerabilities/python/flask/confusion/webapp/$SECTION*/
```

**For detailed analysis** → Delegate to `uc-maintainer` or appropriate specialized agent.

**NEVER use built-in `Explore` agent** - it bypasses our specialized agents.

**Avoid:**
- Running full test suites yourself
- Deep code analysis yourself
- Reading all exercise files directly

---

## Step 3: Propose Plan

Based on dialog and quick assessment, propose:

1. **Scope** - Exactly what exercises, what work
2. **Approach** - Which workflow (review/fix/extend/brainstorm)
3. **Agents** - Who will do what
4. **Order** - Sequence of operations
5. **Risks** - What might go wrong

Present as clear options if multiple approaches exist.

**Get explicit user approval before proceeding.**

---

## Step 4: Execute (Only After Approval)

Once approved, delegate to appropriate command:

| Task | Delegate To |
|------|-------------|
| Review exercises | `/exercise/review $ARGUMENTS` |
| Fix exercises (TDD) | `/exercise/fix $ARGUMENTS` |
| Extend to new version | `/exercise/extend $ARGUMENTS` |
| Brainstorm new exercise | `/exercise/brainstorm $ARGUMENTS` |

Or delegate to `uc-maintainer` for complex multi-step workflows.

---

## Why This Pattern?

**Problem**: Exercise commands can trigger expensive multi-agent workflows.

**Solution**: Cheap dialog first establishes:
- What "review" or "fix" means for this context
- Which exercises actually need work
- What order to tackle things

This prevents:
- Running all tests when only one exercise needs work
- Implementing wrong vulnerability
- Misunderstanding section evolution narrative

---

## Agent Routing Reference

| Task | Agent |
|------|-------|
| Design vulnerability | content-planner |
| Implement code | code-author |
| Write specs | spec-author |
| Run specs | spec-runner |
| Debug specs | spec-debugger |
| Write demos | demo-author |
| Debug demos | demo-debugger |
| Edit docs | docs-author |
| Commit | commit-agent |
| Orchestrate complex work | uc-maintainer |

---

## External AI (Optional)

For design questions:
- `gemini -p "Real-world examples of [vulnerability type]"` - Research
- `codex exec "Analyze exercise progression in: ..."` - Large context
