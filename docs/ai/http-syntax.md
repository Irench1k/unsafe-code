# HTTP Syntax Reference

Authoritative syntax rules for `.http` files used by both interactive demos (httpyac) and E2E specs (uctest). Use this file before editing any `.http` file.

---

## Request Structure
```http
### Request title (required)
# @name my_request    # Optional: for @ref chains (specs only)
# @tag v301, happy    # Managed by ucsync (specs only)
METHOD /path?query=1
Header-Name: value
Content-Type: application/json

{"body": "here"}

?? js assertion == expected
```

### Structural Rules
| Rule | Correct | Wrong |
|------|---------|-------|
| New request | `###` prefix | Missing = merged with previous |
| Blank line before body | REQUIRED | Missing = body becomes headers |
| Comments | `#` at line start | `//` NOT supported |
| After HTTP line | Headers only | Comments break parsing |

---

## Variables & Hosts

### File-Level Variables
```http
@host = http://localhost:8000/api/v301
@plankton_email = plankton@chum-bucket.sea
```

### httpyac Auto-Prefix (`@host`)
When `@host` is defined, httpyac automatically prefixes request URLs:
```http
@host = http://localhost:8000/api/v201

### Works - no {{host}} needed
GET /orders
POST /auth/login
```
Never write `GET {{host}}/orders`—httpyac does the prefixing.

### Computed Variables
```http
@plankton_auth = Basic {{btoa(plankton_email + ":" + plankton_password)}}
```

### Response Capture
```http
# @name cart
POST /cart
Authorization: {{plankton_auth}}

@cart_id = {{cart.cart_id}}

### Use captured value
POST /cart/{{cart_id}}/items
```

---

## JavaScript Blocks `{{ }}`
```http
{{
  // Runs BEFORE request
  console.info("Starting...");
  exports.timestamp = Date.now();
}}
POST /endpoint

{{
  // Runs AFTER request (logging only, NOT assertions)
  console.info("Balance:", response.parsedBody.balance);
}}
```

### Single-Line Block Pitfall
```http
# WRONG - httpyac interprets as URL
{{ await seedBalance("v203", "plankton@chum-bucket.sea", 100); }}

# CORRECT
{{
  await seedBalance("v203", "plankton@chum-bucket.sea", 100);
}}
```

### File-Level vs Request-Level Blocks
**File-level** (no `###` before it) runs once and can export helpers.
**Request-level** (after `###`) runs per request; exports are local.

---

## Assertions (`??`) Syntax

### Forms
```http
# Full JavaScript
?? js response.parsedBody.status == approved

# Status shorthand (demos)
?? status == 200

# Body shorthand (demos)
?? body email == plankton@chum-bucket.sea
```

### Operators REQUIRED
`== != < > <= >=`
```http
# WRONG - becomes body content, causes 500
?? js response.parsedBody.isValid

# CORRECT
?? js response.parsedBody.isValid == true
```

### No Quotes on RHS
```http
# WRONG - causes syntax error
?? js response.parsedBody.status == "approved"

# CORRECT
?? js response.parsedBody.status == approved
```

### Multiple Assertions Allowed
```http
?? status == 200
?? body email == plankton@chum-bucket.sea
?? js parseFloat(response.parsedBody.balance) > 100
```

---

## Response Access: Demo vs Spec
| Context | Status | Field | Example |
|---------|--------|-------|---------|
| **Demo** (httpyac) | `response.status` | `response.parsedBody.field` | `?? js response.parsedBody.email == x` |
| **Spec** (uctest)  | `$(response).status()` | `$(response).field("x")` | `?? js $(response).field("email") == x` |

### Demo Examples
```http
?? status == 200
?? body email == plankton@chum-bucket.sea
?? js parseFloat(response.parsedBody.balance) > 100
```

### Spec Examples
```http
?? js $(response).status() == 200
?? js $(response).field("email") == {{user("plankton").email}}
?? js $(response).hasOnlyUserData("plankton") == true
```

---

## References (`@ref` / `@forceRef`) – Specs Only
```http
# @name setup_user
POST /users ...

# @ref setup_user      # Runs once, cached
GET /users/{{setup_user.id}}

# @forceRef setup_user # Runs fresh each time
GET /users/{{setup_user.id}}
```
Use `@forceRef` when the referenced request mutates state; if A uses `@forceRef B`, then B must `@forceRef` its own dependencies.

---

## Variable Definition Patterns
| Pattern | Use Case | Example |
|---------|----------|---------|
| `@var = value` | Static config | `@host = {{base_host}}/v203` |
| `@var = {{response...}}` | Response capture | `@cart_id = {{response.parsedBody.cart_id}}` |
| `{{ exports.var = ... }}` | Computed/array ops | `{{ exports.item = response.parsedBody.find(...); }}` |

`exports.*` may only be set inside `{{ }}` blocks.

---

## Tags & Imports (Specs)
```http
# @tag v301, happy
# @import ../common.http
```
- Tags are managed by `ucsync`; never hand-edit in inherited (`~`) files.
- Imports are relative from the current file.

---

## Content Types
```http
POST /endpoint
Content-Type: application/json

{ "field": "value" }
```
```http
POST /endpoint
Content-Type: application/x-www-form-urlencoded

field=value&other=data
```

---

## Execution Order
```
1. File-level {{ }} blocks run once at load
2. For each request:
   a. Pre-request {{ }} block runs
   b. HTTP request sent
   c. Response received
   d. Post-request {{ }} block runs
   e. ALL ?? assertions execute
   f. @variable captures execute
```

---

## Quick Diagnostics
| Symptom | Cause | Fix |
|---------|-------|-----|
| 500 after adding assertion | Missing operator | Add `== true`, `> 0`, etc. |
| Assertion fails but values look same | Quotes on RHS | Remove quotes |
| Pre-state == post-state | Capture timing | Capture in `{{ }}` BEFORE request |
| Numeric comparison wrong | String comparison | Use `parseFloat()` |
| `ref "X" not found` | Typo or missing `@name` | Check spelling, add `@name` |

---

## Pattern Cheatsheet
```http
# Boolean
?? js $(response).field("active") == true
?? js response.parsedBody.active == true

# String (NO QUOTES)
?? js $(response).field("status") == pending
?? js response.parsedBody.status == approved

# Email
?? js $(response).field("email") == plankton@chum-bucket.sea

# Numeric
?? js parseFloat($(response).balance()) > 100
?? js parseFloat(response.parsedBody.balance) > 100

# Compare to captured value
?? js parseFloat($(response).balance()) > {{balanceBefore}}

# Array length
?? js $(response).field("items").length > 0
?? js response.parsedBody.orders.length > 0

# Status
?? status == 200
?? js $(response).status() == 200
?? js $(response).isOk() == true
```
