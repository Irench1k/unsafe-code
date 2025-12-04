---
name: http-editing-policy
description: "⛔ MANDATORY policy for .http files. Auto-load for ANY agent near .http content. Defines who may read/write .http files."
---

# ⛔ HTTP EDITING POLICY - MANDATORY ⛔

**This skill auto-loads for any agent working near `.http` files.**

---

## Who May Touch `.http` Files

| Agent | May READ | May WRITE | Domain |
|-------|----------|-----------|--------|
| demo-author | ✅ | ✅ | `vulnerabilities/**/*.http` |
| demo-debugger | ✅ | ⚠️ trivial only | `vulnerabilities/**/*.http` |
| spec-author | ✅ | ✅ | `spec/**/*.http` |
| spec-debugger | ✅ | ⚠️ trivial only | `spec/**/*.http` |
| **ALL OTHERS** | ❌ | ❌ | **DELEGATE IMMEDIATELY** |

---

## If You Are Not Listed Above

**STOP. You are NOT authorized to:**
- Read and interpret `.http` file contents
- Propose changes to `.http` assertions
- Make assumptions about `.http` syntax
- Analyze why a demo or spec is failing
- Suggest fixes for `.http` files

**Instead, you MUST:**

1. **Identify the file type:**
   - Path contains `spec/` → E2E spec
   - Path contains `vulnerabilities/` → Demo

2. **Spawn the appropriate debugger:**
   - E2E spec → `spec-debugger`
   - Demo → `demo-debugger`

3. **Let them analyze and delegate:**
   - Debuggers will identify the issue
   - They'll spawn author agents for edits

---

## Why This Restriction Exists

httpyac/uctest `.http` syntax has rules that LLMs **consistently hallucinate wrong**:

| Common Mistake | What Happens | Correct Syntax |
|----------------|--------------|----------------|
| `== "value"` | **SYNTAX ERROR** | `== value` (no quotes!) |
| `?? js expr` (no operator) | Becomes request body, 500 error | `?? js expr == true` |
| Assume auto cookies | Auth confusion, flaky tests | Manual `refreshCookie()` |
| `$(response)` in demos | undefined | `response.parsedBody` |
| `response.parsedBody` in specs | Non-standard | `$(response).field()` |

The blessed agents (demo-author, demo-debugger, spec-author, spec-debugger) load the `http-syntax` and `http-gotchas` skills that contain the correct rules.

**Unauthorized agents do not have this training. Trust the specialists.**

---

## Delegation Examples

### "The demo is failing"
```
DO NOT: Read the .http file and guess what's wrong
DO: Spawn demo-debugger with the file path
```

### "Can you improve this demo?"
```
DO NOT: Read the .http file and propose syntax changes
DO: Spawn demo-debugger to analyze, then demo-author to implement
```

### "The spec assertion is wrong"
```
DO NOT: Edit the .http file
DO: Spawn spec-debugger to diagnose, then spec-author to fix
```

### "Add a new demo for exercise X"
```
DO NOT: Write .http content yourself
DO: Spawn demo-author with the requirements
```

---

## How to Tell Spec from Demo

| Characteristic | E2E Spec | Interactive Demo |
|----------------|----------|------------------|
| Path | `spec/**/*.http` | `vulnerabilities/**/*.http` |
| Runner | uctest | httpyac |
| Response access | `$(response).field()` | `response.parsedBody.field` |
| Auth helpers | `{{auth.basic()}}` | Raw `Authorization:` header |
| Cookie handling | `extractCookie()` / `auth.login()` | `refreshCookie()` |

---

## Summary

1. **You see `.http` file** → Check if you're authorized
2. **Not on the list** → STOP, delegate immediately
3. **Even for "simple" fixes** → Delegate to specialized agent
4. **Trust the specialists** → They have the training you don't

**No exceptions. No "just this once." Delegate.**
