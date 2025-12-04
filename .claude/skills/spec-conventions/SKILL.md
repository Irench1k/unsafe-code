---
name: spec-conventions
description: E2E spec conventions for uctest. Covers utils.cjs helpers, $(response), auth patterns, inheritance, and debugging. Auto-invoke when working with spec/**/*.http files.
---

# E2E Spec Conventions (uctest)

Patterns for `.http` files in `spec/` directories, run with **uctest** (NOT httpyac).

## Response Wrapper: $(response)

```http
# Status
?? js $(response).status() == 200
?? js $(response).isOk() == true
?? js $(response).isError() == true

# Field access
?? js $(response).field("email") == {{user("plankton").email}}
?? js $(response).field("order.status") == pending

# Financial
?? js $(response).total() == 12.99
?? js $(response).balance() == 187.01

# Validation
?? js $(response).hasFields("email", "balance") == true
?? js $(response).hasOnlyUserData("plankton") == true
```

## Authentication Helpers

### auth.basic(user, password?)
```http
Authorization: {{auth.basic("plankton")}}
Authorization: {{auth.basic("plankton", "wrongpassword")}}
```

### auth.login(user) - Async
```http
Cookie: {{auth.login("plankton")}}
```

### auth.restaurant(key)
```http
X-API-Key: {{auth.restaurant("krusty_krab")}}
```

### auth.admin()
```http
X-Admin-API-Key: {{auth.admin()}}
```

## User Helpers

### user(name)
```http
{{user("plankton").email}}      # plankton@chum-bucket.sea
{{user("plankton").shortId}}    # plankton
{{user("plankton").password}}   # i_love_my_wife
{{user("plankton").id}}         # 3 (in v301+)
```

### Async User Methods
```http
?? js await user("plankton").canLogin() == true
?? js await user("plankton").canLogin("wrongpw") == false
?? js await user("plankton").balance() == 200
```

## Platform Setup (E2E Only)

### platform.seed(balances) - Full Reset + Seed
```http
{{
  await platform.seed({ plankton: 200, patrick: 150 });
}}
```

### platform.seedCredits(user, amount) - Fast Balance Set
```http
{{
  await platform.seedCredits("plankton", 200);
}}
```

Sets balance to exact amount (idempotent). **Does NOT increment.**

### platform.reset() - Database Reset Only
```http
{{
  await platform.reset();
}}
```

## Dynamic User Verification

For dynamically created users (registration tests):

```http
?? js await verify.canLogin(regEmail, "password123") == true
?? js await verify.canAccessAccount(regEmail, "password123") == true
```

## Cookie Helpers

```http
# Extract cookie from response
@sessionCookie = {{extractCookie(response)}}

# Check if response sets a cookie
?? js hasCookie(response) == false
```

## Test Email Generation

```http
{{
  exports.regEmail = testEmail("reg");  # reg+1699012345_abc123@example.test
}}
```

## Menu Helpers

```http
{{menu.item(1).id}}                    # Get by ID
{{menu.item("Krabby Patty").id}}       # Get by name
{{menu.firstAvailable(1).id}}          # First available at restaurant 1
{{menu.cheapest().id}}                 # Lowest price
```

## Order Calculations

```http
# Expected total for items + tip
?? js $(response).total() == {{order.total([4, 5], 2)}}

# Expected balance after order
?? js $(response).field("balance") == {{order.balanceAfter(200, [4, 5], 2)}}
```

## @ref / @forceRef Dependencies

```http
# @name setup_cart
POST /cart?restaurant_id=1
Authorization: {{auth.basic("patrick")}}

@cart_id = {{$(response).field("cart_id")}}

### Use cart - runs setup_cart ONCE, caches result
# @ref setup_cart
POST /cart/{{cart_id}}/items
Authorization: {{auth.basic("patrick")}}

### Fresh cart each time - runs setup_cart FRESH
# @forceRef setup_cart
POST /cart/{{cart_id}}/checkout
Authorization: {{auth.basic("patrick")}}
```

**When to use:**
- `@ref` - Share immutable state (list lookups, reads)
- `@forceRef` - Need fresh state (mutations, balance changes)

**Chain discipline:** If A uses `@forceRef B`, then B must `@forceRef` its deps too!

## Inheritance & Tags

Tags are **managed by ucsync** via `spec.yml`. Never edit manually.

```yaml
# spec.yml
v301:
  tags: [r03, v301]
  tag_rules:
    "**/authn.http": [authn]
    "**/happy.http": [happy]
```

**Commands:**
```bash
ucsync -n          # Preview changes
ucsync             # Apply
ucsync spec/v303/  # Resync specific path
```

**Rules:**
- New versions inherit previous unless README says otherwise
- Add tags only in source files, then run ucsync
- Never edit `~` files directly

## Debugging Failures

### Failure Classification

| Error | Cause | Fix |
|-------|-------|-----|
| `ref "X" not found` | Missing/typo @name, wrong scope | ucsync or fix @name |
| Assertion mismatch | Code regression OR test drift | Check README for intent |
| `capture "x" undefined` | Upstream @ref didn't run | Check @ref chain |
| Type error | Syntax issue | Fix helper usage |
| Stale `~` files | Inheritance out of sync | Run ucsync |

### Investigation Commands

```bash
# Run with continuation after failures
uctest vNNN/ -k

# Inspect @ref graph
uctest --show-plan path.http

# Check backend logs
uclogs --since 30m

# Debug output (remove after!)
{{ console.log(response.parsedBody) }}
```

### Handoff Protocol

| Issue Type | Delegate To |
|------------|-------------|
| Spec syntax | spec-author |
| Inheritance/tags | spec-runner (ucsync) |
| App bug | code-author |

## Seeding Best Practice

Seed **inside** the first named request, NOT at file scope:

```http
### Setup (CORRECT)
# @name setup
{{
  await platform.seed({ plankton: 200 });
}}
POST /first-step
...

### WRONG - at file scope
{{
  await platform.seed({ plankton: 200 });  # Runs once at load, breaks chains!
}}
```

## See Also

- `http-syntax` - Core syntax reference
- `http-gotchas` - Critical pitfalls
- `demo-conventions` - Demo patterns (different helpers!)
