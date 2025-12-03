---
name: http-e2e-specs
description: Writing E2E tests in spec/vNNN/ using uctest and utils.cjs helpers. Auto-invoke when working with files in spec/ directory, $(response) helpers, auth.basic(), @ref/@forceRef patterns, or platform.seed(). Do NOT use for interactive demos in vulnerabilities/.../http/ directories - those use plain httpyac syntax without helpers.
---

# E2E Spec Writing

Write `.http` test files for the uctest e2e suite in `spec/`.

## When to Use This Skill

- Creating or editing files in `spec/vNNN/` directories
- Using `$(response)` wrapper helpers
- Using `auth.basic()`, `platform.seed()`, `user()` helpers
- Managing `@ref`/`@forceRef` dependency chains
- Working with `_imports.http`, `_fixtures.http` infrastructure

## When NOT to Use

- **Interactive demos** in `vulnerabilities/.../http/eNN/` directories
  - Those use `httpyac` (NOT uctest)
  - Those use plain `response.parsedBody` (NOT `$(response)`)
  - Those have NO imports, NO @ref/@forceRef
  - Use the `http-interactive-demos` skill instead

## Critical Syntax Rules

### 1. Assertion Format: `?? js LHS == RHS`

```http
# CORRECT - RHS is a literal (no quotes!)
?? js $(response).field("status") == delivered
?? js $(response).field("email") == {{user("plankton").email}}

# WRONG - quotes become part of the literal string
?? js $(response).field("status") == "delivered"
```

### 2. Assertions Run AFTER Request

ALL assertions execute after the HTTP request, regardless of position. Capture pre-state in JS blocks:

```http
# WRONG - both run AFTER request!
POST /refund
?? js await user("plankton").balance() == 200    # Intended "before"
?? js await user("plankton").balance() == 210    # Both check same state!

# CORRECT - capture pre-state in JS block
{{
  exports.balanceBefore = await user("plankton").balance();
}}
POST /refund
?? js await user("plankton").balance() == {{balanceBefore + 10}}
```

### 3. Operator is REQUIRED

Without `== != < > <= >=`, the line becomes request body (causes 500 error):

```http
# WRONG - no operator! Becomes request body!
?? js response.parsedBody.email.includes("plankton")

# CORRECT - has operator
?? js response.parsedBody.email.includes("plankton") == true
```

**Error you'll see**: `Failed to decode JSON object: Extra data`

### 4. Financial Calculations

API returns balances as strings. JS coercion surprises:

```javascript
100 - "12.34"   // === 87.66  OK
100 + "12.34"   // === "10012.34"  BAD (concatenation!)
```

Always use `parseFloat()`:
```http
?? js parseFloat($(response).balance()) + parseFloat(tip) == {{expected}}
```

## Authentication Helpers

```http
# Basic Auth (version-aware)
Authorization: {{auth.basic("plankton")}}
Authorization: {{auth.basic("plankton", "wrongpassword")}}  # test wrong pw

# Cookie Auth
Cookie: {{auth.login("plankton")}}

# Restaurant API key
X-API-Key: {{auth.restaurant("krusty_krab")}}
```

## Response Helpers

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

## Dependencies: @name, @ref, @forceRef

```http
### Creates cart (named for reuse)
# @name cart_created
POST /cart?restaurant_id=1
Authorization: {{auth.basic("patrick")}}

@cart_id = {{$(response).field("cart_id")}}

### Reuses cart (cached result)
# @ref cart_created
POST /cart/{{cart_id}}/items

### Fresh cart each time
# @forceRef cart_created
POST /cart/{{cart_id}}/checkout
```

**Rule**: If A `@forceRef` B, then B must `@forceRef` its own deps too!

## Platform Setup

```http
# Full reset + seed (slow - use sparingly)
{{
  await platform.seed({ plankton: 200, patrick: 150 });
}}

# Balance-only update (fast - no DB reset)
{{
  await platform.seedCredits("plankton", 200);
  await platform.seedCredits("spongebob", 150);
}}
```

**Seed inside first named request, NOT at file scope!**

## File Organization

| File | Purpose | Has @tag? |
|------|---------|-----------|
| `happy.http` | Success paths (canonical fixtures) | Yes |
| `authn.http` | Authentication boundary tests | Yes |
| `authz.http` | Authorization/ownership tests | Yes |
| `validation.http` | Input validation tests | Yes |
| `_fixtures.http` | Named setups only | No (never!) |
| `_imports.http` | Import chain | No |
| `~*.http` | INHERITED - never edit! | Yes (managed) |
| `vuln-*.http` | Vulnerability demonstrations | Yes |

## Import Chain Pattern

```http
# In cart/checkout/post/_imports.http
# @import ../../_imports.http
```

Each `_imports.http` pulls parent imports.

## Tags (Managed by ucsync)

**Never edit `@tag` lines manually.** They're managed by `spec.yml`:

```yaml
v301:
  tags: [r03, v301]
  tag_rules:
    "**/authn.http": [authn]
    "**/happy.http": [happy]
```

Run `ucsync` after changing `spec.yml` to update tags.

## See Also

- [syntax.md](syntax.md) - Full syntax reference
- [helpers.md](helpers.md) - utils.cjs helper reference
- `http-assertion-gotchas` skill - Detailed pitfall explanations
- `spec-inheritance` skill - Managing inheritance
