## r02: Authentication Confusion

_Feature focus:_ middleware, sessions, authentication guards and request context \
_Student skill:_ tracing identity through multiple, coexisting authentication mechanisms

### What It Is

Authentication confusion happens when the part that **verifies identity** and the part that **uses identity** disagree. One path checks "Is Alice authenticated?" while another path operates on a user ID that says "Bob."

This is distinct from authorization (which checks permissions). We're talking about basic identity mix-ups: checking the session but using the query string, verifying a JWT claim but trusting a header, validating one auth method but using context from another.

### Framework Features Introduced

- Middleware and request preprocessing
- Request context enrichment (setting `request.user`, `request.user_type`, etc.)
- Session management (cookies)
- Multiple authentication methods coexisting
- Authentication guards and decorators
- HTTP method-specific route handlers

### Why Confusion Happens

- Middleware sets context from one source (headers), business logic reads from another (body/path)
- Multiple authentication methods coexist without proper isolation
- Auth validation happens in one layer, context usage in another
- Middleware enriches context before validation completes
- Presence checks mistaken for validity checks

### The Story

Business is growing! Sandy's MVP proved successful. The Krusty Krab loves the platform, and now multiple customers are placing orders daily. SpongeBob and Squidward (Krusty Krab employees) need access to a merchant portal to view orders and update statuses.

Sandy adds proper authentication middleware and session management. She introduces cookies for the web UI (better UX than Basic Auth) while keeping API keys for restaurant integrations. She also adds an internal admin API for her own use.

This is where authentication gets interesting: multiple auth methods (Basic Auth, sessions, API keys, admin keys) now coexist in the same codebase. Sandy's middleware needs to handle all of them gracefully.

### Authentication Methods

By the end of r02, these authentication methods coexist:

| Method             | Header/Cookie              | Purpose                   | Introduced |
| ------------------ | -------------------------- | ------------------------- | ---------- |
| Basic Auth         | `Authorization: Basic ...` | Legacy customer auth      | v101 (r01) |
| Cookie Session     | `Cookie: session_id=...`   | Web UI customer auth      | v201       |
| Restaurant API Key | `X-API-Key: ...`           | Restaurant integrations   | v101 (r01) |
| Admin API Key      | `X-Admin-API-Key: ...`     | Internal admin operations | v202       |

> [!NOTE]
> Both cookies and API keys can be implemented as JWT tokens if that's more typical for your framework. For now, we're not covering JWT-specific vulnerabilities, so the token format isn't critical. Focus on the authentication logic, not the encoding.

### Endpoints

| Lifecycle |  Method | Path                       | Auth                      | Purpose                      | Vulnerabilities |
| --------- |  ------ | -------------------------- | ------------------------- | ---------------------------- | --------------- |
| v199+     |  GET    | /account/credits           | Customer                  | View balance                 |                 |
| v199+     |  POST   | /auth/register             | Public                    | Register user                |                 |
| v199+     |  POST   | /cart                      | Customer                  | Create cart                  | v201            |
| v199+     |  POST   | /cart/{id}/checkout        | Customer                  | Checkout cart                | v201            |
| v199+     |  POST   | /cart/{id}/items           | Customer                  | Add item to cart             |                 |
| v199+     |  GET    | /menu                      | Public                    | List available menu items    |                 |
| v199+     |  GET    | /orders                    | Customer/Restaurant       | List orders                  | v201, v204      |
| v199+     |  POST   | /orders/{id}/refund        | Customer                  | Request refund               |                 |
| v199+     |  PATCH  | /orders/{id}/refund/status | Restaurant                | Update refund status         | v203            |
| v199+     |  PATCH  | /orders/{id}/status        | Restaurant                | Update order status          |                 |
| v201+     |  POST   | /auth/login                | Public                    | Create session (cookie auth) | v205            |
| v201+     |  POST   | /auth/logout               | Customer                  | Destroy session              |                 |
| v201+     |  GET    | /cart/{id}                 | Customer/Restaurant       | Get single cart              |                 |
| v201+     |  GET    | /orders/{id}               | Customer/Restaurant       | Get single order             |                 |
| v202+     |  POST   | /account/credits           | Admin (`X-Admin-API-Key`) | Add credits to customer      | v202            |

> [!IMPORTANT]
> Cookies may be JWTs, sessions, or signed cookies — format is not the point. Set cookies to `SameSite=Strict` and wire CORS to avoid unintended CSRF, since r02 focuses on **authentication confusion**, not cross-domain vulnerabilities.

> [!TIP] > **Authentication vs Authorization:** Don't add complex authorization yet – that's r03. For now, use simple database-level ownership checks (`WHERE user_id = current_user AND order_id = ?`) to prevent IDORs. r02 focuses on _who you are_ (authentication), not _what you can do_ (authorization).

### Data Models

The core domain models from r01 (MenuItem, Order, Cart, User, Refund) remain unchanged. r02 introduces session management but doesn't modify existing data structures.

```ts
/**
 * Represents an authenticated session (cookie-based).
 * Introduced in v201 to support web UI authentication.
 */
interface Session {
  session_id: string;
  user_id: string;
  email: string; // May be set incorrectly (see v205)
  created_at: timestamp;
  expires_at: timestamp;
}

/**
 * Request context populated by authentication middleware.
 * This is NOT a database model - it's request-scoped state.
 *
 * DANGER: Different middleware may populate this differently,
 * and validation failures may leave stale values.
 */
interface RequestContext {
  user_id?: string; // Set by any auth method
  user_type?: string; // "customer" | "merchant" | "admin"
  email?: string; // Set from session or token
  restaurant_id?: string; // For merchant users
}
```

