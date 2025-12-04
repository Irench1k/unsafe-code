---
description: "Collaborative scoping for exercise work - dialog before execution"
model: opus
argument-hint: [section] [exercise-range|idea]
---

# Scope Exercise Work: $ARGUMENTS

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
cat vulnerabilities/python/flask/confusion/webapp/$SECTION*/README.md | head -50
```

Use `Explore` agent with `"quick"` thoroughness if needed.

**Avoid:**
- Running full test suites
- Deep code analysis
- Reading all exercise files

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
