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

Squidward gets jealous of SpongeBob getting employee-of-the-month. Plankton intensifies gets signs up Chum Bucket as the next Cheeky Saas customer and intensifies his attacks, probing for ways to sabotage the Krusty Krab from within the platform.

This introduces proper authorization: ownership checks, roles (customer, manager, admin), and resource scoping. Authentication methods from r02 (cookies, API keys) remain, but now handlers must verify not just _who_ you are, but _what_ you can access.

### Authorization Roles

By the end of r03, these roles are enforced:

| Role     | Description                                      | Auth Methods    |
| -------- | ------------------------------------------------ | --------------- |
| Public   | No authentication required                       | None            |
| Customer | Regular users placing orders                     | Cookie          |
| Manager  | Restaurant staff (auto-assigned by email domain) | Cookie/API Key  |
| Admin    | Platform admins                                  | X-Admin-API-Key |

### Endpoints:

| Lifecycle | Method | Path                                    | Auth             | Purpose              | Vulnerabilities |
| --------- | ------ | --------------------------------------- | ---------------- | -------------------- | --------------- |
| v299+     | GET    | /account/credits                        | Customer         | View balance         |                 |
| v299+     | POST   | /account/credits                        | Admin            | Top-up credits       |                 |
| v299+     | POST   | /auth/login                             | Public           | Create session       |                 |
| v299+     | POST   | /auth/logout                            | Customer         | Destroy session      |                 |
| v299+     | POST   | /auth/register                          | Public           | Register user        |                 |
| v299+     | POST   | /cart                                   | Customer         | Create cart          |                 |
| v299+     | GET    | /cart/{id}                              | Customer/Manager | Get single cart      |                 |
| v299+     | POST   | /cart/{id}/checkout                     | Customer         | Checkout cart        | v302            |
| v299+     | POST   | /cart/{id}/items                        | Customer         | Add item to cart     |                 |
| v299+     | GET    | /menu                                   | Public           | List menu items      |                 |
| v299+     | GET    | /orders                                 | Customer/Manager | List orders          | v304            |
| v299+     | GET    | /orders/{id}                            | Customer/Manager | Get single order     |                 |
| v299+     | POST   | /orders/{id}/refund                     | Customer         | Request refund       |                 |
| v299+     | PATCH  | /orders/{id}/refund/status              | Manager          | Update refund status | v301            |
| v299+     | PATCH  | /orders/{id}/status                     | Manager          | Update order status  | v305            |
| v301+     | GET    | /restaurants                            | Public           | List restaurants     | v306            |
| v301+     | GET    | /restaurants/{id}                       | Public           | Get restaurant info  |                 |
| v303+     | PATCH  | /menu/items/{id}                        | Manager          | Update menu item     | v303            |
| v306+     | POST   | /restaurants                            | Public           | Create restaurant    | v306            |
| v306+     | GET    | /restaurants/{id}/api-keys              | Manager          | List API keys        |                 |
| v306+     | POST   | /restaurants/{id}/api-keys              | Manager          | Create API key       |                 |
| v306+     | DELETE | /restaurants/{id}/api-keys/{api_key_id} | Manager          | Delete API key       |                 |
| v307+     | PATCH  | /restaurants/{id}                       | Manager          | Update info          | v307            |

> [!IMPORTANT]
> Multi-tenancy means most endpoints now need `restaurant_id` filtering. Customer endpoints (orders, carts) should allow accessing any restaurant's items for ordering (then limit mutations to the items ordered by this customer), but Manager endpoints should be restricted to their own restaurant only.

> [!TIP]
> Restaurant self-registration requires domain verification. Send verification emails to `admin@{domain}` with a signed token, similar to the user registration flow from r01. This token verification creates an opportunity for authorization bypass vulnerabilities.

#### Schema Evolution

Track how schemas change across versions:

| Model            | v299 | v301             | v302       | v303 | v304 | v305 | v306        | v307 |
| ---------------- | ---- | ---------------- | ---------- | ---- | ---- | ---- | ----------- | ---- |
| Restaurant       | -    | ✅               | -          | -    | -    | -    | `+verified` | -    |
| RestaurantApiKey | -    | -                | -          | -    | -    | -    | ✅          | -    |
| MenuItem         | Base | `+restaurant_id` | -          | -    | -    | -    | -           | -    |
| Cart             | Base | `+restaurant_id` | -          | -    | -    | -    | -           | -    |
| Order            | Base | `+restaurant_id` | -          | -    | -    | -    | -           | -    |
| Session          | Base | -                | `+cart_id` | -    | -    | -    | -           | -    |
| UpdateMenuItem   | -    | -                | -          | ✅   | -    | -    | -           | -    |
| CreateRestaurant | -    | -                | -          | -    | -    | -    | ✅          | -    |
| UpdateRestaurant | -    | -                | -          | -    | -    | -    | -           | ✅   |

