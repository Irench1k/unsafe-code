---
name: demo-principles
description: "⛔ MANDATORY principles for .http demos. Defines what 'clean' means: no {{host}} prefixes, no @disabled, minimal @name, strategic refreshCookie. Auto-invoke when editing ANY demo file."
---

# Demo Principles: What "Clean" Actually Means

> **Core Philosophy**: Demos exist to teach vulnerabilities. Every line must serve that purpose.
> Less code = more clarity = better learning.

---

## ⛔ CRITICAL RULES - NEVER VIOLATE

### 1. NO `{{host}}/` or `{{base}}/` Prefixes

httpyac auto-prefixes `@host` to all URLs. Using `{{base}}/path` is **noise**.

```http
# ❌ WRONG - visual clutter
@base = http://localhost:8000/api/v301
GET {{base}}/menu
POST {{base}}/orders

# ✅ CORRECT - clean and scannable
@host = {{base_host}}/v301
GET /menu
POST /orders
```

**Pattern**: Set `@host` once at file top, then use clean relative paths everywhere.

---

### 2. NO `@disabled` Directive

Demos are **manually clicked by students**, not run in CI. `@disabled` makes no sense.

```http
# ❌ WRONG - defeats the purpose
# @disabled
GET /menu

# ✅ CORRECT - options if file has issues:
# Option A: Remove the entire file if it's not contributing
# Option B: Leave it alone - students click what they want
# Option C: Add explanatory comment about prerequisites
# Requires manual token from Mailpit - see instructions above
GET /menu
```

---

### 3. MINIMAL `@name` Usage

**Anti-pattern**: `@name cart` then `cart.cart_id`
**Pattern**: Inline extraction with meaningful names

```http
# ❌ ANTI-PATTERN - generic name, indirection
# @name cart
POST /cart
...
POST /cart/{{cart.cart_id}}/items

# ✅ PATTERN - descriptive, direct
POST /cart
@cheap_cart_id = {{response.parsedBody.cart_id}}
...
POST /cart/{{cheap_cart_id}}/items
```

**When @name IS acceptable:**
- Distinguishing similar requests: `# @name planktons_order` vs `# @name patricks_order`
- Needing MULTIPLE fields from one response (rare - usually extract each field inline)

**Naming guidance:**
- `cart` → `cheap_cart_id`, `attackers_cart_id`, `unpaid_cart_id`
- `order` → `refund_target_order`, `krustykrab_order_id`
- Names should tell the exploit story

---

### 4. STRATEGIC `refreshCookie()` - NOT Every Request

`refreshCookie(response, session)` checks for Set-Cookie header. Only use when server **might** update session.

```http
# ❌ WRONG - GET never sends Set-Cookie, this is noise
GET /account/info
Cookie: {{session}}
@session = {{refreshCookie(response, session)}}

# ✅ CORRECT - only after requests that might update session
POST /auth/login
@session = {{refreshCookie(response)}}

POST /orders  # might update session cookie
Cookie: {{session}}
@session = {{refreshCookie(response, session)}}

GET /orders  # GET never updates session, no refresh needed
Cookie: {{session}}
```

**Rule of thumb:**
- `POST /auth/login` → always capture cookie
- Other `POST/PUT/PATCH/DELETE` → only if endpoint modifies session (rare)
- `GET` → never needs refreshCookie

---

### 5. State Reset with Helpers - NOT `/account/credits`

`POST /account/credits` **increments**. Use `seedBalance()` which **sets**.

```http
# ❌ WRONG - increment is not idempotent
POST /account/credits
X-Admin-API-Key: {{platform_api_key}}
Content-Type: application/x-www-form-urlencoded

user=plankton@chum-bucket.sea&amount=200

# ✅ CORRECT - idempotent reset
{{
  await seedBalance("v301", "plankton@chum-bucket.sea", 100);
}}

### First real request after reset
GET /account/credits
```

---

### 6. Dynamic Menu Items - NOT Hardcoded IDs

```http
# ❌ WRONG - magic number
POST /cart/{{cart_id}}/items
Content-Type: application/json

{ "item_id": "4" }

# ✅ CORRECT - fetch and name meaningfully
GET /menu

{{ exports.krabby_patty = response.parsedBody.find(i => i.name.includes("Krabby Patty")); }}

POST /cart/{{cart_id}}/items
Content-Type: application/json

{ "item_id": "{{krabby_patty.id}}" }
```

---

## What Makes a Demo "Clean"

Study r01/r02 demos - they're the gold standard:

| Aspect | Clean Demo | Cluttered Demo |
|--------|------------|----------------|
| URLs | `GET /menu` | `GET {{base}}/menu` |
| Variables | `@cart_id = {{response.parsedBody.cart_id}}` | `# @name cart` then `cart.cart_id` |
| Cookie refresh | Only after login/POST | After every single request |
| State reset | `seedBalance()` helper | Manual `/account/credits` |
| Assertions | 1-2 key ones | Every field checked |
| console.info | 2-3 strategic | After every step |

---

## common/setup.http Requirements

Each section's setup.http MUST have:

```http
@base_host = http://localhost:8000/api
@e2e_key = e2e-test-key-unsafe-code-lab

# Actors...

{{
  exports.refreshCookie = (resp, existing = "") => { ... };

  exports.seedBalance = async (version, email, amount) => { ... };

  exports.resetDB = async (version) => { ... };
}}
```

**Remove these anti-patterns:**
- `pickCookie()` - deprecated, use refreshCookie
- `nextMail()` - randomization is for specs, not demos

---

## Variable Naming That Tells the Story

Bad names hide the exploit. Good names reveal it.

| Bad | Good | Why |
|-----|------|-----|
| `cart` | `cheap_cart_id` | Shows it's the low-price cart in the exploit |
| `order` | `refund_target_id` | Shows this order will be exploited |
| `balance` | `balance_before_exploit` | Shows measurement point |
| `session` | `planktons_session` | Shows whose session (when multiple actors) |

---

## Evaluation Checklist

Before ANY demo edit:

- [ ] No `{{base}}/` or `{{host}}/` prefixes in URLs
- [ ] No `@disabled` directives added
- [ ] `@name` only when truly needed (and with descriptive name)
- [ ] `refreshCookie()` only after login or mutating requests
- [ ] `seedBalance()` not `/account/credits` for reset
- [ ] Item IDs fetched from /menu, not hardcoded
- [ ] File is SHORTER or same length (if longer, justify each line)

---

## See Also

- `demo-conventions` - Technical syntax patterns
- `demo-style-philosophy` - Why less is more
- `http-gotchas` - Assertion pitfalls
