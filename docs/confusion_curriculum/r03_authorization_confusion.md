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
| v303+     | PATCH  | /menu/{id}                 | Restaurant          | Update menu item              | v303, v405       |
| v306+     | POST   | /restaurants               | Public              | Register restaurant + API key | v306             |
| v307+     | PATCH  | /restaurants/{id}          | Manager             | Update restaurant profile     | v307             |

#### Schema Evolution

##### Data Model Evolution

| Model               | v301 | v302               | v303 | v304 | v305 | v306                       | v307                     |
| ------------------- | ---- | ------------------ | ---- | ---- | ---- | -------------------------- | ------------------------ |
| OrderAccessHelper   | ✅ `has_access_to_order()` trusts whichever identity is available (customer session bleeds into manager checks) | - | - | - | - | -                          | -                        |
| CartAuthorization   | -    | Session keeps `cart_id`; `resolve_trusted_cart()` trusts it before `g.cart_id` | -    | -    | -    | -                          | -                        |
| MenuItem            | ✅ SQLAlchemy table keyed by `id` with `restaurant_id`, `name`, `price`, `available` | - | - | - | - | -                          | -                        |
| Order               | ✅ Orders persist `restaurant_id`, `user_id`, totals, delivery fees, tips, and `status` enum | - | - | - | - | -                          | -                        |
| OrderItem           | ✅ Snapshot line items capture menu `item_id`, `name`, and `price` per order | - | - | - | - | -                          | -                        |
| Cart                | ✅ Carts store `restaurant_id`, `user_id`, and `active` flag for cross-request ownership | - | - | - | - | -                          | -                        |
| CartItem            | ✅ Join table keeps persisted `cart_id` → `item_id` mappings | - | - | - | - | -                          | -                        |
| Refund              | ✅ Refund records track `order_id`, amount, `status`, `auto_approved`, `paid`, timestamps | - | - | - | - | -                          | -                        |
| User                | ✅ Users now have numeric IDs plus `email`, `name`, hashed `password`, Decimal `balance` | - | - | - | - | -                          | -                        |
| Restaurant          | ✅ Restaurants include description, owner email, and per-tenant API key | - | - | - | - | ✅ (domain onboarding)     | `+domain PATCH mutation` |
| PlatformConfig      | ✅ Key/value store backs platform API key + signup bonus counters | - | - | - | - | -                          | -                        |
| DomainToken         | -    | -                  | -    | -    | -    | ✅ (user token reuse path) | -                        |

##### Behavioral Changes

| Version | Component                      | Behavioral Change                                                                        |
| ------- | ------------------------------ | ---------------------------------------------------------------------------------------- |
| v301    | OrderAccessHelper              | `has_access_to_order()` pulls session customers even during manager API-key calls        |
| v302    | CartAuthorization              | `charge_customer_with_hold()` charges `session.cart_id`; handler re-runs `resolve_trusted_cart()` using the path ID |
| v303    | MenuItem Authorization         | `@restaurant_owns(MenuItem, "item_id")` relies on `restaurant_id` view args; `/menu/{id}` never passes one so only existence is checked |
| v304    | bind_to_restaurant()           | Decorator validates query `restaurant_id`; helper inspects all request containers        |
| v305    | Order Status Update            | Authorization happens in stored procedure; handler returns order before auth check       |
| v306    | Domain Verification            | Token verification checks signature/expiry but not email local-part (admin@ requirement) |
| v307    | Restaurant PATCH Authorization | Middleware updates `request.restaurant_id` from token before authorization layer runs    |

#### Data Models

```ts
type OrderStatus = "created" | "delivered" | "refunded" | "cancelled";
type RefundStatus = "pending" | "auto_approved" | "approved" | "rejected";

interface Restaurant {
  restaurant_id: number;
  name: string;
  description: string;
  owner_email: string;
  api_key: string;
}

interface User {
  user_id: number;
  email: string;
  name: string;
  balance: decimal;
  password: string;
}

interface MenuItem {
  item_id: number;
  restaurant_id: number;
  name: string;
  price: decimal;
  available: boolean;
}

interface Cart {
  cart_id: number;
  restaurant_id: number;
  user_id: number;
  active: boolean;
  items: number[];
}

interface CartItem {
  cart_item_id: number;
  cart_id: number;
  item_id: number;
}

interface OrderItem {
  item_id: number;
  name: string;
  price: decimal;
}

interface Order {
  order_id: number;
  restaurant_id: number;
  user_id: number;
  total: decimal;
  delivery_fee: decimal;
  tip: decimal;
  delivery_address: string;
  created_at: string;
  status: OrderStatus;
  items: OrderItem[];
}

interface Refund {
  refund_id: number;
  order_id: number;
  amount: decimal;
  reason: string;
  status: RefundStatus;
  auto_approved: boolean;
  paid: boolean;
  created_at: string;
}

interface PlatformConfig {
  config_id: number;
  key: string;
  value: string;
}

/** Helper output for bind_to_restaurant(); source indicates where ID came from. */
interface BoundRestaurant {
  restaurant_id: string;
  source: "path" | "query" | "body" | "session";
}

/** Restaurant metadata plus onboarding tokens introduced in v306. */
interface RestaurantDomainToken extends VerificationToken {
  restaurant_domain: string;
}

/** Stored procedure response returned even when writes are rejected (v305). */
interface OrderUpdateResult {
  order: Order;
  updated: boolean;
  rejection_reason?: string;
}

/** Menu item editing payload used by /menu/{id}; route omits restaurant_id so enforcement fails. */
interface MenuItemPatch {
  name?: string;
  price?: decimal;
  available?: boolean;
}
```

