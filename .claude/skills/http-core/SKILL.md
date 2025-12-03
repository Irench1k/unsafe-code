---
name: http-core
description: HTTP file syntax and common pitfalls for specs and demos. Auto-invoke when editing any .http file.
---

# HTTP Core Syntax & Gotchas

**Scope**: Both specs (`spec/**/*.http`) and demos (`vulnerabilities/.../http/**/*.http`).

## Request Structure

```http
### Request title
# @name my_request    # for @ref (specs only)
# @tag v301, smoke    # managed by ucsync (specs only)
METHOD /path?query=1
Header: value
Content-Type: application/json

{"body": "here"}

?? js assertion == expected
```

## Critical Rules

| Rule | Correct | Wrong |
|------|---------|-------|
| Blank line before body | Required | Missing → malformed request |
| RHS in assertions | `== value` (no quotes) | `== "value"` → literal quotes |
| New request | `###` prefix | Missing → merged with previous |
| Comments | `#` before HTTP line | `//` not supported |

## JavaScript Blocks `{{ }}`

- Run **before** request
- Auto-await Promises
- Export with `exports.foo = ...`
- Use for seeding, capturing pre-state

## Assertions `?? js`

- Run **after** request
- Syntax: `?? js expression == literal`
- Multiple allowed per request
- Capture pre-state in `{{ }}` block first

## Spec vs Demo Response Access

| Context | Status | Body Field | Headers |
|---------|--------|------------|---------|
| **Spec** (uctest) | `$(response).status()` | `$(response).field("x")` | `$(response).headers().get("x")` |
| **Demo** (httpyac) | `response.status` | `response.parsedBody.x` | `response.headers["x"]` |

❌ Using `$(response)` in demos → undefined

## References (Specs Only)

```http
# @name setup_user
POST /users ...

# @ref setup_user      # runs once, cached
# @forceRef setup_user # runs fresh each time
GET /users/{{setup_user.id}}
```

- `@name` above HTTP line
- Keep chains acyclic
- Typo in @ref → `ref "x" not found`

## Captures (Specs Only)

```http
@orderId = {{ $(response).field("order_id") }}
```

Scope: same file only, not across imports.

## Tags (Specs Only)

```http
# @tag v301, smoke
```

⚠️ Never hand-edit in inherited (`~`) files—managed by ucsync.

## Common Gotchas

1. **Missing blank line** → request body becomes headers
2. **Quoted RHS** → comparing to literal `"value"` string
3. **$(response) in demos** → undefined, use `response.parsedBody`
4. **@ref typo** → `ref "x" not found`
5. **Wrong Content-Type** → empty parsedBody
6. **Assertions before request** → still run after (capture pre-state first)
7. **Cached @ref** → use @forceRef for fresh state
8. **Trailing spaces** → can break signatures
9. **Comments after HTTP line** → invalid

## Shortcuts (httpyac Demos)

```http
?? status == 200          # instead of ?? js response.status == 200
?? body field == value    # instead of ?? js response.parsedBody.field == value
```
