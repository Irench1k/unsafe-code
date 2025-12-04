---
description: "Collaborative scoping for spec work - dialog before execution"
model: opus
argument-hint: [target-version-or-path]
---

# Scope Spec Work: $ARGUMENTS

## ⚠️ DIALOG FIRST - DO NOT EXECUTE YET ⚠️

This command establishes scope through conversation BEFORE expensive execution.

---

## Step 1: Clarify Requirements

Before any research, ask the user:

1. **What's the goal?**
   - Fix failing tests?
   - Add new test coverage?
   - Improve inheritance?
   - Debug specific issue?

2. **What's the expected outcome?**
   - All tests green?
   - Specific behavior verified?
   - Inheritance maximized?

3. **Any constraints?**
   - Time-sensitive?
   - Specific versions only?
   - Avoid touching certain files?

**Use `AskUserQuestion` tool** to gather this information interactively.

---

## Step 2: Quick Assessment (Minimal)

Only after clarifying requirements, do **minimal** exploration:

```bash
# Quick health check - NOT full test run
uctest $ARGUMENTS --dry-run 2>&1 | head -20
ucsync --check 2>&1 | head -10
```

Use `Explore` agent with `"quick"` thoroughness if needed.

**Avoid:**
- Running full test suites
- Deep code analysis
- Reading many files

---

## Step 3: Propose Plan

Based on dialog and quick assessment, propose:

1. **Scope** - Exactly what will be done
2. **Approach** - Which agents will be used
3. **Risks** - What might go wrong
4. **Alternatives** - Other options considered

Present as clear options if multiple approaches exist.

**Get explicit user approval before proceeding.**

---

## Step 4: Execute (Only After Approval)

Once approved, delegate to appropriate command/agent:

| Task | Delegate To |
|------|-------------|
| Run specs | `/spec/run $ARGUMENTS` |
| Fix failures | `/spec/fix $ARGUMENTS` |
| Check inheritance | `/spec/inheritance $ARGUMENTS` |
| Maximize inheritance | `/spec/maximize $ARGUMENTS` |

Or spawn agents directly:
- `spec-runner` - Execute tests
- `spec-debugger` - Diagnose failures
- `spec-author` - Write/fix specs

---

## Why This Pattern?

**Problem**: Expensive commands run immediately, wasting tokens on wrong scope.

**Solution**: Cheap dialog first, expensive execution only after alignment.

This saves:
- Context tokens (no wasted exploration)
- Time (no rework from misunderstanding)
- Frustration (clear expectations)

---

## External AI (Optional)

For complex scoping questions:
- `gemini -p "What are common patterns for: ..."` - Research approaches
- `codex exec "Analyze spec inheritance for: ..."` - Large context analysis
