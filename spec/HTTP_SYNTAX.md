# HTTP Test Syntax Reference

Prescriptive guide for writing `.http` test files using `uctest` (our fork of httpyac). This covers only what we use - not the full httpyac feature set.

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
- `# @tag` assigns tags (managed by ucsync, never edit manually)
- `# @name`, `# @ref`, `# @forceRef` control dependencies (see below)
- Blank line separates headers from body
- `?? js` starts an assertion line

## Variable Interpolation `{{ }}`

Embed JavaScript expressions in requests:

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

**Auto-awaits promises!** Both of these work:
```http
Cookie: {{await auth.login("plankton")}}
Cookie: {{auth.login("plankton")}}        # Also works - uctest auto-awaits
```

Variables available inside `{{ }}`: everything from `exports` (see utils.cjs).

## Assertions `?? js`

Syntax: `?? js <js_expression> <operator> <right_side>`

```http
?? js $(response).status() == 200
?? js $(response).isOk() == true
?? js $(response).field("email") == {{user("plankton").email}}
```

**⚠️ CRITICAL: Assertions ALWAYS execute AFTER the HTTP request is sent.**

This is true regardless of where assertions appear in the file. The execution order is:
1. JS blocks `{{ }}` run (setup, exports)
2. HTTP request is sent
3. ALL assertions (`?? js`) execute

This matters when you need pre-request state (like checking a balance changed):

```http
### WRONG - balance() is checked AFTER request, not before
POST /refund
?? js await user("plankton").balance() == 200        # Runs AFTER request!
?? js await user("plankton").balance() == 210        # Both run at the same time

### CORRECT - capture state in JS block, assert delta after
{{
  exports.balanceBefore = await user("plankton").balance();  # Runs BEFORE request
}}
POST /refund
?? js await user("plankton").balance() == {{balanceBefore + 10}}  # Runs AFTER
```

**Critical rules:**
- **Left side = JavaScript** (evaluated as code)
- **Right side = literal** (NOT evaluated unless you use `{{interpolation}}`)
- **NO quotes** around expected string values on the right side

```http
# CORRECT
?? js $(response).field("status") == delivered
?? js $(response).field("email") == {{user("plankton").email}}

# WRONG - extra quotes
?? js $(response).field("status") == "delivered"
?? js $(response).field("email") == "{{user("plankton").email}}"
```

**Async assertions work:**
```http
?? js await verify.canLogin(regEmail, "password123") == true
?? js await user("plankton").canLogin() == true
```

## Dependencies: @name, @ref, @forceRef

Control test execution order and state sharing:

```http
### Create a cart (can be referenced by other tests)
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

**When to use which:**
- `@ref` - Share immutable state (list lookups, reads)
- `@forceRef` - Need fresh state (mutations, state machines, balance changes)

**Chain discipline:** If request A uses `@forceRef B`, then B should also `@forceRef` its own dependencies.

## Exports

Share values between requests:

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

## Common Helpers (utils.cjs)

### Authentication

**Standard (always use):**
```http
# Basic Auth (version-aware username format)
Authorization: {{auth.basic("plankton")}}
Authorization: {{auth.basic("plankton", "wrongpassword")}}  # test wrong pw

# Cookie Auth
Cookie: {{auth.login("plankton")}}

# Restaurant API key
X-API-Key: {{auth.restaurant("krusty_krab")}}
```

**For explicit username format testing (account/credits only):**
```http
Authorization: Basic {{user("plankton").shortId}}:wrongpassword
Authorization: Basic {{user("plankton").email}}:wrongpassword
```

**NEVER use these patterns:**
```http
# ❌ Manual Base64 - too verbose
Authorization: Basic {{Buffer.from(user("plankton").email + ":pw").toString("base64")}}
```

### User Data
```http
# Access user properties
{{user("plankton").email}}          # plankton@chum-bucket.sea
{{user("plankton").shortId}}        # plankton
{{user("plankton").password}}       # i_love_my_wife
{{user("plankton").id}}             # 3 (in v301+)

# Async methods for assertions
?? js await user("plankton").canLogin() == true
?? js await user("plankton").canLogin("wrongpw") == false
?? js await user("plankton").balance() == 200
```

### Dynamic User Verification
For dynamically created users (e.g., registration tests):
```http
?? js await verify.canLogin(regEmail, "password123") == true
?? js await verify.canAccessAccount(regEmail, "password123") == true
```

### Response Helpers
```http
?? js $(response).status() == 200
?? js $(response).isOk() == true
?? js $(response).isError() == true
?? js $(response).field("email") == {{user("plankton").email}}
?? js $(response).hasFields("email", "balance") == true
?? js $(response).hasOnlyUserData("plankton") == true
?? js $(response).total() == 12.99
?? js $(response).balance() == 187.01
```

### Platform Setup
```http
# Full reset + seed (use sparingly - slow)
{{
  await platform.seed({ plankton: 200, patrick: 150 });
}}

# Balance-only update (no DB reset - faster)
{{
  await platform.seedCredits("plankton", 200);
  await platform.seedCredits("spongebob", 150);
}}
```

### Cookie Helpers
```http
# Extract cookie from response
@sessionCookie = {{extractCookie(response)}}

