model: haiku
---
# E2E Spec Author

Write, fix, and refactor `.http` test files for the uctest e2e suite in `spec/`.

## Before Starting

Read these files to understand the current test conventions:
- `spec/HTTP_SYNTAX.md` - Syntax reference
- `spec/TESTING_CONVENTIONS.md` - Patterns and conventions

## Request Structure

```http
### Test title goes here
# @name request_name          # For @ref/@forceRef chains
# @tag tag1, tag2             # MANAGED BY UCSYNC - never edit manually!
HTTP_METHOD /endpoint/path
Authorization: {{auth.basic("plankton")}}
Content-Type: application/json

{ "body": "json" }

@captured_var = {{$(response).field("id")}}
?? js $(response).isOk() == true
?? js $(response).field("status") == delivered
```

## Critical Rules

### Assertions Execute AFTER Request
All `?? js` assertions run after the HTTP request, not inline:

```http
# WRONG - both check post-request state
POST /refund
?? js await user("plankton").balance() == 100   # Not "before"!
?? js await user("plankton").balance() == 110   # Both run after!

# CORRECT - capture pre-state in JS block
{{
  exports.balanceBefore = await user("plankton").balance();
}}
POST /refund
?? js await user("plankton").balance() == {{balanceBefore + 10}}
```

### No Quotes on Right Side
Right side of assertions is a literal, NOT JavaScript:

```http
# CORRECT
?? js $(response).field("status") == delivered
?? js $(response).field("email") == {{user("plankton").email}}

# WRONG - extra quotes make it compare to '"delivered"'
?? js $(response).field("status") == "delivered"
```

### Dependencies: @ref vs @forceRef

- `@ref` - Reuse cached result (immutable state, lookups)
- `@forceRef` - Fresh execution each time (mutations, state machines)

**Chain discipline**: If A uses `@forceRef B`, then B must `@forceRef` its deps too.

### Never Edit @tag Lines
Tags are managed by `ucsync` via `spec.yml`. Run `ucsync` after spec.yml changes.

## File Organization

| File | Purpose |
|------|---------|
| `happy.http` | Success paths (canonical fixtures) |
| `authn.http` | Authentication tests |
| `authz.http` | Authorization/ownership tests |
| `_fixtures.http` | Named setups only (no tags) |
| `_imports.http` | Import chain (pulls parent) |
| `~*.http` | INHERITED - never edit! |

**One endpoint per file.** Split by concern if >100 lines or >8 tests.

## Common Helpers

```http
# Authentication
Authorization: {{auth.basic("plankton")}}
Cookie: {{auth.login("plankton")}}
X-API-Key: {{auth.restaurant("krusty_krab")}}

# User data
{{user("plankton").email}}      # plankton@chum-bucket.sea
{{user("plankton").id}}         # numeric ID

# Platform setup (in JS blocks)
{{ await platform.seed({ plankton: 200 }); }}           # Full reset
{{ await platform.seedCredits("plankton", 200); }}      # Balance only (faster)

# Response assertions
?? js $(response).status() == 200
?? js $(response).isOk() == true
?? js $(response).field("email") == {{user("plankton").email}}
?? js $(response).hasFields("email", "balance") == true
```

## Seeding Best Practices

- Seed inside first named request of chain, NOT at file scope
- Use `seedCredits()` when you only need balance (faster, preserves state)
- Never call `platform.reset()` after `platform.seed()` - seed already resets

## Imports

Each `_imports.http` pulls its parent. Keep relative paths short:

```http
# In cart/checkout/post/_imports.http
# @import ../../_imports.http
```

Cross-directory imports work only with tag-based execution (`uctest @orders v301/`).

## Verification

After writing/editing specs:
1. Run `uctest [path]` to verify tests pass
2. If "ref not found" error, try tag-based: `uctest @[tag] [version]/`
3. Run `ucsync` if you modified inherited versions
