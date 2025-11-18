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

##### Data Model Evolution

| Model               | v201                        | v202                                   | v203 | v204 | v205 |
| ------------------- | --------------------------- | -------------------------------------- | ---- | ---- | ---- |
| RequestContext      | ✅ (new entity)             | `+admin_api_key principal`             | -    | -    | -    |
| Session             | ✅ (cookie-backed)          | `+manager role field`                  | -    | -    | -    |
| AccountCredits      | Read-only balance endpoint  | `+mutation payload (amount, customer)` | -    | -    | -    |
| RefundStatusRequest | -                           | -                                      | -    | -    | -    |
| LoginRequest        | Base email/password payload | -                                      | -    | -    | -    |

##### Behavioral Changes

| Version | Component           | Behavioral Change                                                                  |
| ------- | ------------------- | ---------------------------------------------------------------------------------- |
| v201    | RequestContext      | Middleware copies `user_id` from Basic Auth username before password verification  |
| v201    | RequestContext      | Failed Basic Auth falls back to cookie without clearing polluted `user_id`         |
| v202    | AccountCredits      | Admin guard only runs when `request.method == 'POST'`                              |
| v203    | RefundStatusRequest | Controller decorator validates auth; handler decorator only checks header presence |
| v204    | RequestContext      | Middleware sets `user_type = 'manager'` before validating API key                  |
| v204    | RequestContext      | Failed API key validation doesn't clear `user_type` before Basic Auth fallback     |
| v205    | LoginRequest        | Middleware copies request email into session before password verification          |

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
  request_user_id?: string; // Set by middleware before auth completes
  session_user_id?: string; // Derived from cookie
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

### Vulnerabilities to Implement

#### [v201] Session Hijack via Auth Mixup

> Web launch day! Sandy debuts `app.cheeky.sea` with cookie sessions, while legacy clients (tablets, mobile app) stick to Basic Auth. Krusty Krab’s POS still polls `GET /orders` with its API key. The middleware needs to juggle every auth style, which makes Sandy feel a bit anxious, but she considers it an integral part of 'moving fast and breaking things'.

**The Vulnerability**

- `authenticate_customer()` instantiates both the cookie authenticator and the Basic Auth authenticator before checking whether either one succeeds.
- The Basic Auth authenticator copies its username into `g.email` (and loads that user) in its constructor, before the password is ever verified.
- The generator short-circuits as soon as the cookie authenticator succeeds, so the poisoned `g.email` from the failed Basic Auth attempt survives into handler logic.

**Exploit**

1. Log in normally in the browser to obtain a session cookie.
2. Call `GET /orders` with that cookie plus `Authorization: Basic spongebob@krusty-krab.sea:nope`.
3. The Basic authenticator copies SpongeBob’s email into context, the cookie authenticator returns True, and handlers read SpongeBob’s orders while charging your account.

**Impact:** Attacker reads/modifies victim orders and spends their credits. \
**Severity:** 🔴 Critical \
**Endpoints:** `GET /orders`, `POST /cart`, `POST /cart/{id}/checkout`

---

#### [v202] Credit Top-Ups via GET

> Growing pains: Sandy still tops up customer credits manually. To prepare for a semi-automated backoffice tool, she exposes `POST /account/credits` guarded by her personal `X-Admin-API-Key`, and adds it to the existing `GET /account/credits` handler.

**The Vulnerability**

- The admin guard only runs when `request.method == 'POST'`.
- After the method check, any request that carries `user` and `amount` in `request.form` drops into the credit-addition branch—regardless of verb.

**Exploit**

1. Authenticate as a normal customer.
2. Send `GET /account/credits` with `Content-Type: application/x-www-form-urlencoded` and body `user=plankton@chum-bucket.sea&amount=500`.
3. The GET path never hits the admin gate yet still executes the credit mutation path, increasing the attacker’s balance.

**Impact:** Unlimited self-awarded credits. \
**Severity:** 🔴 Critical \
**Endpoints:** `GET /account/credits`

