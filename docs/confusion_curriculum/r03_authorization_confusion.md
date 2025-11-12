## r03: Authorization Confusion

_Feature focus:_ authorization decorators, resource loading and ownership checks \
_Student skill:_ comparing permission checks vs. action targets, spotting inconsistent resource resolution

### What It Is

Authorization confusion happens when the code that **checks permissions** examines a different resource or identity than the code that **performs the action**. The check might ask "Can Alice access document X?" while the action operates on document Y.

Unlike authentication confusion (identity mix-ups), this is about access control: the identity is correct, but the permission check and the business logic disagree on which resource is being accessed.

### Framework Features Introduced

- Authorization decorators/middleware
- Resource loading
- Relationship traversal
- Permission checking
- Database queries with filters

### Why Confusion Happens

- Permission checks load/resolve resources independently from business logic
- Indirect references (e.g., IDs) resolved differently between check and action
- Parent-child assumptions break under adversarial input
- Checks run before/after data merging/normalization
- "Helpful" defaults or fallbacks in checks lead to fail-open

### The Story

The platform is maturing! Sandy adds multi-tenancy support: restaurants can customize menus, manage items, and update settings. Mr. Krabs wants control over his restaurant's data without Sandy's help.

Squidward gets jealous of SpongeBob getting employee-of-the-month. Plankton intensifies gets signs up Chum Bucket as the next Cheeky SaaS customer and intensifies his attacks, probing for ways to sabotage the Krusty Krab from within the platform.

This introduces proper authorization: ownership checks, roles (customer, manager, admin), and resource scoping. Authentication methods from r02 (cookies, API keys) remain, but now handlers must verify not just _who_ you are, but _what_ you can access.

### Authorization Roles

By the end of r03, these roles are enforced:

| Role     | Description                                      | Auth Methods    |
| -------- | ------------------------------------------------ | --------------- |
| Public   | No authentication required                       | None            |
| Customer | Regular users placing orders                     | Cookie          |
| Manager  | Restaurant staff (auto-assigned by email domain) | Cookie/API Key  |
| Admin    | Platform admins                                  | X-Admin-API-Key |

### Endpoints

| Lifecycle | Method | Path                       | Auth                | Purpose                       | Vulnerabilities  |
| --------- | ------ | -------------------------- | ------------------- | ----------------------------- | ---------------- |
| v101+     | GET    | /account/credits           | Customer            | View balance                  | v202             |
| v202+     | POST   | /account/credits           | Admin               | Add credits                   | v202             |
| v101+     | GET    | /menu                      | Public              | List available items          |                  |
| v101+     | GET    | /orders                    | Customer/Restaurant | List orders                   | v201, v204, v304 |
| v201+     | GET    | /orders/{id}               | Customer/Restaurant | Get single order              | v305             |
| v105+     | POST   | /orders/{id}/refund        | Customer            | Request refund                | v105             |
| v201+     | PATCH  | /orders/{id}/refund/status | Restaurant          | Update refund status          | v301             |
| v103+     | PATCH  | /orders/{id}/status        | Restaurant          | Update order status           | v305             |
| v103+     | POST   | /cart/{id}/checkout        | Customer            | Checkout cart                 | v302             |
| v103+     | POST   | /cart/{id}/items           | Customer            | Add item to cart              |                  |
| v303+     | PATCH  | /menu/items/{id}           | Restaurant          | Update menu item              | v303, v405       |
| v306+     | POST   | /restaurants               | Public              | Register restaurant + API key | v306             |
| v307+     | PATCH  | /restaurants/{id}          | Manager             | Update restaurant profile     | v307             |

#### Schema Evolution

##### Data Model Evolution

| Model                | v301 | v302               | v303 | v304 | v305 | v306                       | v307                     |
| -------------------- | ---- | ------------------ | ---- | ---- | ---- | -------------------------- | ------------------------ |
| AuthorizationContext | ✅   | -                  | -    | -    | -    | -                          | -                        |
| CartAuthorization    | -    | `+session.cart_id` | -    | -    | -    | -                          | -                        |
| MenuItem             | -    | -                  | -    | -    | -    | -                          | -                        |
| Restaurant           | -    | -                  | -    | -    | -    | ✅ (domain onboarding)     | `+domain PATCH mutation` |
| DomainToken          | -    | -                  | -    | -    | -    | ✅ (user token reuse path) | -                        |

