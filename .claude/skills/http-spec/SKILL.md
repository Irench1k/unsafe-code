---
name: http-spec
description: E2E spec conventions, debugging, and inheritance for uctest. Auto-invoke when working with spec/**/*.http files.
---

# E2E Spec Reference (uctest)

## Conventions

**Helpers** (from utils.cjs):
- Auth: `auth.basic()`, `auth.login()`, `auth.restaurant()`
- Users: `user("plankton").balance()`, `user().canLogin()`
- Platform: `platform.seed()`, `platform.seedCredits()`
- Response: `$(response).status()`, `.field("x")`, `.isOk()`, `.hasOnlyUserData()`
- Utils: `testEmail()`, `menu.item()`, `order.total()`

**Structure**:
- One scenario per `###` block
- `@name` above HTTP line
- Captures: `@foo = {{ $(response).field("id") }}`
- Tags: `# @tag v301, smoke` (managed by ucsync)

**Assertions**:
```http
?? js $(response).status() == 200
?? js $(response).hasOnlyUserData("plankton") == true
?? js $(response).field("balance") > 100
```

## Inheritance

**spec.yml** controls inheritance. Never edit `~` files directly.

**Commands**:
```bash
ucsync -n          # preview changes
ucsync             # apply
ucsync spec/v303/  # resync path
```

**Rules**:
- New versions inherit previous unless README says otherwise
- Add tags only in source files, then run ucsync
- Prefer adding overrides over deleting inherited tests

## Debugging Failures

### Failure Classification

| Error | Cause | Fix |
|-------|-------|-----|
| `ref "X" not found` | Missing/typo @name, wrong scope | ucsync or fix @name |
| Assertion mismatch | Code regression OR test drift | Check README for intent |
| `capture "x" undefined` | Upstream @ref didn't run | Check @ref chain |
| Type error | Syntax issue | Fix helper usage |
| Stale `~` files | Inheritance out of sync | Run ucsync |

### Investigation

```bash
# Run with continuation after failures
uctest vNNN/ -k

# Inspect @ref graph
uctest --show-plan path.http

# Check backend logs
uclogs --since 30m

# Add debug output (remove after)
?? js $(response).json()
{{ console.log(response.parsedBody) }}
```

### Handoff

| Issue Type | Delegate To |
|------------|-------------|
| Spec syntax | spec-author |
| Inheritance/tags | spec-runner (ucsync) |
| App bug | code-author |

## @ref / @forceRef

```http
# @name login_user
POST /auth/login ...

# @ref login_user      # cached, runs once
# @forceRef login_user # fresh each time
GET /orders
Cookie: {{login_user.cookie}}
```

- Keep chains acyclic
- Use @forceRef for stateful operations that must rerun