#### Data Models

```ts
/**
 * Represents a restaurant tenant on the platform.
 * Introduced in v301 to support multi-tenancy.
 */
interface Restaurant {
  restaurant_id: string;
  name: string;
  domain: string; // Email domain for manager authorization (e.g., "krusty-krab.sea")
  created_at: timestamp;

  // Added in v306 (self-registration)
  verified?: boolean; // Domain ownership verified via email token
}

/**
 * Represents an API key for restaurant integrations.
 * Introduced in v306 for third-party integrations.
 */
interface RestaurantApiKey {
  api_key_id: string;
  restaurant_id: string;
  api_key_secret: string; // The actual key value (hashed in DB)
  created_at: timestamp;
}

/**
 * MenuItem from r01, now scoped to restaurants.
 * Updated in v301 to support multi-tenancy.
 */
interface MenuItem {
  id: string;
  name: string;
  price: decimal;
  available: boolean;

  // Added in v301
  restaurant_id: string;
}

/**
 * Cart from r01, now scoped to restaurants.
 * Updated in v301 to support multi-tenancy.
 */
interface Cart {
  cart_id: string;
  items: string[]; // Array of item IDs

  // Added in v301
  restaurant_id: string;
}

/**
 * Order from r01, now scoped to restaurants.
 * Updated in v301 to support multi-tenancy.
 */
interface Order {
  order_id: string;
  total: decimal;
  delivery_address: string;
  created_at: timestamp;
  items: OrderItem[];
  delivery_fee?: decimal;
  cart_id?: string;
  tip?: decimal;

  // Added in v301
  restaurant_id: string;
}

/**
 * Session from r02, now tracks cart persistence.
 * Updated in v302 to support returning customers.
 */
interface Session {
  session_id: string;
  user_id: string;
  email: string;
  created_at: timestamp;
  expires_at: timestamp;

  // Added in v302 (cart persistence)
  cart_id?: string; // Allows customers to resume shopping
}

/**
 * Request context from r02, now extended with restaurant info.
 * This is NOT a database model - it's request-scoped state.
 */
interface RequestContext {
  user_id?: string;
  user_type?: string; // "customer" | "manager" | "admin"
  email?: string;
  restaurant_id?: string; // For manager users, which restaurant they manage
}
```

#### Request and Response Schemas

```ts
// GET /restaurants
type ListRestaurantsResponse = Restaurant[];

// GET /restaurants/{id}
type GetRestaurantResponse = Restaurant;

// POST /restaurants (v306)
type CreateRestaurantRequest = {
  name: string;
  domain: string;
  token?: string; // Provided in second step for domain verification
};

type CreateRestaurantResponse = {
  restaurant_id: string;
  name: string;
  domain: string;
  verified: boolean;
  api_key?: string; // Returned only when verified=true
};

// PATCH /restaurants/{id} (v307)
type UpdateRestaurantRequest = {
  name?: string;
  domain?: string;
  token?: string; // Required for domain changes
};

type UpdateRestaurantResponse = Restaurant;

// PATCH /menu/items/{id} (v303)
type UpdateMenuItemRequest = {
  name?: string;
  price?: decimal;
  available?: boolean;
};

type UpdateMenuItemResponse = MenuItem;

// GET /orders (v304)
// Query parameters: ?restaurant_id=...
type ListOrdersResponse = Order[];

// PATCH /orders/{id}/status (v305)
type UpdateOrderStatusRequest = {
  status: "pending" | "preparing" | "delivering" | "completed" | "cancelled";
};

type UpdateOrderStatusResponse = Order;

// POST /cart/{id}/checkout (v302)
// Reads cart_id from: session cookie OR path parameter
type CheckoutCartRequest = {
  delivery_address: string;
  tip?: decimal;
  cart_id?: string; // Optional: overrides session.cart_id if provided
};

type CheckoutCartResponse = Order;

// GET /restaurants/{id}/api-keys (v306)
type ListApiKeysResponse = {
  api_key_id: string;
  created_at: timestamp;
  description?: string; // Never return api_key_secret
}[];

// POST /restaurants/{id}/api-keys (v306)
type CreateApiKeyRequest = {
  description?: string;
};

type CreateApiKeyResponse = {
  api_key_id: string;
  api_key_secret: string; // Only returned once at creation
  created_at: timestamp;
};

// DELETE /restaurants/{id}/api-keys/{api_key_id} (v306)
type DeleteApiKeyResponse = {}; // Empty response
```

