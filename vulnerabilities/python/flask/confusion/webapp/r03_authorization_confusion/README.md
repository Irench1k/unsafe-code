## r03: Authorization Confusion (Work in Progress)

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

### Vulnerabilities to Implement (Work in Progress)

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
