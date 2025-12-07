---
name: demo-conventions
description: Interactive demo conventions for httpyac. Covers response.parsedBody, manual cookie handling, state reset, and student-facing narrative. Auto-invoke when working with vulnerabilities/**/*.http files.
---

# Interactive Demo Conventions (httpyac)

Patterns for `.http` files in `vulnerabilities/.../http/` directories, run with **httpyac** (NOT uctest).

## ⛔⛔⛔ CRITICAL: Read These FIRST ⛔⛔⛔

1. **Style Philosophy:** `.claude/references/demo-style-philosophy.md`
2. **Principles (anti-patterns):** `.claude/skills/demo-principles/SKILL.md`

## The Non-Negotiable Rules

| Rule | Wrong | Right |
|------|-------|-------|
| URL prefix | `GET {{base}}/menu` | `GET /menu` |
| @disabled | Never add | Fix or delete the file |
| @name | `@name cart` → `cart.cart_id` | `@cart_id = {{response.parsedBody.cart_id}}` |
| refreshCookie | After every request | Only after login/mutating POST |
| State reset | `/account/credits` | `seedBalance()` helper |
| Item IDs | `"item_id": "4"` | Fetch from /menu |

**TL;DR:**
- `GET /path` not `GET {{host}}/path` - httpyac auto-prefixes from `@host`
- Every line must justify its existence
- CLEAN > VERBOSE - fewer lines, less noise
- 2-3 console.info max per file, at key state transitions

## Key Differences from E2E Specs

| Aspect | Demo (this skill) | E2E Spec |
|--------|-------------------|----------|
| Runner | `httpyac` | `uctest` |
| Response | `response.parsedBody.field` | `$(response).field("x")` |
| Auth | Raw `Authorization:` header | `{{auth.basic()}}` helpers |
| Cookies | Manual `refreshCookie()` | Auto or `auth.login()` |
| Seeding | `/e2e/balance` endpoint | `platform.seedCredits()` |
| Purpose | Student learning | Automated testing |
| Asserts | 1-2 per request | Multiple OK |

❌ `$(response)` is **undefined** in demos
❌ `auth.basic()` is **unavailable** in demos

## Variable Definition Patterns

**Three patterns, each for a specific use case:**

| Pattern | When to Use | Example |
|---------|-------------|---------|
| `@var = value` | Static config, constants | `@host = {{base_host}}/v203` |
| `@var = {{response...}}` | Simple response capture | `@cart_id = {{response.parsedBody.cart_id}}` |
| `{{ exports.var = ... }}` | Computed values, array ops | `{{ exports.kelp = response.parsedBody.find(...); }}` |

### Static Variables: `@var = value`
```http
@host = {{base_host}}/v203
@initial_balance = 50
@plankton_auth = Basic plankton@chum-bucket.sea:i_love_my_wife
```

### Response Capture: `@var = {{...}}`
```http
POST /cart
Authorization: {{plankton_auth}}

@cart_id = {{response.parsedBody.cart_id}}
```

### Computed/Complex Values: `exports.var`
```http
GET /menu

{{ exports.kelp = response.parsedBody.find(i => i.name.includes("Kelp")); }}

### Later access properties
POST /cart/{{cart_id}}/items
Content-Type: application/json

{"item_id": "{{kelp.id}}"}

{{
  console.info("Ordered:", kelp.name, "for $" + kelp.price);
}}
```

**⚠️ CRITICAL:** `exports.var` is ONLY used inside `{{ }}` JS blocks. Never mix patterns!

## Response Access

```http
# Status check (shorthand)
?? status == 200

# Body field (shorthand)
?? body email == plankton@chum-bucket.sea

# JavaScript form (when math needed)
?? js parseFloat(response.parsedBody.balance) > 100
?? js response.parsedBody.orders.length > 0
```

## Authentication

### Basic Auth (Manual)
```http
@plankton_auth = Basic plankton@chum-bucket.sea:i_love_my_wife

GET /orders
Authorization: {{plankton_auth}}
```

### API Key Auth
```http
@krabs_api_key = key-krusty-krub-z1hu0u8o94

GET /orders
X-API-Key: {{krabs_api_key}}
```

