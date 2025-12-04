---
name: demo-conventions
description: Interactive demo conventions for httpyac. Covers response.parsedBody, manual cookie handling, state reset, and student-facing narrative. Auto-invoke when working with vulnerabilities/**/*.http files.
---

# Interactive Demo Conventions (httpyac)

Patterns for `.http` files in `vulnerabilities/.../http/` directories, run with **httpyac** (NOT uctest).

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

GET {{host}}/orders
Authorization: {{plankton_auth}}
```

### API Key Auth
```http
@krabs_api_key = key-krusty-krub-z1hu0u8o94

GET {{host}}/orders
X-API-Key: {{krabs_api_key}}
```

### Cookie Auth (Manual - NEW CONVENTION)

**Cookies are disabled by default** via `httpyac.config.js`:
```javascript
module.exports = {
  cookieJarEnabled: false,
};
```

Use `refreshCookie()` helper for session management:

```http
### Login
# @name login
POST {{host}}/auth/login
Content-Type: application/json

{"email": "plankton@chum-bucket.sea", "password": "i_love_my_wife"}

@session = {{refreshCookie(login)}}

### Use session
GET {{host}}/account/info
Cookie: {{session}}

@session = {{refreshCookie(response, session)}}

### Another request using updated session
GET {{host}}/orders
Cookie: {{session}}
```

**refreshCookie() behavior:**
- Returns new cookie if Set-Cookie header present
- Returns existing value if no Set-Cookie header
- Allows seamless session updates through request chain

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

Use E2E endpoint at demo start to reset state:

```http
@e2e_key = e2e-test-key-unsafe-code-lab

### Reset Plankton's balance for demo
POST {{host}}/e2e/balance
X-E2E-API-Key: {{e2e_key}}
Content-Type: application/json

{"user_id": "plankton@chum-bucket.sea", "balance": 100}

?? status == 200
```

**⚠️ DO NOT use `POST /account/credits` for reset—it increments, not sets!**

## Console.info for State Transitions

Make hidden state visible to students:

```http
### Check balance before exploit
# @name before
GET {{host}}/account/credits
Authorization: {{plankton_auth}}

{{
  console.info(`💰 Plankton's balance BEFORE: $${response.parsedBody.balance}`);
}}

### [EXPLOIT HAPPENS HERE]
...

### Check balance after exploit
GET {{host}}/account/credits
Authorization: {{plankton_auth}}

{{
  const after = response.parsedBody.balance;
  console.info(`💰 Plankton's balance AFTER: $${after}`);
  console.info(`📈 Gained: $${after - before.balance} (should not be possible!)`);
}}

?? js parseFloat(response.parsedBody.balance) > {{parseFloat(before.balance)}}
```

## Named Variables for Magic Numbers

Replace magic numbers with descriptive variables:

```http
# ❌ BAD: What is 6?
POST {{host}}/cart/{{cart_id}}/items
Content-Type: application/json

{"item_id": "6"}

# ✅ GOOD: Self-documenting
@kelp_shake = 6

POST {{host}}/cart/{{cart_id}}/items
Content-Type: application/json

{"item_id": "{{kelp_shake}}"}
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

```http
# @title Section shared setup
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

### Exploit Narrative Flow
1. Show legitimate usage (optional)
2. Clear marker: `### --- EXPLOIT ---`
3. Attacker performs attack with their own auth
4. Assertion proves attack succeeded
5. Show business impact (balance changed, data accessed)

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