#### Request and Response Schemas

```ts
// PATCH /orders/{id}/refund/status (v301)
type UpdateRefundStatusRequest_v301 = {
  status: "approved" | "rejected";
};

// POST /cart/{id}/checkout (v302 authorization confusion)
type CheckoutCartRequest_v302 = CheckoutCartRequest_v201;
// Confusion stems from which cart ID the framework reads (session vs. path), not from new fields.

// PATCH /menu/{id} (v303)
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

> The in-memory dict can't scale anymore. Sandy migrates to Postgres with SQLAlchemy, refactoring the entire data layer to use ORM models. While she's at it, she introduces multi-tenancy—each restaurant now gets its own API key.

**The Vulnerability**

- Sandy extracted a `has_access_to_order(order_id)` helper that returns `True` if _either_ the current customer owns the order or the current restaurant owns the order.
- Manager-only endpoints now rely on that helper even though they should only consider the restaurant branch.
- Plankton keeps his customer session cookie (from placing the order) and sends a Chum Bucket manager API key when patching refunds.
- The API-key authenticator marks the request as "manager" while `has_access_to_order()` immediately approves the request because the still-present customer session owns the order.

**Exploit**

1. Place an order at Krusty Krab as a regular customer (keep the cookie or stay logged in).
2. Send `PATCH /orders/{id}/refund/status` with your Chum Bucket `X-API-Key`; no extra auth header is required because the cookie still rides along.
3. The manager endpoint sees the API key and trusts the helper, which immediately approves the request because your user session owns the order.

**Impact:** Cross-tenant privilege escalation; Plankton refunds his own purchases at competitors. \
**Severity:** 🟠 High \
**Endpoints:** `PATCH /orders/{id}/refund/status`

---

#### [v302] Cart Swap Checkout

> Sandy adds order and cart IDs to the session cookie, in order to simplify the ownership checks in the web app. The mobile app still uses Basic Auth relying on the legacy behavior, so she needs to support both. She also experiments with the new 'foolproof' way of charging the customers: the authorization check includes placing a hold on the customer's credit which gets automatically reversed if the request fails.

**The Vulnerability**

- The new `charge_customer_with_hold` decorator resolves carts by reading `session.cart_id` first, charging/authorizing that cart total, and then clearing the session entry.
- The checkout handler runs afterwards and calls `resolve_trusted_cart()` again; with the session entry gone, it falls back to the cart ID in the URL path (`/<cart_id>/checkout`).
- A request can therefore pay for the cheap cart currently stored in the session while the handler fulfills the expensive cart referenced in the path.

**Exploit**

1. Maintain two carts: keep a $7 “official” cart in the UI so `session.cart_id` points to it, and separately build a $70 cart by calling the API with different IDs.
2. Without checking out the cheap cart, send `POST /cart/{expensive_cart_id}/checkout` from the browser session.
3. The hold decorator charges the $7 session cart, but the handler immediately re-resolves the path cart and ships the $70 items.

**Impact:** Plankton is charged $10 for the $100 cart. \
**Severity:** 🟠 High \
**Endpoints:** `POST /cart/{id}/checkout`

---

#### [v303] Menu Edits Without Restaurant ID

> Restaurants want self-service menu updates. Sandy adds a convenience endpoint `PATCH /menu/{item_id}` and extracts a reusable `@restaurant_owns()` decorator from her existing routes.

**The Vulnerability**

- The decorator expects `restaurant_id` in `request.view_args` to validate ownership.
- The new `/menu/{item_id}` route never sets `restaurant_id`, so the decorator just verifies the item exists and exits without comparing ownership.
- Handlers therefore trust whichever API key showed up, even when the item belongs to another restaurant.

**Exploit**

1. Auth as manager of Chum Bucket (restaurant_id = 2).
2. Call `PATCH /menu/1` (a Krusty Krab item) with `{ "available": false }`.
3. The decorator has no restaurant ID to compare, so the request succeeds and disables the competitor’s menu item.

**Impact:** Cross-restaurant menu tampering. \
**Severity:** 🟠 High \
**Endpoints:** `PATCH /menu/{id}`

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
