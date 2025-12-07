---
name: http-syntax
description: Authoritative .http file syntax for specs and demos. Auto-invoke when editing any .http file. MUST be loaded alongside http-gotchas.
---

# HTTP File Syntax Reference

Authoritative syntax for `.http` files used by both **uctest** (E2E specs) and **httpyac** (demos).

## Request Structure

```http
### Request title (required - starts new request)
# @name my_request    # optional: for @ref chains (specs only)
# @tag v301, smoke    # managed by ucsync (specs only)
METHOD /path?query=1
Header-Name: value
Content-Type: application/json

{"body": "here"}

?? js assertion == expected
```

## Critical Structural Rules

| Rule | Correct | Wrong |
|------|---------|-------|
| New request | `###` prefix | Missing → merged with previous |
| Blank line before body | REQUIRED | Missing → body becomes headers |
| Comments | `#` at line start | `//` not supported |
| After HTTP line | Headers only | Comments break parsing |

## Variables

### File-Level Variables
```http
@host = http://localhost:8000/api/v301
@plankton_email = plankton@chum-bucket.sea
```

### @host Auto-Prefix (httpyac)

When `@host` is defined, httpyac **automatically** prefixes all request URLs:

```http
@host = http://localhost:8000/api/v201

### This WORKS - no {{host}} needed!
GET /orders
POST /auth/login
```

❌ **DO NOT** write `GET {{host}}/orders` - it adds visual noise
✅ **DO** write `GET /orders` - cleaner, httpyac handles the prefix

### Computed Variables
```http
@plankton_auth = Basic {{btoa(plankton_email + ":" + plankton_password)}}
```

### Response Capture (via @name)
```http
# @name cart
POST {{host}}/cart
Authorization: {{plankton_auth}}

@cart_id = {{cart.cart_id}}

### Use captured value
POST {{host}}/cart/{{cart_id}}/items
```

## JavaScript Blocks `{{ }}`

```http
{{
  // Runs BEFORE request
  console.info("Starting request...");
  exports.timestamp = Date.now();
}}
POST /endpoint

{{
  // Runs AFTER request (for logging, NOT assertions)
  console.info("Got balance:", response.parsedBody.balance);
}}
```

- Run **before** the HTTP line (setup) or **after** response (logging)
- Auto-await Promises
- Export with `exports.foo = ...`
- Use for seeding, capturing pre-state, logging

**⚠️ Single-line `{{ await ... }}` is interpreted as a URL!** Always use multi-line for statements:
```http
# ❌ WRONG - httpyac interprets this as a URL
{{ await seedBalance("v203", "plankton@chum-bucket.sea", 100); }}

# ✅ CORRECT - multi-line block
{{
  await seedBalance("v203", "plankton@chum-bucket.sea", 100);
}}
```

### ⛔⛔⛔ File-Level vs Request-Level Blocks (CRITICAL) ⛔⛔⛔

httpyac has **TWO types** of `{{ }}` blocks with **COMPLETELY different execution behavior**:

| Block Type | Location | Execution | Use Case |
|------------|----------|-----------|----------|
| **File-level** | Before any `###` | Runs **BEFORE EVERY REQUEST** in file | Export helpers via `@import` |
| **Request-level** | After a `###` | Runs **ONCE** for that request | Setup, capture, logging |

**File-level JS block** (NO `###` before it):
```http
@host = http://localhost:8000/api

{{
  // ⚠️ RUNS BEFORE EVERY REQUEST IN THIS FILE!
  // Use ONLY for: helper exports, pure function definitions
  exports.refreshCookie = (resp) => { ... };
}}
```

**Request-level JS block** (AFTER a `###` line):
```http
### Some Request
{{
  // Runs ONCE, for THIS request only
  // Use for: state capture, seeding, clearing, logging
  exports.someValue = ...;
}}
GET /path
```

**⛔ THE #1 MISTAKE: Putting setup code in file-level blocks!**

```http
# ❌ CATASTROPHICALLY WRONG - clears mailpit before EVERY request!
@host = {{base_host}}/v307

{{
  await mailpit.clear();  // Runs before request 1, 2, 3, 4...
}}

### Step 1: Get token
...

### Step 2: Use token  # ← mailpit.clear() runs AGAIN here, deleting the token!
...
```