### Cookie Auth (Manual - Explicit Control)

**Cookies are disabled by default** via `httpyac.config.js`:
```javascript
module.exports = {
  cookieJarEnabled: false,
};
```

Use `refreshCookie()` helper **strategically** - NOT after every request:

```http
### Login - ALWAYS capture cookie here
POST /auth/login
Content-Type: application/json

{"email": "plankton@chum-bucket.sea", "password": "i_love_my_wife"}

@session = {{refreshCookie(response)}}

### Use session - NO refreshCookie needed (GET doesn't set cookies)
GET /account/info
Cookie: {{session}}

### Another GET - still NO refreshCookie needed
GET /orders
Cookie: {{session}}

### POST that might update session - refresh here
POST /orders
Cookie: {{session}}
Content-Type: application/json

{"item_id": "1"}

@session = {{refreshCookie(response, session)}}
```

**⛔ CRITICAL: When to use refreshCookie()**

| Request Type | refreshCookie Needed? | Why |
|--------------|----------------------|-----|
| `POST /auth/login` | ✅ YES - always | Sets session cookie |
| `GET /anything` | ❌ NO - never | GET doesn't modify cookies |
| `POST/PUT/PATCH/DELETE` | ⚠️ Rarely | Only if endpoint modifies session (check source code) |

**Adding refreshCookie after every request is NOISE.** It clutters the demo and teaches bad habits.

**refreshCookie() behavior:**
- Returns new cookie if Set-Cookie header present
- Returns existing value if no Set-Cookie header
- Only NEEDED when server actually sends Set-Cookie

## State Reset: E2E vs In-Universe

### In-Universe Endpoints (students see these)
- `POST /account/credits` - Sandy's admin top-up (**increments** balance)
- `POST /orders/refund` - Customer refund request
- Protected by `platform_api_key` or user auth

### E2E Endpoints (for reset/testing only)
- `POST /e2e/balance` - **Sets** balance to exact amount (idempotent!)
- `POST /e2e/reset` - Full database reset
- Protected by `X-E2E-API-Key` header

### Making Demos Idempotent

**⛔⛔⛔ CRITICAL: Use Request-Level Blocks for Setup! ⛔⛔⛔**

Setup code (`seedBalance()`, `mailpit.clear()`, `resetDB()`) MUST be in a **request-level** `{{ }}` block (after `###`), NOT file-level!

```http
# @import ../common/setup.http
@host = {{base_host}}/v203

### Setup: Reset state
{{
  await seedBalance("v203", "plankton@chum-bucket.sea", 100);
  await mailpit.clear();
}}

### First real request...
```

**⚠️ File-level blocks run before EVERY request in the file, not just once!**

```http
# ❌ WRONG - seeds/clears before EVERY request!
@host = {{base_host}}/v203

{{
  await seedBalance("v203", "plankton@chum-bucket.sea", 100);
  await mailpit.clear();  // Deletes emails before step 2!
}}

### Step 1: Get token (email sent)
...

### Step 2: Use token from mailpit
# FAILS! mailpit.clear() ran again!
```

**⚠️ DO NOT use `POST /account/credits` for reset—it increments, not sets!**

## Console.info: Strategic Use Only

**Target:** 2-3 per demo file. See philosophy doc for full guidance.

### ✅ Good Uses

```http
### Check balance before exploit
GET /account/credits
Authorization: {{plankton_auth}}

{{
  exports.balanceBefore = parseFloat(response.parsedBody.balance);
  console.info("💰 Balance BEFORE: $" + response.parsedBody.balance);
}}

### After exploit - summarize impact
GET /account/credits
Authorization: {{plankton_auth}}

?? js parseFloat(response.parsedBody.balance) > {{balanceBefore}}

{{
  console.info("📈 Free food worth $" + order_total + "!");
}}
```

### ❌ Avoid

```http
# Don't echo what assertion already shows
?? body email == plankton@chum-bucket.sea
{{ console.info("Logged in as:", response.parsedBody.email); }}  // REDUNDANT

# Don't narrate every step
{{ console.info("Step 1..."); }}
{{ console.info("Step 2..."); }}  // TOO MANY
```

