---
name: http-assertion-gotchas
description: Quick reference for HTTP assertion syntax pitfalls. Auto-invoke when assertions fail unexpectedly, "Expected X but got Y" errors, 500 errors after adding assertions, type coercion/mismatch issues, quotes-on-RHS problems, or pre-state vs post-state confusion. Covers both E2E specs (uctest) and interactive demos (httpyac).
---

# HTTP Assertion Gotchas

Quick reference for common assertion pitfalls that cause mysterious failures.

## The Big Four Gotchas

### 1. Operator REQUIRED

Without `== != < > <= >=`, the line becomes **request body** → 500 error!

```http
# WRONG - no operator, becomes body content!
?? js response.parsedBody.isValid
?? js $(response).field("active")

# CORRECT - always use an operator
?? js response.parsedBody.isValid == true
?? js $(response).field("active") == true
```

**Symptom**: 500 Internal Server Error, malformed request

### 2. NO Quotes on Right Side

The right side is a **literal**, not JavaScript. Quotes become part of the string!

```http
# WRONG - quotes become part of literal
?? js $(response).field("status") == "approved"
# This compares to the string: "approved" (with quotes!)

# CORRECT - no quotes
?? js $(response).field("status") == approved
?? js response.parsedBody.email == plankton@chum-bucket.sea
```

**Symptom**: Assertion fails even when values look identical

### 3. All Assertions Run AFTER Request

Assertions execute **after** the HTTP request completes. You cannot check pre-state in an assertion.

```http
# WRONG - balance is captured AFTER request
?? js parseFloat(response.parsedBody.balance) > {{parseFloat(response.parsedBody.balance)}}
# Both sides are the same value!

# CORRECT - capture pre-state in JS block BEFORE request
{{\n  exports.before = parseFloat(await user("plankton").balance());
}}
POST /refund
?? js parseFloat($(response).balance()) > {{before}}
```

**Symptom**: Comparison always equals, or assertion makes no sense

### 4. String Coercion in Math

API values are often strings. Use `parseFloat()` for numeric comparisons.

```http
# WRONG - string comparison
?? js $(response).balance() > 100
# "99.99" > 100 might be true (string comparison)!

# CORRECT - explicit numeric conversion
?? js parseFloat($(response).balance()) > 100
```

**Symptom**: Unexpected comparison results, especially with decimals

## Execution Order Reference

```
1. File-level {{ }} blocks run (once at load)
2. For each request:
   a. Pre-request {{ }} block runs
   b. HTTP request is sent
   c. Response received
   d. Post-request {{ }} block runs
   e. ALL ?? assertions execute
   f. @variable = captures execute
```

## Syntax Differences: E2E vs Demos

| Aspect | E2E Specs (uctest) | Interactive Demos (httpyac) |
|--------|-------------------|----------------------------|
| Response access | `$(response).field("x")` | `response.parsedBody.x` |
| Status check | `$(response).status()` | `status` |
| Financial | `$(response).balance()` | `response.parsedBody.balance` |
| Auth header | `{{auth.basic("user")}}` | `Basic {{btoa("user:pass")}}` |

## Quick Fixes

### "500 Internal Server Error" after adding assertion
→ Check for missing operator (`== true`, `> 0`, etc.)

### "Assertion failed" but values look same
→ Remove quotes from right side
→ Check for whitespace/encoding differences

### "Pre-state equals post-state"
→ Capture pre-state in `{{ }}` block before request

### "Numeric comparison wrong"
→ Wrap both sides in `parseFloat()`

## Pattern Cheatsheet

```http
# Boolean check
?? js $(response).field("active") == true

# String equality (no quotes!)
?? js $(response).field("status") == pending

# Email with special chars (still no quotes)
?? js $(response).field("email") == plankton@chum-bucket.sea

# Numeric comparison
?? js parseFloat($(response).balance()) > 100

# Compare to captured value
?? js parseFloat($(response).balance()) > {{before}}

# Array length
?? js $(response).field("items").length > 0

# Nested field
?? js $(response).field("order.status") == delivered
```

## See Also

- [Common Gotchas Reference](../../references/common-gotchas.md) - Extended troubleshooting guide
- [http-e2e-specs](../http-e2e-specs/SKILL.md) - Full E2E spec syntax
- [http-interactive-demos](../http-interactive-demos/SKILL.md) - Demo syntax (different helpers!)