```http
# ✅ CORRECT - clears mailpit ONCE at the start
@host = {{base_host}}/v307

### Setup: Clear mailpit
{{
  await mailpit.clear();  // Runs only for this request
}}

### Step 1: Get token
...

### Step 2: Use token  # ← Token is still in mailpit!
...
```

**Key insight:** To share helpers via `@import`, put the `{{ }}` block at FILE LEVEL (no `###` before it). But for **any state-modifying operations** (seeding, clearing, resetting), ALWAYS use a request-level block with `###` before it.

## Assertions `?? js` / `?? status` / `?? body`

Run **after** request completes.

### Syntax Forms

```http
# Full JavaScript form
?? js response.parsedBody.status == approved

# Status shorthand (httpyac demos)
?? status == 200

# Body shorthand (httpyac demos)
?? body email == plankton@chum-bucket.sea
```

### Operators (REQUIRED)

`== != < > <= >=`

**⚠️ Without an operator, the line becomes request body (causes 500 error!):**
```http
# ❌ WRONG - becomes body content!
?? js response.parsedBody.isValid

# ✅ CORRECT
?? js response.parsedBody.isValid == true
```

### Multiple Assertions

```http
?? status == 200
?? body email == plankton@chum-bucket.sea
?? js parseFloat(response.parsedBody.balance) > 100
```

## Response Access Differences

| Context | Status | Body Field | Example |
|---------|--------|------------|---------|
| **Demo** (httpyac) | `response.status` | `response.parsedBody.field` | `?? js response.parsedBody.email == x` |
| **Spec** (uctest) | `$(response).status()` | `$(response).field("x")` | `?? js $(response).field("email") == x` |

❌ Using `$(response)` in demos → undefined
❌ Using `response.parsedBody` in specs → works but non-standard

## References (Specs Only)

```http
# @name setup_user
POST /users ...

# @ref setup_user      # runs once, cached
GET /users/{{setup_user.id}}

# @forceRef setup_user # runs fresh each time
GET /users/{{setup_user.id}}
```

- `@name` above HTTP line
- Keep chains acyclic
- Typo in @ref → `ref "x" not found`

## Variable Definition Patterns

**Three patterns for different use cases:**

| Pattern | When to Use | Example |
|---------|-------------|---------|
| `@var = value` | Static config | `@host = {{base_host}}/v203` |
| `@var = {{response...}}` | Simple response capture | `@cart_id = {{response.parsedBody.cart_id}}` |
| `{{ exports.var = ... }}` | Computed values, array ops | `{{ exports.item = response.parsedBody.find(...); }}` |

### Simple Capture: `@var = {{...}}`
```http
@orderId = {{$(response).field("order_id")}}           # Specs
@orderId = {{response.parsedBody.order_id}}            # Demos
@session = {{refreshCookie(response)}}                  # Demos with cookies
```

### Computed Values: `exports.var` (INSIDE JS blocks only)
```http
GET /menu

{{ exports.kelp = response.parsedBody.find(i => i.name.includes("Kelp")); }}

### Use the extracted object
POST /cart/{{cart_id}}/items
Content-Type: application/json

{"item_id": "{{kelp.id}}"}
```

**⚠️ CRITICAL:** `exports.var` is ONLY valid inside `{{ }}` blocks!
```http
# ❌ WRONG - exports outside JS block
exports.foo = 123

# ✅ CORRECT - inside JS block
{{ exports.foo = 123; }}
```

**Scope:** Variables are file-local. However, exports from **file-level** `{{ }}` blocks (no `###` before them) ARE available via `@import`. See "File-Level vs Request-Level Blocks" above.

## Tags (Specs Only)

```http
# @tag v301, smoke
```

⚠️ Never hand-edit in inherited (`~`) files—managed by ucsync.

## Imports

```http
# @import ../common/setup.http
```

- Use for shared variables/setup
- Relative paths from current file
- NO cross-file @ref between unrelated files

## Content Types

### JSON
```http
POST {{host}}/endpoint
Content-Type: application/json

{
  "field": "value"
}
```

### Form URL Encoded
```http
POST {{host}}/endpoint
Content-Type: application/x-www-form-urlencoded

field=value&other=data
```

## See Also

- `http-gotchas` - Critical pitfalls (LOAD THIS TOO!)
- `spec-conventions` - E2E spec patterns
- `demo-conventions` - Demo patterns