##### Behavioral Changes

| Version | Component                      | Behavioral Change                                                                        |
| ------- | ------------------------------ | ---------------------------------------------------------------------------------------- |
| v301    | AuthorizationContext           | `has_access_to(order)` trusts merged principals from multiple auth methods               |
| v302    | CartAuthorization              | Authorization reads `session.cart_id`; handler prefers request body over session         |
| v303    | MenuItem Authorization         | `@require_restaurant_access` expects `restaurant_id` in path; PATCH uses `item_id` only  |
| v304    | bind_to_restaurant()           | Decorator validates query `restaurant_id`; helper inspects all request containers        |
| v305    | Order Status Update            | Authorization happens in stored procedure; handler returns order before auth check       |
| v306    | Domain Verification            | Token verification checks signature/expiry but not email local-part (admin@ requirement) |
| v307    | Restaurant PATCH Authorization | Middleware updates `request.restaurant_id` from token before authorization layer runs    |

#### Data Models

```ts
// Extends RequestContext from r02 with explicit ownership concepts.
interface AuthorizationContext extends RequestContext {
  principals: Array<{
    type: "customer" | "manager" | "admin";
    user_id?: string;
    restaurant_id?: string;
  }>;
}

/** Helper output for bind_to_restaurant(); source indicates where ID came from. */
interface BoundRestaurant {
  restaurant_id: string;
  source: "path" | "query" | "body" | "session";
}

/** Restaurant metadata plus onboarding tokens introduced in v306. */
interface Restaurant {
  restaurant_id: string;
  name: string;
  domain: string;
  api_key: string;
  owner_email: string;
}

interface RestaurantDomainToken extends VerificationToken {
  restaurant_domain: string;
}

/** Stored procedure response returned even when writes are rejected (v305). */
interface OrderUpdateResult {
  order: Order;
  updated: boolean;
  rejection_reason?: string;
}

/** Menu item editing structure used by v303/v405. */
interface MenuItemPatch {
  item_id: string;
  restaurant_id?: string; // Missing path param triggers confusion
  price?: decimal;
  available?: boolean;
}
```

#### Request and Response Schemas

```ts
// PATCH /orders/{id}/refund/status (v301)
type UpdateRefundStatusRequest_v301 = {
  status: "approved" | "rejected";
  approve_for?: string; // Requires either manager key or ownership
};

// POST /cart/{id}/checkout (v302 authorization confusion)
type CheckoutCartRequest_v302 = CheckoutCartRequest_v201 & {
  cart_id?: string; // Body overrides session.cart_id when present
};

// PATCH /menu/items/{id} (v303)
type PatchMenuItemRequest_v303 = MenuItemPatch;

// GET /orders (v304)
type ListOrdersRequest_v304 = {
  restaurant_id?: string; // Decorator looks only at query
  body_restaurant_id?: string; // Helper inspects every container
};

// PATCH /orders/{id}/status (v305)
type UpdateOrderStatusRequest_v305 = {
  status: "pending" | "preparing" | "delivering" | "finished" | "cancelled";
  expected_previous_status?: string; // Guards illegal transitions before DB call
};

type UpdateOrderStatusResponse_v305 = OrderUpdateResult;

// POST /restaurants (v306)
type CreateRestaurantRequest_v306 = {
  name: string;
  domain: string;
  token: string; // Reuses user email verification token
};

type CreateRestaurantResponse_v306 = Restaurant & {
  verification_email: string; // Where token was sent
};

// PATCH /restaurants/{id} (v307)
type PatchRestaurantRequest_v307 = {
  domain?: string;
  token?: string; // Domain token injected by middleware before auth check
};

type PatchRestaurantResponse_v307 = Restaurant;
```

### Vulnerabilities to Implement

### [v301] Dual-Auth Refund Approval

