## r02: Authentication Confusion

_Feature focus:_ middleware, sessions, authentication guards and request context \
_Student skill:_ tracing identity through multiple, coexisting authentication mechanisms

### What It Is

Authentication confusion happens when the part that **verifies identity** and the part that **uses identity** disagree. One path checks "Is Alice authenticated?" while another path operates on a user ID that says "Bob."

This is distinct from authorization (which checks permissions). We're talking about basic identity mix-ups: checking the session but using the query string, verifying a JWT claim but trusting a header, validating one auth method but using context from another.

### Framework Features Introduced

- Middleware and request preprocessing
- Request context enrichment (setting `request.user`, `request.auth_context`, etc.)
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

| Lifecycle | Method | Path                          | Auth                | Purpose                  | Vulnerabilities |
| --------- | ------ | ----------------------------- | ------------------- | ------------------------ | --------------- |
| v101+     | GET    | /account/credits              | Customer            | View balance             | v202            |
| v101+     | GET    | /account/info                 | Customer            | View profile+order stats |                 |
| v202+     | POST   | /account/credits              | Admin               | Add credits              | v202            |
| v101+     | GET    | /menu                         | Public              | List available items     |                 |
| v101+     | GET    | /orders                       | Customer/Restaurant | List orders              | v201, v204      |
| v105+     | POST   | /orders/{id}/refund           | Customer            | Request refund           |                 |
| v203+     | PATCH  | /orders/{id}/refund/status    | Restaurant          | Approve/reject refunds   | v203            |
| v203+     | GET    | /orders/{id}/refund/status    | Customer/Restaurant | Fetch refund decision    |                 |
| v103+     | POST   | /cart                         | Customer            | Create cart              | v201            |
| v103+     | POST   | /cart/{id}/items              | Customer            | Add item to cart         |                 |
| v103+     | POST   | /cart/{id}/checkout           | Customer            | Checkout cart            | v201            |
| v106+     | POST   | /auth/register                | Public              | Register user            | v106, v107      |
| v201+     | POST   | /auth/login                   | Public              | Create session           | v205            |
| v201+     | POST   | /auth/logout                  | Customer            | Destroy session          |                 |

#### Schema Evolution

##### Data Model Evolution

| Model               | v201                                                | v202 | v203 | v204 | v205 |
| ------------------- | --------------------------------------------------- | ---- | ---- | ---- | ---- |
| RequestContext      | Authenticators hydrate `g.email/g.user` pre-check   | -    | -    | API-key authenticators set `g.auth_context` + `g.manager_request` before validation | -    |
| Session             | Cookie session stores `email` for browser requests  | -    | -    | -    | -    |
| AccountCredits      | Read-only balance endpoint                          | Shared GET/POST handler mutates balances via form fields `user`/`amount` | -    | -    | -    |
| RefundStatusRequest | -                                                   | -    | Form body `status` drives manager decisions without revalidating API keys | -    | -    |
| LoginRequest        | Base email/password payload                         | -    | -    | -    | Handler trusts JSON email even when authenticator short-circuits via cookie |

##### Behavioral Changes

| Version | Component              | Behavioral Change                                                                  |
| ------- | ---------------------- | ---------------------------------------------------------------------------------- |
| v201    | CustomerAuthenticator  | `authenticate_customer()` instantiates cookie + Basic authenticators up front      |
| v201    | CredentialAuthenticator| Basic constructor sets `g.email/g.user` before password verification               |
| v202    | AccountCredits         | Admin guard only runs when `request.method == 'POST'`                              |
| v203    | RefundStatusRequest    | Blueprint guard validates auth; handler helper only checks header presence         |
| v204    | RequestContext         | `RestaurantAuthenticator` sets `g.manager_request = True` as soon as header exists |
| v204    | RequestContext         | Failed API key validation doesn't clear `g.manager_request` before Basic fallback  |
| v205    | LoginHandler           | Customer authenticator short-circuits on existing session; handler still copies request email into session |

#### Data Models

```ts
// Reuse MenuItem, Order, Cart, Refund, and User from r01.

interface RequestContext {
  email?: string;
  user?: User;
  name?: string;
  balance?: decimal;
  order?: Order;
  email_confirmed?: boolean;
  refund_is_auto_approved?: boolean;
  auth_context?: "customer" | "manager" | "platform";
  manager_request?: boolean;
  customer_request?: boolean;
  platform_request?: boolean;
  authenticated_customer?: boolean;
  authenticated_manager?: boolean;
  authenticated_platform?: boolean;
}

interface Session {
  email?: string;
}

/**
 * Payload used by POST /account/credits and (incorrectly) honored by GET when sent as form data.
 */
interface AccountCreditMutation {
  user: string;
  amount: decimal;
}

/**
 * Manager-only refund status updates.
 */
interface RefundStatusUpdate {
  status: "approved" | "rejected";
}

/** Login payload used by the JSON form + Basic Auth fallback. */
interface LoginRequest {
  email: string;
  password: string;
}
```

