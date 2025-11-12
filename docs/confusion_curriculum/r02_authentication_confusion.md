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

Business is growing! Sandy's MVP proved successful. The Krusty Krab loves the platform, and now multiple customers are placing orders daily. SpongeBob and Squidward (Krusty Krab employees) need access to a manager portal to view orders and update statuses.

Sandy adds proper authentication middleware and session management. She introduces cookies for the web UI (better UX than Basic Auth) while keeping API keys for restaurant integrations. She also adds an internal admin API for her own use.

This is where authentication gets interesting: multiple auth methods (Basic Auth, sessions, API keys, admin keys) now coexist in the same codebase. Sandy's middleware needs to handle all of them gracefully.

### Endpoints

| Lifecycle | Method | Path                       | Auth                | Purpose              | Vulnerabilities |
| --------- | ------ | -------------------------- | ------------------- | -------------------- | --------------- |
| v101+     | GET    | /account/credits           | Customer            | View balance         | v202            |
| v202+     | POST   | /account/credits           | Admin               | Add credits          | v202            |
| v101+     | GET    | /menu                      | Public              | List available items |                 |
| v101+     | GET    | /orders                    | Customer/Restaurant | List orders          | v201, v204      |
| v201+     | GET    | /orders/{id}               | Customer/Restaurant | Get single order     |                 |
| v105+     | POST   | /orders/{id}/refund        | Customer            | Request refund       |                 |
| v201+     | PATCH  | /orders/{id}/refund/status | Restaurant          | Update refund status | v203            |
| v103+     | PATCH  | /orders/{id}/status        | Restaurant          | Update order status  |                 |
| v101-v102 | POST   | /orders                    | Customer            | Create new order     | v101, v102      |
| v103+     | POST   | /cart                      | Customer            | Create cart          | v201            |
| v103+     | POST   | /cart/{id}/items           | Customer            | Add item to cart     |                 |
| v103+     | POST   | /cart/{id}/checkout        | Customer            | Checkout cart        | v201            |
| v201+     | GET    | /cart/{id}                 | Customer/Restaurant | Get single cart      |                 |
| v106+     | POST   | /auth/register             | Public              | Register user        | v106, v107      |
| v201+     | POST   | /auth/login                | Public              | Create session       | v205            |
| v201+     | POST   | /auth/logout               | Customer            | Destroy session      |                 |

#### Schema Evolution

| Model/Context        | v201                                   | v202                         | v203                               | v204                               | v205                                      |
| -------------------- | -------------------------------------- | ---------------------------- | ---------------------------------- | ---------------------------------- | ----------------------------------------- |
| RequestContext       | `user_id` copied before auth completes | `+admin_api_key principal`    | `+decorator shortcuts (header only)` | `+user_type flag (customer/manager/internal)` | `Login handler mutates context before password check` |
| Session              | Cookie-backed session introduced       | `+remember manager role`      | -                                  | -                                  | `Session identity overwritten from login payload` |
| AccountCredits       | Read-only balance endpoint             | `+mutation payload (amount, customer)` | -                          | -                                  | -                                           |
| RefundStatusRequest  | -                                      | -                            | `Header-only decorator validation` | -                                  | -                                           |
| LoginRequest         | Base email/password payload            | -                            | -                                  | -                                  | `Context-first assignment triggers contamination` |

#### Data Models

```ts
// Reuse MenuItem, Order, Cart, Refund, and User from r01.

/**
 * Request-scoped authentication context produced by middleware.
 * v201 copies Basic Auth usernames before verification; v204 adds user_type.
 */
interface RequestContext {
  user_id?: string;
  restaurant_id?: string;
  auth_mechanism?: "basic" | "cookie" | "api_key" | "admin_key";
  user_type?: "customer" | "manager" | "internal";
}

/**
 * Cookie session persisted for browser/mobile clients after v201.
 */
interface Session {
  session_id: string;
  user_id: string;
  user_type: "customer" | "manager";
  issued_at: timestamp;
}

/**
 * Payload stored when Sandy (or middleware) mutates account credits.
 * POST /account/credits shares the same structure as the GET body confusion.
 */
interface AccountCreditMutation {
  customer: string; // email
  amount: decimal;
  note?: string;
}

/** Decorators stash header presence only, not validity (v203). */
interface DecoratorState {
  has_customer_auth: boolean;
  has_restaurant_key: boolean;
}

/** Login payload; middleware now mutates sessions before verifying credentials. */
interface LoginRequest {
  email: string;
  password: string;
}

/** Exposed view of individual carts/orders (used by new GET endpoints). */
interface CartDetail extends Cart {
  holds?: decimal; // Authorization layer may place temporary holds before checkout
}
```

