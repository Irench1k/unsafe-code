---
description: "Improve demo quality via blessed demo agents - orchestrator only"
model: opus
argument-hint: [section|path]
---

# Improve Demos: $ARGUMENTS

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
| `code-reviewer` | ❌ Use project agents instead |

### 3. I AM A DUMB ROUTER

**My ONLY job is to delegate to project agents.** I do NOT:

- ❌ Read `.http` files
- ❌ Read skill files (`.claude/skills/`)
- ❌ Read reference files (`.claude/references/`)
- ❌ Analyze code or syntax
- ❌ Run bash commands (except trivial `ls`)
- ❌ Make decisions about HOW to fix things
- ❌ Create anonymous subagents via Task tool

### 4. ALLOWED AGENTS (ONLY THESE)

| Task | Agent | How to Spawn |
|------|-------|--------------|
| Analyze demos | `demo-debugger` | `Task(subagent_type="demo-debugger")` |
| Fix demos | `demo-author` | `Task(subagent_type="demo-author")` |
| Fix source code | `code-author` | `Task(subagent_type="code-author")` |

**If the task doesn't fit these agents → STOP and tell the user.**

---

## ⛔ I DO NOT EDIT .HTTP FILES DIRECTLY ⛔

I am an **orchestrator**. I delegate ALL `.http` work to specialized agents.

See `.claude/CLAUDE.md` for the .HTTP FILE RESTRICTION policy.

**I MUST NOT:**
- Read `.http` files and interpret their syntax
- Propose specific assertion changes
- Make assumptions about httpyac syntax
- Analyze demo quality directly

**I MUST:**
- Delegate analysis to demo-debugger FIRST
- Delegate fixes to demo-author based on debugger's report
- Verify changes don't increase file verbosity

---

## My Workflow

### Step 1: Identify Scope

Find demo files in target section/path:
- `vulnerabilities/python/flask/confusion/webapp/rNN_*/http/` directories
- Files: `*.exploit.http`, `*.fixed.http`

### Step 2: Delegate Analysis (MANDATORY FIRST STEP)

**ALWAYS** spawn **demo-debugger** BEFORE any fixes:
- Run demos with `httpyac -a --bail`
- Identify syntax errors, assertion failures, quality issues
- Assess existing demo quality (good voice/narrative to preserve?)
- Report console.info count per file
- Classify each issue by type

### Step 3: Delegate Fixes

Based on demo-debugger's analysis, spawn the appropriate agent:

| Issue Type | Agent | What They Do |
|------------|-------|--------------|
| Demo syntax error | demo-author | Fix .http syntax |
| Assertion incorrect | demo-author | Fix assertion |
| Missing cookie handling | demo-author | Add refreshCookie pattern |
| Narrative unclear | demo-author | Improve comments/flow |
| Magic numbers | demo-author | Add named variables |
| Missing console.info | demo-author | Add state visibility |
| Missing state reset | demo-author | Add /e2e/balance call |
| Vulnerability not implemented | code-author | Implement vuln in source |
| Fix not implemented | code-author | Implement fix in source |

### Step 4: Verify

Spawn **demo-debugger** to re-run and confirm fixes.

### Step 5: Repeat Until Complete

Continue the analyze → fix → verify cycle until all demos pass.

---

## What "Improve" Means

### HIGH Priority (always do these)

1. **console.info() for state transitions**
   - Show balance before/after exploit
   - Make hidden variable values visible
   - Help students understand what's happening

2. **Named variables for magic numbers**
   - `@kelp_shake = 6` instead of `"item_id": "6"`
   - Self-documenting demos

3. **State reset for idempotency**
   - Add `/e2e/balance` call at demo start
   - Demos must be replayable

4. **Migrate to refreshCookie() pattern**
   - Remove `@no-cookie-jar` annotations
   - Use explicit cookie passing

5. **Simplify assertions**
   - Prefer `?? body field == value` over `?? js response.parsedBody.field == value`
   - One key assertion per request

### Take Ownership

If demos are broken due to:
- **Missing vulnerability implementation** → Spawn code-author to implement
- **Missing fix implementation** → Spawn code-author to implement
- **Incorrect draft content** → Spawn demo-author to rewrite

**DO NOT** use "it was probably meant to be this way" as an excuse.
**DO** fix whatever is wrong.

---

## What I Am NOT Allowed To Do

- ❌ Read `.http` files and interpret their syntax
- ❌ Propose specific assertion changes
- ❌ Make assumptions about httpyac syntax
- ❌ Edit `.http` files directly
- ❌ Analyze why demos are failing (delegate to demo-debugger)
- ❌ Skip the demo-debugger step and go straight to demo-author

These are handled **ONLY** by demo-author through demo-debugger's analysis.

---

## Delegation Protocol

When spawning demo-debugger:
```
Analyze demos in: [path]
Run with: httpyac -a --bail
Report:
  - Each failure with classification
  - Existing console.info count per file
  - Assessment of existing quality (preserve or rewrite?)
```

When spawning demo-author:
```
Context: [what demo-debugger found]
Task: [specific fix needed]
File: [exact path]
Expected: [what the demo should do]
Style: Follow .claude/references/demo-style-philosophy.md
Preserve: [list any good existing content to keep]
```

When spawning code-author:
```
Context: Demo requires feature that's not implemented
Task: Implement [vulnerability|fix] in [version]
Source: [demo file showing expected behavior]
```

---

## ⚠️ CRITICAL: Style Philosophy

Before delegating ANY changes, ensure agents understand:
1. **MINIMIZE** - Changes should make files simpler, not more complex
2. **CLEAN SYNTAX** - Use `GET /path` not `GET {{host}}/path`
3. **SIMPLEST ASSERTIONS** - Only assert what demonstrates the vuln

See `.claude/references/demo-style-philosophy.md` for full principles.

## Validation Step (REQUIRED)

After demo-author makes changes, **spawn demo-debugger again** to verify:
- [ ] All demos pass `httpyac -a --bail`
- [ ] File line count did NOT increase significantly
- [ ] console.info count ≤ 3 per file
- [ ] Post-request ordering is correct (session → vars → asserts → logs)
- [ ] No unnecessary `{{host}}/` prefixes were added
- [ ] Assertions use simplest syntax
- [ ] Existing quality was preserved (not unnecessarily rewritten)

**If validation fails:** Reject changes and have demo-author retry with specific feedback.

## Success Criteria

After improvements:
- [ ] All demos pass `httpyac -a --bail`
- [ ] State transitions have console.info()
- [ ] Magic numbers replaced with named variables
- [ ] Demos are idempotent (state reset at start)
- [ ] Cookie handling uses refreshCookie() pattern
- [ ] Assertions are simple and educational
- [ ] Files are NOT more verbose than before
