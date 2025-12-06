# Interactive Demo Conventions (httpyac)

Single-source rules for `.http` demos under `vulnerabilities/.../http/`, executed with **httpyac**. These are student-facing narratives that demonstrate vulnerabilities and fixes.

---

## File Locations & Naming
```
vulnerabilities/python/flask/confusion/webapp/
├── r0N_*/http/
│   ├── common/setup.http
│   ├── eNN/
│   │   ├── eNN_name.exploit.http   # Demonstrates vulnerability succeeds
│   │   └── eNN_name.fixed.http     # Demonstrates fix blocks exploit
│   └── httpyac.config.js           # cookieJarEnabled: false
```

---

## Response Access & Assertions
- Status shorthand: `?? status == 200`
- Body shorthand: `?? body email == plankton@chum-bucket.sea`
- JS form: `?? js parseFloat(response.parsedBody.balance) > 100`
- Never use `$(response)` in demos (undefined).

Minimum expectations:
- `exploit.http`: status assertion AND proof exploit succeeded (wrong data, price mismatch, or balance increase).
- `fixed.http`: status assertion AND proof exploit blocked (correct data, correct price, or explicit 403/denial).
- One assert per request to keep focus on impact.

---

## Authentication Patterns

### Basic Auth
```http
@plankton_auth = Basic plankton@chum-bucket.sea:i_love_my_wife
GET /orders
Authorization: {{plankton_auth}}
```

### API Keys
```http
@krabs_api_key = key-krusty-krab-z1hu0u8o94
GET /orders
X-API-Key: {{krabs_api_key}}
```

### Cookie Auth (Manual)
Cookies are disabled by default (`cookieJarEnabled: false`).
```http
### Login - capture cookie
POST /auth/login
Content-Type: application/json
{"email": "plankton@chum-bucket.sea", "password": "i_love_my_wife"}

@session = {{refreshCookie(response)}}

### Use session
GET /orders
Cookie: {{session}}

### Mutating POST - refresh if needed
POST /orders
Cookie: {{session}}
Content-Type: application/json
{"item_id": "1"}

@session = {{refreshCookie(response, session)}}
```
`refreshCookie` is only needed after login or mutating requests that set cookies; never after GET.

---

## State Management
- Use helpers for reset, never in-universe endpoints.
```http
{{
  await seedBalance("v203", "plankton@chum-bucket.sea", 100);  # Idempotent
}}
{{ await resetDB("v301"); }}  # Full reset
```
- **Never** use `/account/credits` for reset (it increments).

---

## Menu Items: Fetch, Don't Hardcode
```http
# WRONG
{"item_id": "6"}

# CORRECT
GET /menu
{{ exports.kelp = response.parsedBody.find(i => i.name.includes("Kelp")); }}

### Add to cart
POST /cart/{{cart_id}}/items
Content-Type: application/json
{"item_id": "{{kelp.id}}"}
```

---

## console.info Usage
Target 2–3 per demo at key transitions.
- Good: balance before/after, explicit exploit/fix impact messages.
- Avoid redundancy (don't echo assertions) and avoid log spam.

### Post-Request Ordering
```http
### Request
GET /endpoint
Authorization: {{plankton_auth}}

@session = {{refreshCookie(response, session)}}     # 1. Session first
@cart_id = {{response.parsedBody.cart_id}}          # 2. Captures

?? body email == plankton@chum-bucket.sea           # 3. Assertion

{{                                                # 4. console.info last
  console.info("💰 Balance: $" + response.parsedBody.balance);
}}
```

---

## Narrative Guidelines
- Titles are behavioral: `### EXPLOIT: Plankton reads Patrick's order history` (not technical jargon).
- Impacts are business-focused: describe what the attacker gained.
- Keep exploit/fix flows parallel; `fixed.http` mirrors `exploit.http` with different outcome.
- Use section markers (`# --- Legitimate Usage ---` / `# --- EXPLOIT ---`) for long files (>4 requests).

---

## Anti-Patterns
| Pattern | Problem | Do Instead |
|---------|---------|------------|
| `GET {{host}}/orders` | Redundant host | `GET /orders` (httpyac prefixes) |
| `@disabled` | Hides problems | Fix the root cause |
| `@name cart` → `cart.cart_id` | Indirect and brittle capture | `@cart_id = {{response.parsedBody.cart_id}}` |
| `refreshCookie` after GET | No effect | Only after login/mutating POST |
| Using `/account/credits` for reset | Non-idempotent | `seedBalance()` |
| Hardcoded menu IDs | Brittle | Fetch from `/menu` |
| 7+ `console.info` | Noise | Use 2–3 meaningful logs |

---

## Running Demos
```bash
# Wrapper (recommended)
ucdemo r02           # All demos in section 02
ucdemo r02/e03 --bail
ucdemo . -k          # Current directory, keep going

# Direct httpyac
httpyac path/to/demo.http -a
httpyac path/to/demo.http -a --bail
```