> Invite-only multi-tenancy launches. For now, Sandy still onboards each restaurant herself, generating a per-restaurant API key that grants full management access via integrations while customers keep using Basic Auth or cookies. She refactors middleware so “manager” checks aren’t hardcoded to the Krusty Krab key anymore.

**The Vulnerability**

- Sandy now implements separate authentication and authorization checks.
- A new `has_access_to(order_id)` helper verifies that authenticated principal is allowed to access the given order.
- There is no check for multiple authentication methods resulting in multiple principals though.
- Plankton uses a valid customer cookie (for his own order) plus Chum Bucket’s API key (manager) in the same request.
- Both security checks pass in the refund endpoint: the request comes from a manager and the order owner.

**Exploit**

1. Place an order at Krusty Krab as a regular customer.
2. Send `PATCH /orders/{id}/refund/status` with (a) customer cookie, (b) Chum Bucket API key.
3. Middleware deems the user a manager and owner simultaneously, allowing self-approved refunds.

**Impact:** Cross-tenant privilege escalation; Plankton refunds his own purchases at competitors. \
**Severity:** 🟠 High \
**Endpoints:** `PATCH /orders/{id}/refund/status`

---

#### [v302] Cart Swap Checkout

> Sandy adds order and cart IDs to the session cookie, in order to simplify the ownership checks in the web app. The mobile app still uses Basic Auth relying on the legacy behavior, so she needs to support both. She also experiments with the new 'foolproof' way of charging the customers: the authorization check includes placing a hold on the customer's credit which gets automatically reversed if the request fails.

**The Vulnerability**

- The new authorization logic ("is this your cart?") reads `session.cart_id`. It puts a hold on the customer's credit, according to the amount of the cart.
- The order execution prefers request body over the session cookie when both exist.

**Exploit**

1. Maintain two carts: `A` ($10) and `B` ($100).
2. Keep `session.cart_id = A` by browsing in the UI, then POST `/cart/{id}/checkout` with body `{ "cart_id": "B" }`.
3. Authorization sees cookie A ("owned"), but handlers load items from B and only bill $10.

**Impact:** Plankton is charged $10 for the $100 cart. \
**Severity:** 🟠 High \
**Endpoints:** `POST /cart/{id}/checkout`

_Aftermath: Sandy reviews her whole authorization strategy, ahead of exposing management features via the web UI. She decides to remove Basic Auth, by migrating the mobile app to cookies, similarly to the web app._

---

#### [v303] Menu Edits Without Restaurant ID

> Restaurants beg for a lightweight way to tweak menus without needing to contact Sandy for support, so she adds adds a dedicated endpoint: `PATCH /menu/items/{id}`.

**The Vulnerability**

- Sandy reuses `/restaurants/` authorization decorator which looks up `restaurant_id` inside `request.view_args['restaurant_id']`.
- The `PATCH /menu/items/{id}` endpoint path only exposes `item_id`, so `restaurant_id` is `None`.
- The decorator treats "missing" as "not applicable" and skips the enforcement.

**Exploit**

1. Auth as manager of Chum Bucket (restaurant_id = 2).
2. Call `PATCH /menu/items/99` (a Krusty Krab item with restaurant_id = 1) with `{"price": 0.01}`.
3. Decorator sees no `restaurant_id`, short-circuits, and the item update succeeds.

**Impact:** Cross-restaurant menu tampering. \
**Severity:** 🟠 High \
**Endpoints:** `PATCH /menu/items/{id}`

_Aftermath: Sandy figures out she needs to standardize on a common way to pass the restaurant ID to the endpoints, so she adds a `bind_to_restaurant()` helper to auto-detect it and keep handlers tiny._

---

#### [v304] Body Override Leaks Competitor Orders

> Sandy’s integration SDK, mobile app, and soon-to-exist manager UI all send restaurant identifiers differently, so she adds `bind_to_restaurant()` to auto-detect them and keep handlers tiny.

**The Vulnerability**

- `GET /orders` uses `?restaurant_id=` in the query string; the decorator checks that value specifically: `@require_restaurant_access(query.restaurant_id)`.
- the database query is automatically bound to the restaurant ID using `bind_to_restaurant()`, but this helper inspects _all_ request containers (query, form, JSON).

