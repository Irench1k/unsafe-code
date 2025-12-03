# HTTP Syntax Quick Reference

Essential patterns for .http files. For full reference, see `spec/HTTP_SYNTAX.md`.

## Request Structure

```http
### Test title (required)
# @tag tag1, tag2, v301 (managed by ucsync - NEVER edit!)
HTTP_METHOD /endpoint
Header-Name: value

{"body": "here"}

?? js assertion == expected
```

## Variables

```http
# Define
@base = http://localhost:8000/api/v301
@auth = {{Buffer.from("user:pass").toString("base64")}}

# Use
GET {{base}}/messages
Authorization: Basic {{auth}}

# Multi-line JS block
{{
  await platform.seed({ plankton: 200 });
  exports.email = testEmail("reg");
}}
```

## Assertions

**Syntax**: `?? js <left_expression> <operator> <right_literal>`

```http
?? js $(response).status() == 200
?? js $(response).isOk() == true
?? js $(response).field("email") == {{user("plankton").email}}
```

**CRITICAL**:
- No quotes on right side (it's a literal, not JS)
- All assertions run AFTER request
- Capture pre-state in JS block for change detection

## Dependencies

```http
### First request
# @name setup
POST /cart
@cart_id = {{$(response).field("cart_id")}}

### Reuses setup result (cached)
# @ref setup
GET /cart/{{cart_id}}

### Gets fresh setup each time
# @forceRef setup
POST /cart/{{cart_id}}/checkout
```

**Rule**: If A `@forceRef` B, then B must `@forceRef` its deps too!

## Common Helpers (E2E Specs Only)

```http
# Auth
Authorization: {{auth.basic("plankton")}}
Cookie: {{auth.login("plankton")}}
X-API-Key: {{auth.restaurant("krusty_krab")}}

# Response
$(response).status()
$(response).isOk() / isError()
$(response).field("key")
$(response).hasFields("a", "b")

# Platform
await platform.seed({ plankton: 200 })
await platform.seedCredits("plankton", 200)
```

## Demo vs Spec Syntax

| Demos | E2E Specs |
|-------|-----------|
| `response.parsedBody.field` | `$(response).field()` |
| Raw `Authorization:` | `{{auth.basic()}}` |
| 1 assert per test | Multiple OK |
| Plain httpyac | Full utils.cjs |

## Gotchas

1. **Assertions run AFTER request** - capture pre-state in JS block
2. **No quotes on RHS** - `== delivered` not `== "delivered"`
3. **String coercion** - use `parseFloat()` for math with API strings
4. **@tag lines** - managed by ucsync, never edit
