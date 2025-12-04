---
description: "Collaborative scoping for demo work - dialog before execution"
model: opus
argument-hint: [section-or-path]
---

# Scope Demo Work: $ARGUMENTS

## ⚠️ DIALOG FIRST - DO NOT EXECUTE YET ⚠️

This command establishes scope through conversation BEFORE expensive execution.

---

## Step 1: Clarify Requirements

Before any research, ask the user:

1. **What's the goal?**
   - Fix broken demos?
   - Improve quality/clarity?
   - Add new demos?
   - Update for new features?

2. **What specifically needs work?**
   - All demos in section?
   - Specific exercises?
   - Specific issues (cookies, assertions, narrative)?

3. **What's the expected outcome?**
   - All demos pass `httpyac -a`?
   - Better educational impact?
   - Specific changes?

4. **Any constraints?**
   - Characters to use/avoid?
   - Complexity level?
   - Time budget?

**Use `AskUserQuestion` tool** to gather this information interactively.

---

## Step 2: Quick Assessment (Minimal)

Only after clarifying requirements, do **minimal** exploration:

```bash
# Quick file listing - NOT full demo runs
ls vulnerabilities/python/flask/confusion/webapp/$ARGUMENTS/http/*/
```

Use `Explore` agent with `"quick"` thoroughness if needed.

**Avoid:**
- Running all demos
- Deep analysis of .http syntax
- Reading many files

---

## Step 3: Propose Plan

Based on dialog and quick assessment, propose:

1. **Scope** - Exactly which demos, what changes
2. **Approach** - Which agents will be used
3. **Priority** - What to fix first
4. **Risks** - What might break

Present as clear options if multiple approaches exist.

**Get explicit user approval before proceeding.**

---

## Step 4: Execute (Only After Approval)

Once approved, delegate to appropriate command/agent:

| Task | Delegate To |
|------|-------------|
| Improve demos | `/demo/improve $ARGUMENTS` |
| Validate demos | `/demo/validate $ARGUMENTS` |

Or spawn agents directly:
- `demo-debugger` - Analyze issues (read-only)
- `demo-author` - Write/fix demos

**Remember:** Only `demo-debugger` and `demo-author` may touch `.http` files!

---

## Why This Pattern?

**Problem**: `/demo/improve` would immediately start analyzing .http files.

**Solution**: Cheap dialog first, expensive execution only after alignment.

This prevents:
- Wrong priorities (HIGH vs LOW)
- Wasted analysis of demos that don't need work
- Misunderstanding what "improve" means

---

## External AI (Optional)

For research questions:
- `gemini -p "Best practices for educational security demos"` - Research
- `codex exec "Review demo narrative for: ..."` - Large context review