#### Request and Response Schemas

```ts
// GET /cart/{id}
type GetCartResponse_v201 = CartDetail;

// GET /orders/{id}
type GetOrderResponse_v201 = Order;

// POST /cart (v201 refresher)
type CreateCartRequest_v201 = CreateCartRequest; // from r01

// POST /cart/{id}/checkout (v201)
type CheckoutCartRequest_v201 = CheckoutCartRequest_v104; // inherits tip + cart_id overwrite bug

// POST /cart/{id}/checkout (context confusion path)
type CheckoutCartContext = {
  request_user_id?: string;   // Set by middleware before auth completes
  session_user_id?: string;   // Derived from cookie
};

// GET /orders (v201)
type ListOrdersRequest_v201 = {
  restaurant_id?: string;
};

// GET /orders (v204 adds polluted user_type)
type ListOrdersRequest_v204 = ListOrdersRequest_v201 & {
  user_type?: "customer" | "manager";
};

// POST /account/credits (v202 admin mutation shares handler with GET)
type PostCreditsRequest_v202 = AccountCreditMutation;

// GET /account/credits (v202 confusion path)
type GetCreditsRequestBody_v202 = AccountCreditMutation; // unexpected body for GET

// PATCH /orders/{id}/refund/status (v203)
type UpdateRefundStatusRequest_v203 = {
  status: "accepted" | "rejected";
  approver?: string;
};

// POST /auth/login
type LoginResponse = {
  session_id: string;
  user_id: string;
  user_type: "customer" | "manager";
};

// POST /auth/logout
type LogoutRequest = {
  session_id: string;
};

// Middleware-shared context snapshot (used by diagnostics/tests)
type AuthDebugPayload = {
  request_user_id?: string;
  cookie_user_id?: string;
  user_type?: string;
};
```

### Authentication Methods

By the end of r02, these authentication methods coexist:

| Method             | Header/Cookie              | Purpose                   | Introduced |
| ------------------ | -------------------------- | ------------------------- | ---------- |
| Admin API Key      | `X-Admin-API-Key: ...`     | Internal admin operations | v202       |
| Basic Auth         | `Authorization: Basic ...` | Legacy customer auth      | v101 (r01) |
| Cookie Session     | `Cookie: session_id=...`   | Web UI customer auth      | v201       |
| Restaurant API Key | `X-API-Key: ...`           | Restaurant integrations   | v101 (r01) |

> [!NOTE]
> Both cookies and API keys can be implemented as JWT tokens if that's more typical for your framework. For now, we're not covering JWT-specific vulnerabilities, so the token format isn't critical. Focus on the authentication logic, not the encoding.

### Vulnerabilities to Implement

#### [v201] Authentication Type Confusion

> Web launch day! Sandy debuts `app.cheeky.sea` with cookie sessions, while legacy clients (tablets, mobile app) stick to Basic Auth. Krusty Krab’s POS still polls `GET /orders` with its API key. The middleware needs to juggle every auth style, which makes Sandy feel a bit anxious, but she considers it an integral part of 'moving fast and breaking things'.

**The Vulnerability**

