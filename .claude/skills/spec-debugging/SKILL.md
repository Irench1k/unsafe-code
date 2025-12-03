---
name: spec-debugging
description: Systematic diagnosis of E2E spec failures in Unsafe Code Lab. Auto-invoke when tests fail, seeing "Expected X but got Y", 500 errors, connection refused, "ref not found", or when uctest reports failures. Provides decision trees for determining whether to fix code or fix test.
---

# E2E Spec Debugging Guide

## When to Use This Skill

- Tests are failing and need diagnosis
- Seeing assertion mismatches ("Expected X but got Y")
- Server returning 500 errors during tests
- "ref not found" errors
- Connection refused or timeout errors
- Deciding whether to fix code or fix test

## When NOT to Use This Skill

- Writing new tests from scratch (use http-e2e-specs)
- Running demos (use http-interactive-demos)
- Managing inheritance (use spec-inheritance)

## The Golden Rule

**If inherited test fails → CODE IS SUSPECT, not the test**

Unless README explicitly documents intentional behavior change.

## Diagnostic Steps

### 1. Check Server Health FIRST

```bash
# Is server running?
docker compose ps

# Recent errors in logs?
uclogs --since 5m | grep -i error

# Specific endpoint issue?
uclogs --since 5m | grep "POST /orders"
```

### 2. Identify Error Type

| Error | Likely Cause | First Check |
|-------|--------------|-------------|
| Assertion mismatch | Wrong value or wrong assertion | Check assertion syntax |
| 500 error | Server bug OR assertion in body | Check uclogs, then assertion placement |
| 401/403 | Auth issue | Check auth helper usage |
| ref not found | Import/scope issue | Check import chain |
| Timeout | Missing seed or slow test | Check for platform.seed() |
| Connection refused | Server not running | Run docker compose up |

### 3. Classify the Test

**Is it inherited?** (~ prefix or from earlier version)
- YES → Investigate source code FIRST
- NO → May be test issue

**Is it testing a vulnerability?** (vuln-*.http)
- YES → Vuln may have been accidentally fixed
- NO → Check for API changes

## Common Error Patterns

### "Expected X but got Y"

**Symptoms**: Assertion fails with value mismatch

**Diagnosis**:
1. Is the assertion using correct syntax? (operator required, no quotes on RHS)
2. Is the value actually wrong, or is the assertion wrong?
3. For inherited tests: Did code change the behavior?

**Fix Path**:
- Wrong syntax → Fix assertion (uc-spec-author)
- Code regression → Fix source code (uc-code-crafter)
- Intentional change → Update test (uc-spec-author)

### 500 Internal Server Error

**Symptoms**: Server returns 500, often with assertion text in response

**Diagnosis**:
1. Check uclogs for the actual error
2. Is there an assertion BEFORE the request completes?
3. Is there a blank line between headers and body?

**Common Cause**: Assertion placed where request body should be

```http
# WRONG - assertion treated as body, sent to server
GET /orders
Authorization: ...

?? status == 200  # This is sent as request body!

# CORRECT - blank line before assertion
GET /orders
Authorization: ...

?? status == 200  # This is an assertion
```

**Fix Path**:
- Assertion placement → Fix test structure (uc-spec-author)
- Actual server bug → Fix source code (uc-code-crafter)

### "ref X not found"

**Symptoms**: Test references a named request that can't be found

**Diagnosis**:
1. Is the referenced test in scope? (path-based execution narrows scope)
2. Is the import chain correct?
3. Is the file excluded in spec.yml?
4. Is it an inherited file that needs regeneration?

**Fix Path**:
- Scope issue → Run with broader path or use tags
- Import missing → Fix import chain (uc-spec-author)
- Exclusion issue → Update spec.yml (uc-spec-sync)
- Stale inheritance → Run ucsync (uc-spec-sync)

### Connection Refused

**Symptoms**: Can't connect to server

**Diagnosis**:
1. Is docker compose running?
2. Is the correct port exposed?
3. Did a previous test crash the server?

**Fix Path**:
```bash
docker compose down && docker compose up -d
```

### Timeout

**Symptoms**: Test hangs or times out

**Diagnosis**:
1. Is there a platform.seed() or platform.reset() call?
2. Is the test waiting for something that won't happen?
3. Is there an infinite loop in the code?

**Fix Path**:
- Missing seed → Add platform.seed() (uc-spec-author)
- Code bug → Debug and fix (uc-code-crafter)

## Decision Tree: Fix Code or Fix Test?

```
Test Fails
    │
    ├─ Is test inherited (~ prefix or from earlier version)?
    │   │
    │   ├─ YES → CODE IS SUSPECT
    │   │        │
    │   │        ├─ Check: Did recent refactoring change behavior?
    │   │        ├─ Check: Was vulnerability accidentally fixed?
    │   │        └─ Fix: Source code to restore intended behavior
    │   │
    │   └─ NO → Could be either
    │
    ├─ Is test for vulnerability (vuln-*.http)?
    │   │
    │   ├─ Test PASSES unexpectedly → Vuln not implemented
    │   └─ Test FAILS unexpectedly → Vuln may be fixed
    │
    └─ Is assertion syntax correct?
        │
        ├─ Missing operator → Fix: ?? field == value
        ├─ Quotes on RHS → Fix: ?? field == literal (no quotes)
        └─ Multiple assertions → Fix: Use && in single ?? js
```

## Verification After Fix

After applying any fix:

```bash
# Run the specific test
uctest path/to/test.http

# Run the full version
uctest v301/

# Check inheritance chain
uctest v301 v302 v303
```

## Agent Handoff Summary

| Diagnosis | Hand Off To |
|-----------|-------------|
| Assertion syntax error | uc-spec-author |
| Import chain broken | uc-spec-author or uc-spec-sync |
| Source code regression | uc-code-crafter |
| Inheritance stale | uc-spec-sync |
| Need to exclude test | uc-spec-sync |
| Server configuration | Manual intervention |

## See Also

- [Common Gotchas Reference](../../references/common-gotchas.md) - Extended troubleshooting patterns
- [http-e2e-specs](../http-e2e-specs/SKILL.md) - Writing specs
- [spec-inheritance](../spec-inheritance/SKILL.md) - Managing inheritance
- [http-assertion-gotchas](../http-assertion-gotchas/SKILL.md) - Assertion syntax
- [uclab-tools](../uclab-tools/SKILL.md) - CLI tool reference
