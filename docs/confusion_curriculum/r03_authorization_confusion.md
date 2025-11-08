## r03: Authorization Confusion

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

- Authorization checks one resource
- Business logic acts on different resource
- Indirect references resolved differently
- Parent-child relationship assumptions

### The Story

The platform is maturing! Sandy adds multi-tenancy support: restaurants can customize menus, manage items, and update settings. Mr. Krabs wants control over his restaurant's data without Sandy's help.

Squidward gets jealous of SpongeBob getting employee-of-the-month. Plankton intensifies his attacks, probing for ways to sabotage the Krusty Krab.

### Endpoints:

| Method | Path                                    | Auth                   | Purpose                | Input                                    | Response                                                                 |
| ------ | --------------------------------------- | ---------------------- | ---------------------- | ---------------------------------------- | ------------------------------------------------------------------------ |
| GET    | /restaurants/{id}                       | Public                 | Get restaurant info    | `restaurant_id`                          | `{restaurant_id, name, address}`                                         |
| GET    | /menu                                   | Public                 | List menu items        | `restaurant_id`                          | `[{id, name, price}]`                                                    |
| POST   | /cart                                   | Customer               | Create cart            | `restaurant_id`, `items: [item_id]`      | `{cart_id, restaurant_id, ...}`                                          |
| GET    | /orders                                 | Customer/Manager/Admin | List orders            | `restaurant_id`                          | `[{order_id, restaurant_id, ...}]`                                       |
| PATCH  | /menu/items/{id}                        | Admin                  | Update menu item       | `name`, `price`                          | `{id, name, price}`                                                      |
| POST   | /restaurants                            | Public                 | Create restaurant      | `name`, `id`, `description?`, `domain?`  | `{restaurant_id, name, id, description, domain}`                         |
| GET    | /restaurants                            | Public/Admin           | List restaurants       | -                                        | `[{restaurant_id, name, id, description, domain, api_keys?, managers?}]` |
| PATCH  | /restaurants/{id}                       | Admin                  | Update restaurant info | `name?`, `id`, `description?`, `domain?` | `{restaurant_id, name, id, description, domain}`                         |
| POST   | /restaurants/{id}/api-keys              | Admin                  | Create API key         | `description?`                           | `{api_key_id, api_key_secret}`                                           |
| GET    | /restaurants/{id}/api-keys              | Admin                  | List API keys          | -                                        | `[{api_key_id, api_key_secret}]`                                         |
| DELETE | /restaurants/{id}/api-keys/{api_key_id} | Admin                  | Delete API key         | -                                        | `{api_key_id, api_key_secret}`                                           |

(the other endpoints need to be adjusted to process and return restaurant-scoped data where appropriate)

Notes:

- We introduce the restaurant self-registration here, which includes definition of the restaurant's domain. This requires email verification (similar to how we implemented email verification for user registration) - with the emails sent to `admin@DOMAIN`
- Platform users whose email domain matches restaurant's domain are automatically considered `managers` of that restaurant

Authorization roles used in this section:

