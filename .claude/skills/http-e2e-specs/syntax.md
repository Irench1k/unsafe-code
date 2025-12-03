# E2E Spec Syntax Reference

Full syntax reference for `.http` test files using uctest.

## Request Structure

```http
### Test title goes here
# Optional comment
# @tag tag1, tag2, v301
HTTP_METHOD /endpoint/path
Header-Name: header-value
Content-Type: application/json

{
  "body": "goes here"
}

?? js assertion_expression == expected_value
```

Key elements:
- `###` starts a new test (required)
- `# @tag` assigns tags (MANAGED BY UCSYNC - never edit manually!)
- `# @name`, `# @ref`, `# @forceRef` control dependencies
- Blank line separates headers from body
- `?? js` starts an assertion line

## Variable Interpolation `{{ }}`

```http
# Single-line expression
POST /cart?restaurant_id={{restaurantId}}
Authorization: {{auth.basic("plankton")}}

# Multi-line JS block (for setup/exports)
{{
  await platform.seed({ plankton: 200 });
  exports.regEmail = testEmail("reg");
}}
```

**Auto-awaits promises!** Both work:
```http
Cookie: {{await auth.login("plankton")}}
Cookie: {{auth.login("plankton")}}        # Also works
```

## Assertions `?? js`

Syntax: `?? js <js_expression> <operator> <right_side>`

```http
?? js $(response).status() == 200
?? js $(response).isOk() == true
?? js $(response).field("email") == {{user("plankton").email}}
```

### CRITICAL: Execution Order

1. JS blocks `{{ }}` run (setup, exports)
2. HTTP request is sent
3. ALL assertions (`?? js`) execute

### CRITICAL: No Quotes on Right Side

Right side is a **literal**, NOT JavaScript:

```http
# CORRECT
?? js $(response).field("status") == delivered
?? js $(response).field("email") == {{user("plankton").email}}

# WRONG - quotes become part of the literal
?? js $(response).field("status") == "delivered"
```

### Supported Operators

`== != < > <= >=`

Without an operator, the assertion becomes request body (causes 500 error).

## Dependencies: @name, @ref, @forceRef

```http
### Create a cart (can be referenced)
# @name cart_created
POST /cart?restaurant_id=1
Authorization: {{auth.basic("patrick")}}

@cart_id = {{$(response).field("cart_id")}}

### Use the cart - runs cart_created ONCE and reuses result
# @ref cart_created
POST /cart/{{cart_id}}/items
Authorization: {{auth.basic("patrick")}}

### Fresh cart each time - runs cart_created FRESH each time
# @forceRef cart_created
POST /cart/{{cart_id}}/checkout
Authorization: {{auth.basic("patrick")}}
```

**When to use:**
- `@ref` - Share immutable state (list lookups, reads)
- `@forceRef` - Need fresh state (mutations, state machines, balance changes)

**Chain discipline:** If A uses `@forceRef B`, then B must `@forceRef` its deps too!

## Exports and Captures

```http
# File-level exports (run once when file loads)
{{
  exports.host = "http://localhost:8000/api/v301";
  exports.testUser = testEmail("user");
}}

# Per-request exports (run when request executes)
### Setup request
# @name setup
{{
  await platform.reset();
  exports.regEmail = testEmail("reg");
}}

# Variable capture from response
@cart_id = {{$(response).field("cart_id")}}
@token = {{$(response).field("Text").match(/token=([A-Za-z0-9._-]+)/)[1]}}
```

## Suppression Directives `@ucskip`

Skip linter checks for specific requests:

```http
# @ucskip              # Suppress all checks
# @ucskip endpoint     # Suppress endpoint jurisdiction only
# @ucskip method       # Suppress method mismatch only
# @ucskip fake-test    # Suppress fake test warning
```

**Use for:** Verification steps in exploit chains, setup requests that cross endpoint boundaries.

## Imports

```http
# Import chain (pulls parent utilities)
# @import ../_imports.http

# Import specific file for dependencies
# @import ../../../cart/checkout/post/~happy.http
```

When files are inherited and deleted locally, imports must reference the `~` version:
```http
# Before porting (file exists locally)
# @import ./happy.http

# After porting (file now inherited)
# @import ./~happy.http
```

## File Organization

```
spec/v301/
  _imports.http                    # @import ../common.http
  cart/checkout/post/
    _imports.http                  # @import ../../_imports.http
    _fixtures.http                 # Named setups (no tags)
    happy.http                     # Success paths
    authn.http                     # Auth tests
    authz.http                     # Authorization tests
```

**One endpoint per file** - don't mix `/cart` and `/orders` in one file.

## Tags

Tags are **managed by ucsync** via `spec.yml`. Never edit manually.

```yaml
v301:
  tags: [r03, v301]              # All tests get these
  tag_rules:
    "**/authn.http": [authn]     # Pattern-based tags
    "**/happy.http": [happy]
```