# Check if response sets a cookie (auth failure should NOT set cookie)
?? js hasCookie(response) == false
```

## Suppression Directives `@ucskip`

Skip linter checks for specific requests (useful for multi-step exploits or verification steps):

```http
# @ucskip              # Suppress all checks (method + endpoint)
# @ucskip endpoint     # Suppress endpoint jurisdiction only
# @ucskip method       # Suppress method mismatch only
# @ucskip fake-test    # Suppress fake test warning
```

**When to use:**
- Verification steps in exploit chains (e.g., `GET /account/info` to verify hijack)
- Setup requests that cross endpoint boundaries (e.g., `GET /menu` for price lookup)
- Impact validation requests (e.g., checking balance after exploit)

**Example:**
```http
### Verify hijack succeeded
# @forceRef exploit_step
# @ucskip
# @tag auth, r02, v205, vulnerable
GET /account/info
Cookie: {{hijacked_cookie}}

?? js $(response).fieldEquals("email", "victim@example.com") == true
```

---

## Common Gotchas

### Assertion Execution Order

All assertions run AFTER the HTTP request, not inline where they appear:

```http
### This test is BROKEN - both assertions check post-request state
POST /api/refund
?? js await user("plankton").balance() == 100        # WRONG: Intended as "before"
?? js await user("plankton").balance() == 110        # Both check the same (post-request) state!

### CORRECT: Capture pre-state in JS block
{{
  exports.balanceBefore = await user("plankton").balance();
}}
POST /api/refund
?? js await user("plankton").balance() == {{balanceBefore + 10}}
```

**Rule of thumb:** If you need to assert something CHANGED, capture the "before" value in a JS block and compute the expected "after" value in the assertion using `{{interpolation}}`.

### Financial Calculations (JS String Coercion)

API returns balances as strings (`"12.34"`). JavaScript coercion can surprise you:

```javascript
100 - "12.34"   // === 87.66  ✓ (subtraction works)
100 + "12.34"   // === "10012.34"  ✗ (concatenation!)
```

**Always use parseFloat():**
```http
?? js parseFloat($(response).balance()) + parseFloat(tip) == {{expected}}
```

### No Quotes on Right Side

The right side of assertions is a literal, not JavaScript:

```http
# CORRECT
?? js $(response).field("status") == delivered

# WRONG - this compares to the string '"delivered"' with quotes
?? js $(response).field("status") == "delivered"
```

### Assertions MUST Have Two Sides (Operator Required)

httpyac assertions **require an operator and two sides**. An assertion without an operator becomes part of the request body!

```http
# CORRECT - has operator with two sides
?? js response.parsedBody.email == plankton@chum-bucket.sea
?? js response.parsedBody.length > 0

# WRONG - no operator! This becomes part of request body!
?? js response.parsedBody.email.includes("plankton")
?? js response.parsedBody.isValid
```

The "wrong" examples will cause **500 server errors** because httpyac sends the assertion text as JSON body, corrupting the request. Error logs will show: `Failed to decode JSON object: Extra data`.

**Key rule:** Every `?? js` line must have `==`, `!=`, `<`, `>`, `<=`, or `>=` with values on both sides.

### Explicit Username Format Testing

When testing credentials with explicit username format, use the email format (short username format is not supported in most versions):

```http
# Email format Basic Auth - explicit
Authorization: Basic {{user("plankton").email}}:wrongpassword

# For wrong/empty password tests
Authorization: Basic {{user("plankton").email}}:
```

Use `auth.basic()` for standard tests; use explicit format only when testing the credential format itself.

### @forceRef Chain Consistency

If you use `@forceRef` for a dependency, that dependency should also `@forceRef` its own dependencies:

```http
# CORRECT - consistent chain
# @name step1
# @forceRef setup
...

# @name step2
# @forceRef step1    # step1 already @forceRef setup, chain is consistent
...

# WRONG - broken chain
# @name step1
# @ref setup         # Using @ref here...
...

# @name step2
# @forceRef step1    # ...means @forceRef here doesn't get fresh setup
...
```

## File Organization

- **One endpoint per file** - don't mix `/cart` and `/orders` in one file
- **~100 lines or ~8 tests max** - split by concern if larger
- **Use `@import` chains** - each `_imports.http` pulls parent imports

```
spec/v301/
  _imports.http                    # @import ../common.http
  cart/checkout/post/
    _imports.http                  # @import ../../_imports.http
    happy.http                     # Success paths
    authn.http                     # Auth tests
    authz.http                     # Authorization tests
```

## Tags (Managed by ucsync)

**Never edit `@tag` lines manually.** They're managed by `spec.yml`:

```yaml
v301:
  tags: [r03, v301]              # All tests get these
  tag_rules:
    "**/authn.http": [authn]     # Pattern-based tags
    "**/happy.http": [happy]
```

Run `ucsync` after changing `spec.yml` to update tags.

## Interactive Demo Files (vulnerabilities/*/http/)

Interactive `.http` files in `vulnerabilities/*/http/` directories are **student-facing demos**, NOT automated e2e tests. They use **plain httpyac syntax** without utils.cjs helpers.

| Pattern | Interactive Demos | spec/ e2e Tests |
|---------|-------------------|-----------------|
| Response body | `response.parsedBody.email` | `$(response).field("email")` |
| Named ref body | `{{namedRef.email}}` | Not commonly used |
| Assertions | `?? js X == value` | `?? js $(response).isOk() == true` |
| Auth helpers | Manual `Authorization:` headers | `{{auth.basic("plankton")}}` |

**Key differences:**
- Interactive demos use simple, readable patterns (no utils.cjs)
- Each file should be runnable standalone via VSCode extension
- Cookie jar state is NOT reset between requests in the same file
- Run with `httpyac file.http -a` (not `uctest`)