### Vulnerabilities to Implement

### [v301] Sticky Role From API Key (Context Bleed)

**Scenario:**

Sandy has rolled out initial multi-tenancy support, and onboarded her second customer, Chum Bucket. There is no restaurant self-registration yet and management functionality remains API key only. She prepares platform for adding this functionality to the web UI, by iterating on authentication middleware.

Previously, the management functionality was gated by a straightforward API key verification, because that was the only authentication method available. Furthermore, there was only one restaurant in the system. Sandy rewrites middleware to remove these obsolete assumption and now management functionality is gated by two checks:

1. Middleware checks that the user is manager (at this stage this is still only possible via API key, but this decoupling simplifies future introduction of Cookie-based management authentication) and sets `request.manager = true`
2. Handler uses `has_access_to(order_id)` helper to check if the user has access to the order

**The Bug:**

The new helper `has_access_to(order_id)` checks _indirect ownership_: user -> is manager at the restaurant -> the order was placed at this restaurant -> user has access to the order, but the simpler _direct ownership_ works as well: user -> has placed the order -> user has access to the order.

Another weakness is that middleware checks all available authentication methods (not just the first successful one), and no thought has been put into considering what happens when multiple authentication methods are present.

**Impact:** Plankton requests refund for his own order at Krusty Krab, using a regular customer cookie. He then approves the refund himself, by sending `PATCH /orders/{id}/refund/status` request by adding BOTH Chum Bucket API key (that satisfies `request.manager` check) and regular customer cookie (that satisfies `has_access_to(order_id)` check).

**Severity:** 🔴 Critical
**Endpoints:** `PATCH /orders/{id}/refund/status`

---

#### [v302] Cart Confusion: Cookie vs Body

**Scenario:** Sandy refactors the checkout flow to improve UX. The new flow stores `cart_id` in a session cookie to let returning customers _continue shopping_ from where they left off. She needs to maintain the backwards compatibility with the old behavior, because some mobile app customers still haven't received the update.

**The Bug:**

- New checkout flow stores `cart_id` in a session cookie
- The checkout handler processes both types of requests correctly: with and without the `session.cart_id` cookie
- However, if the request contains both a cookie and a body, the price calculation is performed on the `session.cart_id` while the order items are associated with the `body.cart_id`

**Impact:** Plankton creates two carts: cart A (worth $10), and cart B (worth $100). He sends checkout request with cookie pointing to cart A and body containing `{"cart_id": "<B>"}`. Only $10 is charged, but the order contains 100$ worth of items from cart B. \
**Severity:** 🔴 Critical

**Endpoints:** `POST /cart/{id}/checkout`

---

#### [v303] Menu Item IDOR: Missing Resource Type

**Scenario:** Sandy implements resource-based authorization for restaurant management. She creates a reusable decorator: `@require_restaurant_access(restaurant_id=...)` that checks if the current user is a manager of the specified restaurant.

**The Bug:**

- Decorator expects `restaurant_id` parameter from path: `@require_restaurant_access(restaurant_id=request.view_args['restaurant_id'])`
- But `PATCH /menu/items/{id}` only has `item_id` in the path, not `restaurant_id`
- Decorator fails to find `restaurant_id`, gets `None`, and the None-check silently passes (fail-open)

**Attack Scenario:** Plankton (manager of Chum Bucket, restaurant_id=2) sends `PATCH /menu/items/99` (Krabby Patty from restaurant_id=1) with body `{"price": 0.01}`. Authorization looks for `restaurant_id` in path, doesn't find it, defaults to "allow." Plankton sabotages the Krusty Krab's menu.

**Impact:** Plankton can change the price or availability of any menu item at Krusty Krab: Cross-restaurant IDOR \
**Severity:** 🔴 Critical

**Endpoints:** `PATCH /menu/items/{id}`

---

#### [v304] Authorization Bypass via Unvalidated Request Parameter

**Scenario:** Sandy keeps iterating on the `restaurant_id` authorization, trying to make it as convenient as possible. Her latest experiments include:

1. the `bind_to_restaurant()` database query helper, that automatically binds the current user to the restaurant
2. `has_access_to(restaurant_id)` authorization helper to check if the user has access to the restaurant