- `Public` - no authentication
- `Customer` - Cookie-based sesion, authenticated as a customer
- `Manager` - authenticated as a manager of the restaurant (automatically assigned to platform users whose email domain matches restaurant's domain)
- `Admin` - authenticated as a platform administrator (only via `X-API-Key` header)
- `Platform` - Sandy Cheeks, authenticated as a platform administrator (only via `X-Admin-API-Key` header)

### Vulnerabilities to Implement

#### 1. Manager Bypass: API Key vs Session

**Endpoint(s):** `POST /v201/orders/{id}/refund/status`

**Setup:**
Sandy adds management functionality support to web UI. She also has API key authentication for partners to integrate with Cheeky Saas. Managers can approve refunds, regular users cannot.

**The Vulnerability:**
Authentication middleware checks the API key and sets `request.user_id` from the key's owner. Authorization decorator checks this flag and (separately) permission to access order ID.

**Attack Scenario:**

1. Plankton registers a regular user account and logs in (gets session with role="user")
2. He creates an order at Krusty Krab, using user account
3. Plankton generates an API key for his own restaurant account
4. He hits an endpoint with both user cookie and restaurant API key
5. Auth middleware adds `request.role = "manager"` to the session
6. Plankton sends a request to approve the refund with the cookie only
7. Authorization decorator checks `request.role = "manager"` and order ID access, both pass
8. Plankton approves his own refund, on behalf of Krusty Krab restaurant

**Root Cause:**
Two authentication mechanisms coexist without clearing/syncing derived context. Session data persists beyond API key usage.

**Impact:**
Privilege escalation - regular users can perform manager actions by mixing authentication methods.

**Severity:** 🔴 Critical

**Framework Translation Notes:**

- Look for middleware that populates `request.user`, `req.user`, `context.user`
- Session and API key auth often set different properties
- Framework may have multiple "current user" sources that don't clear each other

#### 2. Order Hijacking: Cookie vs Body

**Endpoint(s):** `POST /v301/orders/{id}/checkout`

**Setup:** Sandy implements refactoring to store the cart ID in a cookie so users don't have to pass it explicitly. This should lead to a simplified and unified checkout flow.

**The Vulnerability:** The handler reads `cart_id` from cookies to load the cart and verify ownership. It then reads `order_id` from the path to checkout. However, it also reads a second `cart_id` from the JSON body to associate line items, without re-checking ownership.

**Attack Scenario:**

1. Plankton has created two carts in two browser session:
   - `cart_id=100` in his cookies (items worth $15)
   - `cart_id=200` in his cookies (items worth $100)
2. Using cookies from the first cart, he sends: `POST /v301/orders/999/checkout` with body `{"cart_id": 200}`
3. Handler verifies ownership of cart 100
4. Handler associates items from cart 200 with the new order
5. Plankton gets items worth $100 while only paying $15

**Root Cause:** Ownership check performed on cookie value, business logic acts on body value, assuming they're the same.

**Impact:** Order theft - attacker can finalize and receive another user's cart items.

**Severity:** 🔴 Critical

#### 3. Menu Item IDOR: Check Restaurant, Modify Item

**Endpoint(s):** `PATCH /v202/menu/{item_id}`

**Setup:**
Sandy implements resource-based permissions. Managers can only modify their own restaurant's data. She adds an authorization decorator that takes a `restaurant_id` parameter.

**The Vulnerability:**
Authorization decorator: `@require_restaurant_access(restaurant_id=request.view_args['restaurant_id'])` expects `<restaurant_id>` in the path.
But this endpoint only has `item_id` in the path: `/menu/{item_id}`.
The decorator fails to find `restaurant_id`, defaults to `None`, and the None-check passes silently.

**Attack Scenario:**

1. Plankton is manager of restaurant ID 2
2. He sends: `PATCH /v202/menu/99` (Krusty Krab's burger) with body `{"price": 0.01}`
3. Authorization looks for `<restaurant_id>` in path, doesn't find it
4. Authorization defaults to "allow" (missing data interpreted as unrestricted)
5. Business logic updates item 99's price

**Root Cause:**
Authorization decorator parameterized for wrong resource type, missing data treated as pass condition (Fail Open).

**Impact:**
Cross-restaurant IDOR - managers can modify any restaurant's menu items.

**Severity:** 🔴 Critical

**Framework Translation Notes:**

- Decorator parameterization: some frameworks use dependency injection, others use closure variables
- Path parameter extraction naming conventions

#### 4. Authorization Bypass via Unvalidated Form Parameter

- **Method:** `GET /orders`
- **Scenario:** The `GET /orders` endpoint now requires a `restaurant_id` to show tenant-specific orders. An authorization check is added to validate the user has access to the `restaurant_id` provided in the **query string**.
- **The Bug:** The authorization check _only_ inspects the **query string** (e.g., `request.args['restaurant_id']`). The data access logic, however, was written to be "flexible" and tries to get `restaurant_id` from the query string _or_ a `x-www-form-urlencoded` **form body** (e.g., `request.form.get('restaurant_id')`).
- **Impact:** Plankton (manager of Chum Bucket, `id=2`) sends a request to `GET /orders?restaurant_id=2` (which passes the auth check). He also includes a `Content-Type: application/x-www-form-urlencoded` header and a body of `restaurant_id=1` (for Krusty Krab). The data logic reads the ID from the form body and leaks all of Mr. Krabs' orders.
- **Severity:** 🔴 Critical

#### 5. Authorization Bypass via "No-Op" Data Leak

- **Method:** `PATCH /orders/{id}/status`
- **Scenario:** This endpoint updates an order's status. To be "efficient," Sandy placed the authorization check (is this _your_ restaurant's order?) inside the `if new_status:` block, right before the database `UPDATE` call.
- **The Bug:** The handler first fetches the order by its ID (from the path). Then it checks if a new `status` was provided. If no `status` is in the body, the update logic is skipped... and so is the authorization check. The handler then serializes and returns the order object it fetched.
- **Impact:** Plankton iterates order IDs (`PATCH /orders/123/status`, `PATCH /orders/124/status`...) with an empty body. The auth check is skipped, and the handler helpfully returns the full order JSON for _any_ order, leaking all of Krusty Krab's data.
- **Severity:** 🟡 High

#### 6. "Time-of-Check, Time-of-Use" (TOCTOU) in Authorization

- **Method:** `PATCH /restaurants/{id}`
- **Scenario:** To update a restaurant, a user must be a manager. A user is a manager if their email domain matches the restaurant's `domain` field (e.g., `spongebob@krusty-krab.sea` matches `krusty-krab.sea`).
- **The Bug:** The handler is written in a flawed order:
  1.  Load restaurant from DB.
  2.  Update the restaurant object _in memory_ with data from the request body.
  3.  _Then_, check authorization: `if current_user.email.endswith(restaurant.domain):`
  4.  Save the (modified) restaurant object to DB.
- **Impact:** Plankton (`plankton@chum-bucket.sea`) wants to hijack Krusty Krab (`id=1`, `domain='krusty-krab.sea'`). He sends `PATCH /restaurants/1` with the body `{"domain": "chum-bucket.sea"}`.
  1.  Code loads Krusty Krab.
  2.  In-memory `restaurant.domain` is set to "chum-bucket.sea".
  3.  Auth check: `if "plankton@chum-bucket.sea".endswith("chum-bucket.sea")`: **Pass**.
  4.  The change is saved. Plankton has just hijacked the Krusty Krab account.
- **Severity:** 🔴 Critical

#### 8. Domain Authorization Bypass

- **Method:** `POST /restaurants`, `PATCH /restaurants/{id}`
- **Scenario:** Domain authorization reuses email verification tooling, when provided with the token it only validates that the domain matches. The verification email is sent to `admin@DOMAIN`, which is one of the industry-standard ways of email validation. The attacker that doesn't control a domain and only contains a single email address, can nevertheless bypass domain authentication by initiating new user registration with that email address and providing the received token to the restaurant domain change request.
- **The Bug:** The handler incorrectly accepts another token from user registration.
- **Impact:** Plankton uses the free email provider's address `plankton@bmail.sea` to bypass domain authentication and change his own restaurant's domain to `bmail.sea` (the domain change verification email was sent to `admin@bmail.sea`, but the handler incorrectly accepted another token from user registration).
- **Severity:** 🔴 Critical