- Middleware eagerly sets `request.user_id` from the Basic Auth username before verifying the provided password.
- When Basic Auth validation later fails, the code simply falls back to the cookie but leaves the polluted `user_id` in place.
- Handlers trust `request.user_id` because it used to be populated only after auth succeeded (i.e. previously the request would have failed when Basic Auth failed, but now there's a fallback to the cookie - without proper cleanup in between).

**Exploit**

1. Log in normally in the browser to obtain a session cookie.
2. Call `GET /orders` with that cookie plus `Authorization: Basic spongebob@krusty-krab.sea:` (no password).
3. Middleware copies the victim email into context, fails auth, then uses the cookie. However, handlers still see the victim’s ID.

**Impact:** Attacker reads/modifies victim orders and spends their credits. \
**Severity:** 🔴 Critical \
**Endpoints:** `GET /orders`, `POST /cart`, `POST /cart/{id}/checkout`

---

#### [v202] Method Confusion on Shared Handler

> Growing pains: Sandy still tops up customer credits manually. To prepare for a semi-automated backoffice tool, she exposes `POST /account/credits` guarded by her personal `X-Admin-API-Key`, and adds it to the existing `GET /account/credits` handler.

**The Vulnerability**

- The admin guard only runs when `request.method == 'POST'`.
- Sending a GET with a body triggers the credit-addition logic without hitting the admin guard.

**Exploit**

1. Authenticate as a normal customer.
2. Send `GET /account/credits` with body `{ "amount": 500, "customer": "plankton@chum-bucket.sea" }`.
3. Handler skips the admin gate yet executes the credit mutation path, increasing the attacker’s balance.

**Impact:** Unlimited self-awarded credits. \
**Severity:** 🔴 Critical \
**Endpoints:** `GET /account/credits`

_Aftermath: Maintaining separate auth blobs per handler is exhausting, so she extracts decorators (`@authenticated_with("restaurant")`, `@authenticated_with("customer")`) to future-proof the code for multi-tenant growth._

---

#### [v203] Presence ≠ Validity

> Investors keep asking when other restaurants can join. To scale, Sandy makes her decorators “lightweight” so new endpoints can be added quickly.

**The Vulnerability**

1. The `@require_customer_or_restaurant` controller level decorator accepts either a customer cookie or an API key and stops at the first success.
2. The `@authenticated_with("restaurant")` handler level decorator merely ensures `X-API-Key` exists on the request.
3. A request with a valid cookie plus a fake `X-API-Key` passes both layers even though the key was never validated.

**Exploit**

1. Log in as a regular customer and keep the session cookie.
2. Call `PATCH /orders/{id}/refund/status` with header `X-API-Key: fake`.
3. Global middleware authenticates via cookie; decorator sees the header and lets the request call manager-only code.

**Impact:** Customers approve their own refunds as if they were restaurant managers. \
**Severity:** 🟡 High \
**Endpoints:** `PATCH /orders/{id}/refund/status`

_Aftermath: Sandy realizes that she needs a simpler and more reliable way to track user types, so she introduces a `request.user_type` context flag._

---

#### [v204] Auth Context Pollution from Failed Validation

> As Sandy prepares to scale her platform to multiple restaurants, she wants handlers to rely on a single `request.user_type` value ('customer', 'manager', 'internal'). She sets it the moment an API key shows up, then intends to downgrade it if validation fails.

**The Vulnerability**

- When verifying the provided API key, the middleware sets `request.user_type = 'manager'` before running validation.
- If validation fails, it forgets to clear the flag before moving on to Basic Auth validation.
- Manager-only endpoints (`GET /orders` listing all restaurants) read the stale flag and skip additional checks.

**Exploit**

1. Send `X-API-Key: fake` plus a valid Basic Auth credentials to `GET /orders`.
2. Middleware marks the context as `manager`, fails key validation, then authenticates via Basic Auth.
3. Handler sees `request.user_type == 'manager'` and returns all orders across tenants.

**Impact:** Full data disclosure/modification for every restaurant. \
**Severity:** 🟡 High \
**Endpoints:** `GET /orders`

> **Why didn’t testing catch this?** Sandy only regression-tested `PATCH /orders/{id}/refund/status`, whose middleware order (API key -> cookie) cleans up the context. `GET /orders` executes Basic Auth first, so the polluted state survives into handler logic.

_Aftermath: Sandy doubles down on "intelligent" middleware to reduce the amount of micro-managing she needs to do._

---

#### [v205] Login Parameter → Session Contamination

> Sandy refactors her authentication middleware to act more transparently, no matter whether the request is authenticated with Basic Auth, a cookie session or an API key.

**The Vulnerability**

- The new middleware automatically uses request context for Basic Auth & API key requests, and cookie session for cookie requests.
- If a login handler is called with valid cookie session, it will place `session.email` based on the provided value.
- Email/password verification runs _after_ this copy.
- An attacker with a valid cookie can post `{ "email": "plankton@krusty-krab.sea", "password": "wrong" }` and still rewrite the session identity.

**Exploit**

1. Log in as Plankton and keep the session cookie.
2. Call `POST /auth/login` with JSON `{ "email": "spongebob@krusty-krab.sea", "password": "nope" }`.
3. Middleware copies the victim email into the session, fails password check, but leaves the mutated session cookie active. Subsequent requests run as SpongeBob.

**Impact:** Session fixation-style account takeover. \
**Severity:** 🔴 Critical \
**Endpoints:** `POST /auth/login`
