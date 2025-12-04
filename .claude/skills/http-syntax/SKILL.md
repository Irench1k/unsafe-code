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
POST {{host}}/endpoint

{{
  // Runs AFTER request (for logging, NOT assertions)
  console.info("Got balance:", response.parsedBody.balance);
}}
```

- Run **before** the HTTP line (setup) or **after** response (logging)
- Auto-await Promises
- Export with `exports.foo = ...`
- Use for seeding, capturing pre-state, logging

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

## Variable Capture

```http
@orderId = {{$(response).field("order_id")}}           # Specs
@orderId = {{response.parsedBody.order_id}}            # Demos
@session = {{refreshCookie(response)}}                  # Demos with cookies
```

Scope: same file only, not across imports.

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