### Request and Response Schemas

```ts
// POST /auth/login
type LoginRequest = {
  email: string;
  password: string;
};

type LoginResponse = {
  user_id: string;
  session_id: string; // Returned as Set-Cookie header, can be a JWT token as well
};

// POST /auth/logout
type LogoutResponse = {}; // Empty response, clears cookie

// GET /orders/{id}
// Returns the same Order model from r01
type GetOrderResponse = Order;

// GET /cart/{id}
// Returns the same Cart model from r01
type GetCartResponse = Cart;

// POST /account/credits (v202)
type AddCreditsRequest = {
  customer: string; // User ID or email
  amount: decimal;
};

type AddCreditsResponse = {
  customer: string;
  amount: decimal;
  balance: decimal; // New balance after credit added
};
```

### Vulnerabilities to Implement

#### [v201] Authentication Type Confusion

**Scenario:** Sandy implements Cookie-based sessions for the UI, but keeps Basic Auth for backwards compatibility.

**The Bug:**

- Middleware sets `request.user_id` from Basic Auth username before validating credentials.
- Attacker provides valid Cookie (own account) and invalid Basic Auth header (victim's username, no password), bypassing validation.

**Impact:** Attacker accesses victim's orders and spends their credits. \
**Severity:** 🔴 Critical

**Endpoints:** `GET /orders`, `POST /cart`, `POST /cart/{id}/checkout`

---

#### [v202] Method Confusion on shared handler

**Scenario:** Sandy creates an internal admin endpoint (`POST /account/credits`) to add credits to customer accounts. She protects it with her `X-Admin-API-Key`, which only she has. The endpoint is marked as POST-only, but she wants to reuse the handler for viewing credits via GET (regular customer auth required for viewing your own balance).

**The Bug:**

- Auth check ties to POST method only.
- Shared handler parses body on GET (many frameworks allow this), executing add logic without auth.

**Impact:** Attacker can add unlimited credits to their own account, essentially stealing money from the platform. \
**Severity:** 🔴 Critical

**Endpoints:** `GET /account/credits` (exploited via body)

---

#### [v203] Presence ≠ Validity

**Scenario:** Sandy needs to protect merchant-only endpoints, like approving refunds. This must be called with a valid restaurant `X-API-Key`.

**The Bug:** The request goes through two checks:

1. A global auth middleware checks for _any_ valid authentication (a customer cookie _or_ an API key).
2. A route-specific decorator checks _only for the presence_ of the `X-API-Key` header (e.g., `if 'X-API-Key' in request.headers:`), assuming the global middleware already validated it.

**Impact:** Attacker uses valid customer cookie + fake key to approve own refunds as merchant. \
**Severity:** 🟡 High

**Endpoints:** `PATCH /orders/{id}/refund/status`

---

#### [v204] Auth Context Pollution from Failed Validation

**Scenario:** Frustrated by the `v203` bug, Sandy refactors her auth middleware. She makes it "smarter" by setting a `user_type = 'merchant'` flag on the request context so that handlers can simply check it. This is meant to simplify things and avoid repetitive validity checks in every decorator. She also remembers to verify that the v203 vulnerability **is not present** anymore, dynamically.

**The Bug:** The middleware logic is flawed:

1. See `X-API-Key`, set `request.user_type = 'merchant'`.
2. Try to validate the key.
3. If validation fails, it _forgets to reset_ `request.user_type` and moves on to check for a cookie, which succeeds.
4. The `GET /orders` handler later trusts this `user_type` variable to show all merchant orders.

**Impact:** The same attack scenario repeats: Plankton still can bypass the auth check by providing a valid customer cookie and a fake `X-API-Key` header. The handler sees `user_type == 'merchant'` and leaks _all_ restaurant orders. \
**Severity:** 🟡 High

**Endpoints:** `GET /orders`

> [!IMPORTANT]
> **Why didn't Sandy catch this during testing?**
> Sandy tested the exact endpoint that was vulnerable to v203, but didn't regression test OTHER merchant endpoints.
> The `PATCH /orders/{id}/refund/status` endpoint is had different middleware order: 1) api key; 2) basic auth; 3) cookie. Basic Auth validation masked the weakness introduced in api key handling, by cleaning up the request context on failure.
> The `GET /orders` endpoint had a different middleware order: 1) basic auth; 2) api key; 3) cookie (or maybe Basic Auth is completely skipped for this endpoint?), so cookie validation operates on a polluted context, leading to vulnerability.

---

#### [v205] Login parameter→session contamination

**Scenario:** Sandy refactors her middleware to be more uniform and now it "intelligently" abstracts both request context and persistent session data, based on the authentication method used (cookie / basic auth / API key).

**The Bug:** The login handler populates `email` claim based on the `request.json['email']` value, aiming to store it in the request context (the login requests are not expected to contain any cookies). But if there is a valid cookie session, the `session.email` claim will be updated instead – before the email validation.

**Impact:** Plankton logs in into his own account, and then repeats the login request – this time with a victim's email in the body. The middleware updates the session `email` claim to `spongebob@krusty-krab.sea`. Follow-up requests with this cookie will authorize Plankton as `spongebob@krusty-krab.sea`. \
**Severity:** 🔴 Critical

**Endpoints:** `POST /auth/login`