**The Bug:**

- `GET /orders?restaurant_id=<ID>` endpoint is protected by `@require_restaurant_access(query.restaurant_id)` decorator
- The storage access uses `bind_to_restaurant()` helper to only fetch orders for the authorized restaurant
- The `bind_to_restaurant()` is meant to be universal, so it actually examines all possible sources, including form and json – not just query string

**Impact:** Plankton leaks all Krusty Krab orders by adding `restaurant_id=1` to request body – instead of query string. \
**Severity:** 🔴 Critical

**Endpoints:** `GET /orders`

---

#### [v305] Authorization Bypass via "No-Op" Data Leak

**Scenario:** Sandy experiments with _'better ask for forgiveness than permission'_ approach to authorization. She embeds the authorization check inside the database update call, which is raising exception on failure.

**The Bug:**

- The authorization check only occurs if there is a database update operation
- Handler only performs database update after checking state machine constraints (e.g. `PENDING` -> `COMPLETED` -> `REFUNDED`)
- If the constraints are not met, the handler skips the update – trying to be _"idempotent"_
- As a result, if the status is set to `PENDING` the database update is always skipped, along with the authorization check. The handler still returns the order object, leaking the order details.

**Impact:** Plankton can iterate order IDs and leak all order details across all restaurants in the system. \
**Severity:** 🟡 High

**Endpoints:** `PATCH /orders/{id}/status`

---

#### [v306] Domain Verification Token Confusion

**Scenario:** Sandy finally rolls out restaurant self-registration. In order to avoid spam and impersonation of legitimate businesses, she implements basic domain verification. When creating a restaurant, the user must prove ownership of the domain, by confirming the verification token sent to `admin@{domain}` email address.

Unrelatedly, Sandy plans to introduce management functionality via web UI, not just API keys. She updates the `GET /restaurants` endpoint ahead of that work, to return the list of all users that are registered in the system with the email domain matching the restaurant's domain. She informs restaurant owners to check if they have any users registered already, as they will be automatically assigned manager role once the new functionality is rolled out.

**The Bug:**

- Authorization checks that previously consumed restaurant ID have been updated to also accept restaurant domain
- Token validation checks: signature, expiration and – of course – that claimed domain matches the token's email address
- But there's no validation that `token.email == "admin@{domain}`, even though that's the address the token was sent to
- Internally, the token verification system is shared with user registration handler
- The system does not make a distinction between the two use cases

**Impact:**

1. User enumeration (🟡 High). Plankton registers a new user with the free Bmail address `plankton@bmail.sea` (a free email provider popular in Bikini Bottom). He also registers the restaurant with the domain `bmail.sea`. Although the verification token is sent to `admin@bmail.sea`, Plankton is able to finish registration by providing the token he received during the registration of `plankton@bmail.sea` account. As a result, Plankton is able to enumerate all users registered in the system with this popular free email provider.
2. Tenant takeover (🔴 Critical). Plankton bribes Squidward, and gets access to the `test@krusty-krab.sea` email address. This mailbox is unused and does not seem like a big risk. However, Plankton can now create a new restaurant with the domain `krusty-krab.sea` (the domain used by the real Krusty Krab restaurant). The restaurant creation request returns API key, which Plankton can now use to access legitimate Krusty Krab restaurant's resources.

**Severity:** 🔴 Critical
**Endpoints:** `POST /restaurants`

---

#### [v307] "Time-of-Check, Time-of-Use" (TOCTOU) in Authorization

**Scenario:** Sandy works hard to address the vulnerabilities used in v306, by hardening token verification, and removing poorly thought out domain based authorization checks. With these changes, she is confident in rolling out the management functionality in the web UI. This release automatically assigns manager role to users whose email domain matches the restaurant's domain (e.g., `spongebob@krusty-krab.sea` can manage restaurant with `domain='krusty-krab.sea'`) – the idea that was warmly received by restaurant owners as it significantly simplifies management overhead.

**The Bug:** The authorization check is executed during database update, but the handler accidentally updates restaurant object in memory, before that.

**Impact:** Plankton hijacks Krusty Krab by updating its domain to `chum-bucket.sea`. He starts by initiating new restaurant registration, then sends an update request to `PATCH /restaurants/1` (Krusty Krab's ID) with the body `{"token": "<verification token>", "domain": "chum-bucket.sea"}`.

**Severity:** 🔴 Critical

**Endpoints:** `PATCH /restaurants/{id}`
