---
name: http-gotchas
description: "⛔ CRITICAL pitfalls for .http files. Auto-invoke when assertions fail unexpectedly, 500 errors after adding assertions, type coercion issues, or quotes-on-RHS problems. MUST READ before editing ANY .http file."
---

# ⛔ HTTP Assertion Gotchas - CRITICAL ⛔

**READ THIS BEFORE EDITING ANY .http FILE.**

These are the mistakes LLMs make repeatedly. Every single one causes real failures.

---

## 🚨 The Big Four - Memorize These

### 1. NO Quotes on Right-Hand Side

The RHS is a **literal**, NOT JavaScript. Quotes become part of the string!

```http
# ✅ CORRECT - no quotes
?? js response.parsedBody.status == approved
?? js response.parsedBody.email == plankton@chum-bucket.sea
?? js $(response).field("status") == pending

# ❌ WRONG - CAUSES SYNTAX ERROR in httpyac!
?? js response.parsedBody.status == "approved"
?? js $(response).field("email") == "plankton@chum-bucket.sea"
```

**Why**: The assertion parser treats RHS as a raw literal. Adding `"quotes"` means you're comparing to the string `"approved"` (with literal quote characters), not `approved`.

**Symptom**: Assertion fails even when values look identical, OR httpyac syntax error.

---

### 2. Operator REQUIRED - Always

Without `== != < > <= >=`, the line becomes **request body** → 500 error!

```http
# ❌ WRONG - becomes body content, causes 500!
?? js response.parsedBody.isValid
?? js $(response).field("active")

# ✅ CORRECT - always use operator
?? js response.parsedBody.isValid == true
?? js $(response).field("active") == true
```

**Why**: The parser needs an operator to know it's an assertion. Without one, it interprets the line as request body content.

**Symptom**: 500 Internal Server Error, malformed request.

---

### 3. Assertions Run AFTER Request - Capture Pre-State First

All `?? js` assertions execute **after** the HTTP request completes. You cannot check pre-state in an assertion.

```http
# ❌ WRONG - both sides are same value (post-request)!
?? js parseFloat(response.parsedBody.balance) > {{parseFloat(response.parsedBody.balance)}}

# ✅ CORRECT - capture pre-state in JS block BEFORE request
{{
  exports.balanceBefore = parseFloat(await user("plankton").balance());
}}
POST /refund
?? js parseFloat(response.parsedBody.balance) > {{balanceBefore}}
```

**Why**: Variable interpolation `{{}}` happens at request time, assertions run after response.

**Symptom**: Comparison always equals, assertion makes no sense.

---

### 4. parseFloat() for Numeric Comparisons

API values are often strings. Use `parseFloat()` for math.

```http
# ❌ WRONG - string comparison
?? js $(response).balance() > 100
# "99.99" > 100 might be true (string comparison)!

# ✅ CORRECT - explicit numeric conversion
?? js parseFloat($(response).balance()) > 100
```

**Why**: JSON numbers may be returned as strings. JavaScript string comparison is lexicographic.

**Symptom**: Unexpected comparison results, especially with decimals.

---

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

---

## Quick Diagnostics

### "500 Internal Server Error" after adding assertion
→ **Missing operator.** Add `== true`, `> 0`, etc.

### "Assertion failed" but values look identical
→ **Quotes on RHS.** Remove them: `== approved` not `== "approved"`
→ Check for whitespace/encoding differences

### "Pre-state equals post-state"
→ **Capture in `{{ }}` block before request**, not in assertion.

### "Numeric comparison wrong"
→ **Wrap both sides in `parseFloat()`**

### "ref X not found"
→ Typo in @name or @ref
→ Missing @name directive
→ Wrong file scope (refs don't cross files)

---

## Pattern Cheatsheet

```http
# Boolean check
?? js $(response).field("active") == true
?? js response.parsedBody.active == true

# String equality (NO QUOTES!)
?? js $(response).field("status") == pending
?? js response.parsedBody.status == approved

# Email with special chars (STILL no quotes!)
?? js $(response).field("email") == plankton@chum-bucket.sea
?? js response.parsedBody.email == sandy@bikinibottom.sea

# Numeric comparison
?? js parseFloat($(response).balance()) > 100
?? js parseFloat(response.parsedBody.balance) > 100

# Compare to captured value
?? js parseFloat($(response).balance()) > {{before}}
?? js parseFloat(response.parsedBody.balance) > {{balanceBefore}}

# Array length
?? js $(response).field("items").length > 0
?? js response.parsedBody.orders.length > 0

# Status checks
?? status == 200
?? js $(response).status() == 200
?? js $(response).isOk() == true
```

---

## Demo vs Spec Syntax Reminder

| Aspect | Demo (httpyac) | Spec (uctest) |
|--------|----------------|---------------|
| Status | `response.status` or `?? status` | `$(response).status()` |
| Field | `response.parsedBody.x` | `$(response).field("x")` |
| Balance | `response.parsedBody.balance` | `$(response).balance()` |
| Auth | Raw `Authorization:` header | `{{auth.basic("user")}}` |

---

## See Also

- `http-syntax` - Full syntax reference
- `spec-conventions` - E2E spec patterns
- `demo-conventions` - Demo patterns