_Aftermath: Maintaining separate auth blobs per handler is exhausting, so she extracts decorators (`@authenticated_with("restaurant")`, `@authenticated_with("customer")`) to future-proof the code for multi-tenant growth._

---

#### [v203] Fake Header Refund Approvals

> Investors keep asking when other restaurants can join. To scale, Sandy makes her decorators “lightweight” so new endpoints can be added quickly.

**The Vulnerability**

1. The `@require_customer_or_restaurant` controller-level guard accepts either a customer cookie or an API key and stops at the first success.
2. The handler-level `authenticated_with("restaurant")` helper literally checks `if "x-api-key" in request.headers`—it never re-validates the key’s value.
3. A request with a valid cookie plus a fake `X-API-Key` therefore passes both layers even though the key was never validated.

**Exploit**

1. Log in as a regular customer and keep the session cookie.
2. Call `PATCH /orders/{id}/refund/status` with header `X-API-Key: fake`.
3. Global middleware authenticates via cookie; decorator sees the header and lets the request call manager-only code.

**Impact:** Customers approve their own refunds as if they were restaurant managers. \
**Severity:** 🟠 High \
**Endpoints:** `PATCH /orders/{id}/refund/status`

_Aftermath: Sandy realizes that she needs a simpler and more reliable way to track user types, so she introduces a `request.user_type` context flag._

---

#### [v204] Manager Mode Stuck After Bad Key

> As Sandy prepares to scale her platform to multiple restaurants, she wants handlers to rely on a single `request.user_type` value ('customer', 'manager', 'internal'). She sets it the moment an API key shows up, then intends to downgrade it if validation fails.

**The Vulnerability**

- The shared `@require_auth(["cookies","restaurant_api_key","basic_auth"])` decorator instantiates the restaurant authenticator whenever an `X-API-Key` header appears.
- That authenticator sets `g.manager_request = True` up front so handlers can tell a manager flow is in progress, then runs the HMAC comparison.
- When the key is invalid the authenticator returns `False`, but nobody clears `g.manager_request` before the Basic Auth authenticator runs.
- Manager endpoints (like `GET /orders`) check `g.manager_request` to decide whether to return all tenants, so a stale flag after a failed key lets any Basic Auth user read every order.

**Exploit**

1. Send `X-API-Key: fake` plus a valid Basic Auth credentials to `GET /orders`.
2. Middleware marks the context as `manager`, fails key validation, then authenticates via Basic Auth.
3. Handler sees `g.manager_request` still set and returns all orders across tenants.

**Impact:** Full data disclosure/modification for every restaurant. \
**Severity:** 🟠 High \
**Endpoints:** `GET /orders`

> **Why didn’t testing catch this?** Sandy regression-tested `PATCH /orders/{id}/refund/status`, which requires a restaurant API key and therefore fails outright when the key is bad. `GET /orders` allows Basic Auth as a fallback, so once the invalid key sets `g.manager_request`, the later Basic Auth success leaves the flag in place.

_Aftermath: Sandy doubles down on "intelligent" middleware to reduce the amount of micro-managing she needs to do._

---

#### [v205] Session Overwrite via Login Form

> Sandy refactors her authentication middleware to act more transparently, no matter whether the request is authenticated with Basic Auth, a cookie session or an API key.

**The Vulnerability**

- The login form now reuses the unified `CustomerAuthenticator` to “validate” credentials instead of checking the JSON body directly.
- That authenticator always tries the session cookie first; if you’re already logged in, `authenticate()` returns `True` before it ever inspects the JSON email/password.
- The handler assumes the JSON credentials were validated and blindly sets `session["email"] = request.json["email"]`.
- A logged-in attacker can therefore rebind their session to any email address without knowing the password.

**Exploit**

1. Log in as Plankton and keep the session cookie.
2. Call `POST /auth/login` with JSON `{ "email": "spongebob@krusty-krab.sea", "password": "nope" }`.
3. The authenticator short-circuits on your existing cookie, the handler still overwrites `session.email` with SpongeBob, and future requests run as the victim.

**Impact:** Session fixation-style account takeover. \
**Severity:** 🔴 Critical \
**Endpoints:** `POST /auth/login`