#### Request and Response Schemas

```ts
// GET /account/credits
type ViewCreditsResponse_v201 = {
  email: string;
  balance: string;
};

// POST /account/credits
type PostCreditsRequest_v202 = AccountCreditMutation;
type PostCreditsResponse_v202 = ViewCreditsResponse_v201;

// GET /account/info
type ViewAccountInfoResponse_v201 = {
  email: string;
  name: string;
  balance: string;
  orders: number;
};

// GET /orders
type ListOrdersResponse_v201 = Order[];

// POST /cart
type CreateCartResponse_v201 = Cart;

// POST /cart/{id}/items
type AddCartItemRequest_v201 = {
  item_id: string;
};

// POST /cart/{id}/checkout
type CheckoutCartRequest_v201 = {
  delivery_address: string;
  tip?: decimal;
};

// POST /orders/{id}/refund
type RefundOrderRequest_v201 = {
  amount?: decimal;
  reason?: string;
};

// PATCH /orders/{id}/refund/status
type UpdateRefundStatusRequest_v203 = RefundStatusUpdate;
type RefundStatusResponse_v203 = Refund;

// GET /orders/{id}/refund/status shares RefundStatusResponse_v203

// POST /auth/login
type LoginResponse_v201 = {
  message: string; // "Login successful"
};

// POST /auth/logout
type LogoutResponse_v201 = {
  message: string; // "Logout successful"
};
```

### Vulnerabilities to Implement

#### [v201] Session Hijack via Auth Mixup

> Web launch day! Sandy debuts `app.cheeky.sea` with cookie sessions for the website while keeping Basic Auth support for the mobile app. Supporting both authentication methods simultaneously means instantiating both authenticators in her helper—she figures the `any()` check will handle which one succeeds.

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

_Aftermath: The app is getting crowded. Sandy splits her monolithic routes file into separate blueprints by domain (`routes/account.py`, `routes/orders.py`, etc.) to keep things organized as she adds more features._

---

#### [v202] Credit Top-Ups via GET

> Sandy needs to top up customer credits manually while she builds proper payment integration. Rather than create a separate admin endpoint, she adds POST support to the existing `GET /account/credits` route—one handler, two auth paths, less duplication.

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

_Aftermath: Sandy notices she's decorating every orders endpoint with authentication checks. She adds a blueprint-level `@bp.before_request` guard to handle auth once for all routes, keeping handlers cleaner._

---

#### [v203] Fake Header Refund Approvals

> Investors keep asking when other restaurants can join. Sandy knows she'll be adding lots of manager endpoints soon, so she splits authentication into two layers: a blueprint guard that validates credentials once, and a lightweight `authenticated_with()` helper that just checks which role was used.

**The Vulnerability**

1. The blueprint-level `@bp.before_request` guard accepts either a customer cookie or an API key and stops at the first success.
2. The handler-level `authenticated_with("restaurant")` helper literally checks `if "x-api-key" in request.headers`—it never re-validates the key's value.
3. A request with a valid cookie plus a fake `X-API-Key` therefore passes both layers even though the key was never validated.

**Exploit**

1. Log in as a regular customer and keep the session cookie.
2. Call `PATCH /orders/{id}/refund/status` with header `X-API-Key: fake`.
3. Global middleware authenticates via cookie; decorator sees the header and lets the request call manager-only code.

**Impact:** Customers approve their own refunds as if they were restaurant managers. \
**Severity:** 🟠 High \
**Endpoints:** `PATCH /orders/{id}/refund/status`

_Aftermath: Sandy wants handlers to branch on auth type without re-checking credentials. She refactors authenticators to set `g.manager_request` flags early, letting handlers know what kind of request they're processing._

---

#### [v204] Manager Mode Stuck After Bad Key

> As Sandy prepares for multi-tenancy, she builds a unified `@require_auth()` decorator that accepts a list of allowed methods. Authenticators set context flags like `g.manager_request` in their constructors so handlers can branch on auth type—if validation fails, the decorator won't call the handler anyway.

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

> **Why didn't testing catch this?** Sandy regression-tested `PATCH /orders/{id}/refund/status`, which requires a restaurant API key and therefore fails outright when the key is bad. `GET /orders` allows Basic Auth as a fallback, so once the invalid key sets `g.manager_request`, the later Basic Auth success leaves the flag in place.

_Aftermath: Sandy's decorator API still requires listing multiple customer auth methods (`["cookies", "basic_auth"]`). She wants to simplify this—why not merge all customer authentication into a single class that tries multiple methods internally?_

---

#### [v205] Session Overwrite via Login Form

> Sandy merges her separate authenticator classes into a unified `CustomerAuthenticator` that internally tries session auth, then Basic Auth, then JSON credentials. Now she can use `@require_auth(["customer"])` everywhere instead of listing three different methods—and the login handler can reuse the same authenticator for validation.

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