## Menu Items: Fetch, Don't Hardcode

**Never hardcode item IDs** - fetch from `/menu` and extract dynamically:

```http
# ❌ BAD: Magic number
{"item_id": "6"}

# ❌ STILL BAD: Named magic number (still hardcoded!)
@kelp_shake = 6
{"item_id": "{{kelp_shake}}"}

# ✅ GOOD: Fetch menu, extract dynamically
### Get menu items
GET /menu

{{ exports.kelp = response.parsedBody.find(i => i.name.includes("Kelp")); }}

### Add item to cart
POST /cart/{{cart_id}}/items
Content-Type: application/json

{"item_id": "{{kelp.id}}"}
```

## File Structure

```
vulnerabilities/.../http/
├── common/
│   └── setup.http           # Shared variables, refreshCookie helper
├── httpyac.config.js        # cookieJarEnabled: false
├── e01/
│   ├── e01_*.exploit.http   # Shows vuln succeeds
│   └── e01_*.fixed.http     # Shows fix blocks exploit
├── e02/
│   └── ...
```

## common/setup.http Template

**⚠️ CRITICAL:** The `{{ }}` block must be at FILE LEVEL (no `###` before it) to export `refreshCookie()` globally.

```http
# Section shared setup
@base_host = http://localhost:8000/api

# E2E key for state reset
@e2e_key = e2e-test-key-unsafe-code-lab

# Common actors
@sandy_auth = Basic sandy@bikinibottom.sea:fullStackSquirr3l!
@patrick_auth = Basic patrick@bikinibottom.sea:mayonnaise
@plankton_auth = Basic plankton@chum-bucket.sea:i_love_my_wife
@spongebob_auth = Basic spongebob@krusty-krab.sea:EmployeeOfTheMonth

# Restaurant API keys
@platform_api_key = key-sandy-42841a8d-0e65-41db-8cce-8588c23e53dc
@krabs_api_key = key-krusty-krub-z1hu0u8o94

# ⚠️ NO ### before this block - must be file-level for @import to work!
{{
  /**
   * Extract or refresh session cookie.
   * Returns new cookie if Set-Cookie present, otherwise returns existing.
   */
  exports.refreshCookie = (resp, existing = "") => {
    const raw = resp?.headers?.["set-cookie"];
    if (!raw) return existing;
    const cookieHeader = Array.isArray(raw) ? raw[0] : raw;
    return cookieHeader.split(";")[0];
  };
}}
```

## Narrative Guidelines

### SpongeBob Character Rules
- **Attacker uses THEIR OWN credentials** - never victim's password
- **Plankton** attacks Mr. Krabs/Krusty Krab
- **Squidward** attacks SpongeBob (petty revenge)
- **SpongeBob** is NEVER an attacker

See `spongebob-characters` skill for full character profiles.

### Section Markers (Complexity-Based)

**Simple demos (≤4 requests):** No markers needed - flow is obvious.

**Complex demos (>4 requests, mixed stages):**
```http
# --- Legitimate Usage ---

### Sandy demonstrates normal flow
...


# --- EXPLOIT ---

### Plankton discovers the loophole
...
```

Place marker as standalone `#` comment ABOVE the `###` title.

### exploit.http vs fixed.http

| Aspect | exploit.http | fixed.http |
|--------|--------------|------------|
| Actor | Attacker (Plankton) | Sandy (testing fix) |
| Flow | Same sequence | Same sequence |
| Outcome | Attack succeeds | Attack blocked |

**Parallel structure** makes comparison easy.

### Keep It Simple
- One concept per demo
- Minimal annotations (show, don't tell)
- No technical jargon
- Make impact immediately obvious

## Running Demos

```bash
# Run all requests in file
httpyac path/to/demo.http -a

# Stop at first failure
httpyac path/to/demo.http -a --bail

# Run specific directory
httpyac path/to/e01/ -a --bail
```

## See Also

- `http-syntax` - Core syntax reference
- `http-gotchas` - Critical pitfalls
- `spec-conventions` - E2E spec patterns (different helpers!)
- `spongebob-characters` - Character rules