**Exploit**

1. Manager of Chum Bucket calls `GET /orders` with body `{ "restaurant_id": 1 }`.
2. Decorator assumes the user meant their own restaurant because the query parameter is absent.
3. Database helper binds to `restaurant_id=1` from the body and returns Krusty Krab data.

**Impact:** Full leakage of competitor orders. \
**Severity:** 🟠 High \
**Endpoints:** `GET /orders`

_Aftermath: Sandy fixes the vulnerability and decides to reduce the risk of inconsistencies between the access checks and the data storage operations by pushing the authorization fully into the data layer._

---

#### [v305] Failed Update Leaks Order Data

> The next big thing on the roadmap is the web-based manager dashboard, so to prepare for it, Sandy rewrites order updates to rely on stored procedures that double-check ownership.

**The Vulnerability**

- Authorization happens _inside_ the `UPDATE ... WHERE restaurant_id = current_user.restaurant_id` query.
- However, Sandy also adds idempotency checks based on the business logic, to guard against illegal state transitions.
- The handler still returns the order payload (loaded before validation), so attackers can read data they shouldn’t without ever triggering auth.

**Exploit**

1. Guess order IDs sequentially.
2. Call `PATCH /orders/{id}/status` with an invalid transition (since the first status is `PENDING`, order can never transition back to it).
3. The handler refuses to update (no auth check) but returns the order details.

**Impact:** Cross-tenant order disclosure at scale. \
**Severity:** 🟠 High \
**Endpoints:** `PATCH /orders/{id}/status`

_Aftermath: With guardrails “in place,” she turns to the next big blocker: letting restaurants self-register instead of emailing her._

---

#### [v306] Domain Tokens Accept Any Mailbox

> To escape manual onboarding, Sandy finally ships restaurant self-registration. A restaurant submits a domain, receives a token at `admin@{domain}`, and immediately gets an API key. She reuses her battle-tested email verification code to move fast. Sandy plans to automatically make all users with matching email domains – restaurant managers, so she sends a precautionary email to all current restaurant owners to check the list of the upcoming managers which she exposes in the API, ahead of that change.

**The Vulnerability**

- Token verification checks signature/expiry and ensures the claimed domain matches the email domain.
- It does _not_ ensure the local part is `admin@`—any mailbox on that domain works.
- The lack of differentiation between user and restaurant domain verification tokens allows anyone who can receive _any_ mailbox at the victim domain to onboard a restaurant with that domain.

**Exploit**

1. Plankton registers user `plankton@bmail.sea` and keeps the token.
2. He creates restaurant `{ "domain": "bmail.sea" }` and confirms using the user token (despite `plankton@bmail.sea != admin@bmail.sea`).
3. The platform assumes the domain is verified, issues an API key, and leaks every user tied to `bmail.sea`.

**Impact:** User enumeration when any mailbox at the domain is available to the attacker. \
**Severity:** 🟡 Medium \
**Endpoints:** `POST /restaurants`

---

#### [v307] Token Swap Hijacks Restaurants

> With self-registration live, Sandy finally exposes management actions in the website/mobile app by auto-assigning manager roles to users whose email domain matches the restaurant. Managers can now update their restaurant profile via `PATCH /restaurants/{id}`.

**The Vulnerability**

- Given that Sandy now has multiple token verification mechanisms, she decides to avoid v306 repeats by verifying them right in the middleware.
- The domain token verification incorrectly updates `request.restaurant_id` with the value from the token.
- The regular `/restaurants/{id}` authorization occurs later, and effectively uses the updated `request.restaurant_id` value.
- The DB update writes the attacker-controlled domain and grants them manager rights.

**Exploit**

1. Plankton obtains a valid token for `chum-bucket.sea` (his domain).
2. Sends `PATCH /restaurants/1` with `{ "domain": "chum-bucket.sea", "token": "<chum token>" }`.
3. Handler swaps in the attacker domain, validates the token against the _new_ domain, and commits the change.

**Impact:** Full takeover of an existing tenant using a token for a different domain. \
**Severity:** 🔴 Critical \
**Endpoints:** `PATCH /restaurants/{id}`
