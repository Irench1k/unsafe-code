# Confusion Curriculum Blueprint for Contributors

This document is the master plan for the "Confusion / Inconsistent Interpretation" tutorial (runbooks r01-r05). This tutorial serves as the primary "on-ramp" for the Unsafe Code Lab.

## 1. Your Goal as a Contributor

Your mission is to **translate this narrative and these vulnerability patterns** into your target framework (e.g., Nest.js, Django, FastAPI, Express).

This plan exists to ensure a **consistent learning experience** across all languages. Students should be able to complete the Flask r01 tutorial and then the Nest.js r01 tutorial and feel a strong sense of familiarity. The endpoints, characters, and core vulnerability _patterns_ should be as identical as possible.

The vulnerabilities described here are largely framework-agnostic and follow realistic application evolution patterns, making them ideal for onboarding both students and contributors to new codebases.

## 2. Our Guiding Philosophy

This is _not_ a "secure development" class. Our goal is to teach white-box code review and vulnerability discovery.

- **Embrace Realistic Code:** We are not building puzzles or CTFs. The code must feel _real_. This means it can be imperfect, missing DRY principles, or inconsistent, just like a real-world app that has evolved over time. The vulnerability should be a _plausible_ mistake a real developer would make under pressure.
- **No "Magic" Vulns:** The vulnerability should not rely on obscure, long-patched library bugs. It should stem from the _misuse of the framework's own APIs_.
- **Focus on the Pattern:** Our taxonomy is based on _code-level review patterns_. The lesson for a student isn't "this is how you hack a coupon." The lesson is "I must always trace where data comes from, and I must be suspicious if a security check and a business logic function read that data from different sources."
- **Follow the Narrative:** The story of Sandy, Mr. Krabs, and Plankton is our teaching tool. The app's evolution (MVP -> middleware -> sessions) provides the context for _why_ code is being added or refactored. Use this story to frame your examples.

## 3. Technical & Narrative Setup

- **Narrative:** "Cheeky SaaS" is an online ordering platform for restaurants.
  - 🐿️ **Sandy Cheeks:** The developer (fast-moving, feature-focused).
  - 🦀 **Mr. Krabs:** The first customer (Krusty Krab).
  - 🧪 **Plankton:** The attacker (Chum Bucket).
  - (Others: SpongeBob 🧽, Squidward 🦑, Patrick 𓇼)
- **Technical Base:**
  - The API runs on `api.cheeky.sea`.
  - A (hypothetical) UI runs on `app.cheeky.sea`.
  - All endpoints for r01-r05 should ideally be bundled into a **single project/service** (e.g., one container).
  - Structure endpoints by version: `https://api.cheeky.sea/v1/`, ..., `https://api.cheeky.sea/v25/`
  - This mirrors real API evolution and keeps deployment simple (one container). If your framework makes this impractical, document your alternative approach and rationale.

**Important:** Design each endpoint as if the frontend exists. Include proper status codes, JSON responses, error handling, CORS configuration, etc. Don't build toy examples.

## 4. Why Start with Confusion?

Unlike SQL injection or CSRF, confusion vulnerabilities don't depend on framework-specific security features. They arise from fundamental mismatches in how different code paths interpret the "same" input. These patterns appear across all modern frameworks.

These bugs are everywhere because they're subtle: the code "works" in testing but breaks under adversarial input. Developers rarely test both `?item=burger` and `{"item": "burger"}` in the same request.

Finally, finding confusion bugs requires tracing data flow across functions, files, and layers. This is exactly the muscle memory needed for effective code review. Students learn to:

- Map logical inputs to their actual sources
- Compare security check assumptions vs. business logic reality
- Spot normalization mismatches and precedence conflicts

## 5. Code Quality Guidelines

This is **not** a secure development course. We're not teaching defensive coding, input validation best practices, or security-first architecture. That's unrealistic for code review work.

In real engagements, you can't tell clients "rewrite everything with security in mind." You need to find **actual exploitable bugs** in code that's already shipped. That's what we're training.

In particular:

- **DRY violations are fine** – Repeated logic that later diverges is a common source of confusion bugs
- **Missing abstractions are fine** – Not everything needs to be perfectly architected
- **Inconsistent style is fine** – Sandy's refactoring Q3 code in Q4, patterns shift
- **Edge cases ignored is fine** – "That can't happen" assumptions are realistic

But avoid:

- Logic that makes no business sense (why would this endpoint exist?)
- Bugs that break basic functionality (can't create an order at all)
- Framework anti-patterns that would be caught in code review (SQL strings without parameterization when the ORM is right there)

## 6. Structure of the Lab

The five categories build naturally on each other, mirroring how real applications evolve:

1. **r01: Input Source** → MVP with basic endpoints, multiple input formats
2. **r02: Authentication** → Add middleware, API keys, user context
3. **r03: Authorization** → Introduce resources, ownership, access control
4. **r04: Cardinality** → Handle lists, bulk operations, edge cases
5. **r05: Normalization** → String processing, database lookups, collision bugs

Each stage adds one major framework feature (middleware, sessions, JSON, SQL, validation) while showcasing how those features create new confusion opportunities.

## 7. Understanding Confusion Vulnerabilities (For Students)

Confusion vulnerabilities happen when code that **should be working with one logical value** ends up consulting **different representations or sources** of that value.

Think of it like this: you ask two people "What's the user's ID?" and get different answers because one person checked the URL path while the other read the request body. Both answers might be "correct" from their perspective, but the inconsistency creates a security gap.

### Why This Matters

Security decisions and business logic often live in different parts of your code:

- Middleware checks authentication: "Is this user allowed?"
- Handler performs actions: "Update this user's data"

If they're not reading from the same source, or if they normalize values differently, an attacker can satisfy the security check with one value while exploiting the business logic with another.

### How to Hunt for Confusion Bugs

When reviewing code, pick any important input (user ID, account ID, resource name, order ID) and trace it completely:

1. **Map all sources** – Where can this value enter? Query params? JSON body? Path? Headers? Session?
2. **Find all reads** – Every place the code accesses this value (searches help: grep for the key name)
3. **Compare access methods** – Does the security check looks at both the `request.args` and the `request.json` containers, while the handler only looks at one of them?
4. **Check normalization** – Does one path lowercase the value? Strip whitespace? Decode URLs? Cast types?
5. **Verify execution order** – Do guards run before or after merging/normalization?
6. **Test cardinality** – What happens if the attacker sends an array instead of a single value?

Look for "helpful" abstractions that hide complexity:

- Merged dictionaries that combine query + body + path
- Helper functions with precedence rules
- ORM methods that auto-cast types
- Middleware that modifies request context

The mismatch might be obvious (reading from different sources) or subtle (both use the same source but one normalizes first).

## 8. (r01) Input Source Confusion

_Feature focus:_ request parsing & merging (path/query/form/json/headers/cookies) \
_Student skill:_ follow a logical value across sources and precedence rules.

### What It Is

Source precedence bugs occur when different code paths read the "same" logical input from different locations. Your framework might support query strings, form data, JSON bodies, and path parameters. Each lands in a different container, and some helpers merge them with hidden priority rules.

### Framework Features Introduced

- Request parameter handling
- JSON parsing
- Path parameters
- Query string parsing
- Form data handling
- Basic routing

### Why Confusion Happens

- Different endpoints evolve independently
- Input handling copied between endpoints without consistency
- Framework provides multiple ways to access data (developer picks first one that works)

### The Story

Sandy Cheeks is building a restaurant ordering platform. She starts with a simple MVP: customers browse a menu and place orders. The Krusty Krab is her first tenant.

At this stage, authentication is basic (Sandy onboards each user manually, and uses hardcoded credentials & API keys for authentication). There's no multi-tenancy complexity yet. Sandy is focused on shipping features quickly, validating her MVP and finding product-market fit.

### Endpoints:

The lab starts with the minimal set of endpoints, matching the early MVP requirements:

| Method | Path             | Auth               | Purpose                   | Input                             | Response                                                     |
| ------ | ---------------- | ------------------ | ------------------------- | --------------------------------- | ------------------------------------------------------------ |
| GET    | /menu            | Public             | List available menu items | -                                 | `[{id, name, price}]`                                        |
| GET    | /orders          | Customer/X-API-Key | List orders               | -                                 | `[{order_id, total, items, delivery_address, delivery_fee}]` |
| POST   | /orders          | Customer           | Place new order           | `item?, items?, delivery_address` | `{order_id, total, items, delivery_address, delivery_fee}`   |
| GET    | /account/credits | Customer           | View balance              | -                                 | `{balance}`                                                  |

Throughout the section, we'll evolve the endpoints to add more features and complexity, mirroring the real-world app evolution. `POST /orders` gets removed to be replaced with `POST /cart` and `POST /cart/{id}/checkout`. Manual user onboarding gets replaced with the self-registration flow.

| Method | Path                       | Auth               | Purpose                                | Input                                 | Response                                                     |
| ------ | -------------------------- | ------------------ | -------------------------------------- | ------------------------------------- | ------------------------------------------------------------ |
| POST   | /cart                      | Customer           | Create cart                            | `items: [item_id]`                    | `{cart_id, items, total, coupon_code?}`                      |
| POST   | /cart/{id}/items           | Customer           | Add item to cart                       | `item_id`                             | `{cart_id, items, total, coupon_code?}`                      |
| POST   | /cart/{id}/checkout        | Customer           | Checkout cart                          | `delivery_address`, `tip?`            | `{order_id, total, items, delivery_address}`                 |
| PATCH  | /orders/{id}/status        | X-API-Key          | Update order status                    | `status`                              | `{order_id, total, delivery_address, status, cart_id, tip?}` |
| POST   | /orders/{id}/refund        | Customer/X-API-Key | Request refund (auto-accepted if <20%) | `order_id`, `amount?`, `reason?`      | `{order_id, total, amount, status}`                          |
| PATCH  | /orders/{id}/refund/status | X-API-Key          | Update refund status                   | `status`                              | `{order_id, total, amount, status}`                          |
| POST   | /auth/register             | Public             | Register user                          | `name`, `email`, `password`, `token?` | `{user_id, name, email}`                                     |

_Add a docker compose service for https://github.com/axllent/mailpit to capture verification emails sent during user registration_

> **Implementation Note:** Don't add complex authorization yet – that's r03. Use database-level ownership checks (e.g., `WHERE user_id = current_user`) to avoid accidental IDORs, but don't build a full RBAC system.

### Vulnerabilities to Implement

#### 1. Price Manipulation via Dual Parameters

**Scenario:** Sandy initially accepted a single `item` parameter. Later, she added support for `items` (array) but forgot to remove the old parameter.

**The Bug:**

- Price calculation reads `item` (single value)
- Order creation reads `items` (array)
- If both present, customer pays for one cheap item but receives expensive items

**Impact:** Customer pays for a $1 side of fries, gets a $20 Krabby Patty meal. \
**Severity:** 🔴 Critical

#### 2. Delivery Fee Bypass

**Scenario:** Sandy is adding a free delivery feature for orders over $25.00.

**The Bug:**

- Fee calculation reads `items` from query parameters
- Checkout reads `items` from request body
- Attacker sends fake high-value items in query to trigger free delivery, real low-value items in body

**Impact:** Customer with $10 order gets free delivery by lying about cart total in query string. \
**Severity:** 🟡 Medium

#### 3. Order Overwrite via ID Injection

**Scenario:** When refactoring to support JSON, Sandy merges the JSON into a template object.

**The Bug:**

- For form data: handler creates new order with generated ID
- For JSON: handler merges request JSON into template without sanitizing fields
- Attacker includes `order_id` in JSON body, causing upsert instead of insert

**Impact:** Attacker creates cheap order, then overwrites it with expensive items for free. \
**Severity:** 🔴 Critical

#### 4. Negative Tip

**Scenario:** Sandy is adding a new feature to allow customers to tip their delivery driver.

**The Bug:**

- Tip validation reads `tip` from request body
- Charge calculation reads `tip` from query parameter
- Attacker sends negative tip in query to offset order price, then pays the difference in the body

**Impact:** Customer offsets order price by a negative tip, gets free orders. \
**Severity:** 🔴 Critical

#### 5. Refund Fraud

**Scenario:** Sandy is adding a new feature to allow customers to refund their orders. If the order gets delayed, the client app automatically requests a refund of 20% of the order total, so the backend implements logic to automatically accept refunds of up to 20% of the order total – and to wait for manual resolution for refunds over 20%.

**The Bug:**

- Refund amount validation reads `amount` from JSON body (no value -> default 20% is set)
- When applied, the refund `amount` is accessed from the merged dictionary of form data and JSON body
- Attacker can send negative amount in urlencode form, bypassing the validation and causing the refund to be auto-accepted

**Impact:** Customer paid $2.49, gets $20.00 refund. Steals $17.51. \
**Severity:** 🔴 Critical

#### 6. Onboarding Fraud

**Scenario:** Sandy is adding a new feature to allow customers to onboard themselves. The registration is open to anyone, but requires email verification.

**Intended implementation:**

- The same handler `POST /auth/register` is used for both initial registration and email verification
- First, it receives `{email}` in the request body – and sends a signed (stateless) verification token to the email address
- When the user receives the verification email, they click the link in the email and fill in the rest of the registration form in the web UI
- On submission, the same handler is called again - this time with `{email, password}`
- The handler verifies the token and creates the user with the provided email and password
- New user gets $2.00 credit on their account - not enough to place an order, and meant to be a discount equivalent

**The Bug:**

- Token validation routine checks expiration, signature and `token.email` uniqueness
- User creation reads `body.email` if available, and only falls back to `token.email` if not
- There is no validation that the `email` parameter matches the email embedded in the token
- In case of email collision, the user creation routine resets the password to the provided one and adds $2.00 credit to the existing account

**Impact:**

- Attacker can perform account takeover by initiating new registration and providing `body.email` that matches the email of an existing user – causing their password to be set to the one chosen by the attacker
- Attacker can accumulate free credits by providing in `body.email` an email address of their existing account – replaying this requst won't finish the creation of a new account, but will keep adding $2.00 credit increments to the attacker's existing account

**Severity:** 🟡 High

## 9. (r02) Authentication Confusion

### What It Is

Authentication confusion occurs when the code that **verifies identity** examines a different value than the code that **acts on identity**. One path checks "Is Alice authenticated?" while another path operates on a user ID that says "Bob."

This is distinct from authorization (which checks permissions). We're talking about basic identity mix-ups: checking the session but using the query string, verifying a JWT claim but trusting a header, etc.

### Framework Features Introduced

- Middleware/decorators
- Request context enrichment
- Session handling
- Authentication guards
- Custom headers

### Why Confusion Happens

- Middleware sets context from one source (headers)
- Business logic reads from different source (path/body)
- Multiple authentication methods coexist
- Context enrichment creates derived values

### The Story

Business is growing! Sandy adds proper authentication middleware and API keys. SpongeBob and Squidward (Krusty Krab employees) get access to a merchant portal. Multiple customers are now using the platform.

Sandy introduces sessions, user accounts, and role-based access (customer vs. merchant). Authentication is still simple but now properly enforced via middleware.

### Endpoints:

| Method | Path             | Auth               | Purpose                | Input                | Response                                                     |
| ------ | ---------------- | ------------------ | ---------------------- | -------------------- | ------------------------------------------------------------ |
| POST   | /auth/login      | Public             | Create session         | `email`, `password`  | `{user_id, session_id}`                                      |
| POST   | /auth/logout     | Customer           | Destroy session        | -                    | `{}`                                                         |
| GET    | /cart/{id}       | Customer/X-API-Key | Get cart               | `cart_id`            | `{cart_id, items, total, coupon_code?}`                      |
| GET    | /orders/{id}     | Customer/X-API-Key | Get order              | `order_id`           | `{order_id, total, delivery_address, status, cart_id, tip?}` |
| POST   | /account/credits | X-Admin-API-Key    | Add credits (internal) | `customer`, `amount` | `{customer, amount, balance}`                                |

The authentication methods we cover in this runbook:

- Basic Auth
- Cookie-based session
- Restaurant API key `X-API-Key`
- Platform API key `X-Admin-API-Key` (only Sandy herself is using this)

Notes:

- both Cookies and API keys could be implemented as JWT tokens if that makes it easier / more typical for the framework - right now we don't cover JWT specific vulns, so it's not important for now.
- set cookies to `Strict` and implement CORS from the start. This should be enough to prevent unintended CSRF vulns, but please double-check that the only vulnerabilities in our examples are the ones we're intentionally covering

### Vulnerabilities to Implement

#### 1. Authentication Type Confusion

- **Method:** `GET /orders`, `POST /cart`, `POST /cart/{id}/checkout`
- **Scenario:** Sandy implements Cookie-based session authentication for the UI, but the Basic Auth remains supported.
- **The Bug:** Basic Auth middleware sets `request.user_id` from the username in the request headers, before validating the credentials. Attacker can provide valid Cookie for his own account, and Basic Auth header for victim's account (without providing the password), resulting in authentication bypass.
- **Impact:** Attacker can access victim's order history, and to spend their credits.
- **Severity:** 🔴 Critical

#### 2. Auth Check Bypassed by Method Confusion

- **Method:** `GET /account/credits` (Exploited)
- **Scenario:** Sandy creates an internal admin endpoint (`/account/credits`) to add credits. She shares the route handler for both `GET` (to view) and `POST` (to add), but only protects the `POST` method with her `X-Admin-API-Key` check.
- **The Bug:** The authentication check is strictly tied to the `POST` HTTP method. However, the business logic for adding credits (which reads `customer` and `amount` from the request **body**) is in the shared handler and isn't gated by the method. Many frameworks (like Flask or FastAPI) will still parse a request body on a `GET` request.
- **Impact:** Plankton sends a `GET /account/credits` request with a JSON body (`{"customer": "plankton", "amount": 99999}`). The `POST`-specific auth check is skipped, but the business logic finds the body parameters and successfully adds credits to his account.
- **Severity:** 🔴 Critical

#### 3. Incomplete Auth Validation (Presence vs. Validity)

- **Method:** `PATCH /orders/{id}/refund/status`
- **Scenario:** This endpoint is for restaurants (merchants) to approve or deny a refund and must be called with a valid restaurant API key.
- **The Bug:** The request goes through two checks:
  1.  A global auth middleware checks for _any_ valid authentication (a customer cookie _or_ an API key).
  2.  A route-specific decorator checks _only for the presence_ of the `X-API-Key` header (e.g., `if 'X-API-Key' in request.headers:`), assuming the middleware already validated it.
- **Impact:** Plankton authenticates with his valid _customer cookie_ (passes check #1). He then adds a _fake, invalid_ `X-API-Key: foo` header. The decorator (check #2) is satisfied because the header is present. The handler now executes, believing it's running as a restaurant, and approves Plankton's own refund.
- **Severity:** 🟡 High

#### 4. Auth Context Pollution from Failed Validation

- **Method:** `GET /orders`
- **Scenario:** Sandy refactors her auth middleware to be "helpful" by setting the `user_type` on the request context (e.g., `request.user_type = 'merchant'`) as soon as it sees an API key, _before_ validating it.
- **The Bug:** The middleware logic is flawed: 1) `if 'X-API-Key' in headers: request.user_type = 'merchant'`. 2) It then tries to validate the key. 3) If validation fails, it _forgets to reset_ `request.user_type` and moves on to check for a cookie. The `GET /orders` handler later trusts this `user_type` variable.
- **Impact:** Plankton sends a request with his valid _customer cookie_ AND a _fake_ `X-API-Key` header. The middleware sets `user_type = 'merchant'`, fails to validate the key, then successfully validates his cookie. The request proceeds. The handler sees `user_type == 'merchant'` and leaks _all_ restaurant orders.
- **Severity:** 🟡 High

#### 5. Authentication Bypass via Parameter Mismatch

- **Method:** `POST /auth/login`
- **Scenario:** Sandy refactors her auth middleware to be "helpful" by setting the `email` claim on the request context (e.g., `request.email = request.body.email`) as soon as it sees an email in the request body, _before_ validating it. The recent refactoring introduced a bug where this would be added to active session as well, if it existed (which is not expected for `/auth/login` endpoint).
- **The Bug:** Login handler is meant to set the `email` claim on the request context, but if provided with the cookie sesion - it will update `email` claim there instead. This is insecure, because this claim gets set before the email is validated, and session survives this single request.
- **Impact:** Plankton sends a request with his valid _customer cookie_ AND a _fake_ `email` in the body. The middleware sets `email = 'spongebob@krusty-krab.sea'`, fails to validate the email, but still sets the session `email` claim to `spongebob@krusty-krab.sea`. Follow-up requests with this cookie will authorize Plankton as `spongebob@krusty-krab.sea`.
- **Severity:** 🔴 Critical

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

## r04: Cardinality Confusion

### What It Is

Cardinality confusion occurs when one part of the code treats a parameter as a **single value** while another treats it as a **list**. The parser, validator, and business logic disagree on whether you sent one item or many.

This includes:

- Singular vs. plural parameter names (`item` vs. `items`)
- Single-value accessors vs. multi-value accessors (`.get()` vs. `.getlist()`)
- Type coercion that flattens or wraps values
- Default value handling that changes effective cardinality

### Framework Features Introduced

- List parameter parsing
- `.get()` vs `.getlist()` methods
- Array destructuring
- First-value extraction
- Multi-value headers

### Why Confusion Happens

- One component expects single value
- Another component provides array
- Framework APIs have different default behaviors
- `.get()` returns first element silently

### The Story

Customers love the platform! Sandy adds bulk order features (order multiple items at once) and discounts for bulk purchases. Restaurants want to update multiple menu items simultaneously.

Squidward is still causing trouble. He discovers he can manipulate requests to get unauthorized discounts or bypass limits.

### Endpoints:

| Method | Path                    | Auth       | Purpose                | Input                        | Response                                     | Changes               |
| ------ | ----------------------- | ---------- | ---------------------- | ---------------------------- | -------------------------------------------- | --------------------- |
| POST   | /coupons                | Restaurant | Create coupon          | `code`, `discount_percent`   | `{code, discount_percent}`                   |
| POST   | /cart/{id}/apply-coupon | Customer   | Apply coupon           | `code`                       | `{cart_id, items, total, coupon_code}`       |
| POST   | /orders/bulk-refund     | Restaurant | Refund multiple orders | `order_ids: [order_id, ...]` | `{success: true, refunded: [order_id, ...]}` | NEW: Batch operations |
| GET    | /reports/orders         | Restaurant | Export orders as CSV   | `restaurant_id`              | `CSV`                                        | NEW: Batch operations |

### Vulnerabilities to Implement

#### 1. Free Orders Due to Coupon Stacking

**Endpoint(s):** `POST /v401/cart/{id}/apply-coupon`

**Setup:**
Only one coupon can be applied to a cart.

**The Vulnerability:**

The "check" path validates the coupon code **from the form parameter** and verifies that cart does not have a coupon already applied.

The "coupon application" path uses coupon code **from the query parameter**, deducts the discount from the cart total, and overwrites the existing coupon code in the database.

**Attack Scenario:**

1. Plankton sends: `POST /v401/cart/5/apply-coupon?code=BURGER20` with NO form data
2. Validation does not find any coupon code in the form data, so it passes the check
3. The coupon application path deducts the discount from the cart total, and overwrites the existing coupon code in the database.
4. Plankton repeats the attack with a different coupon code, until the cart total is reduced to 0.

**Root Cause:**
Validation operates on one input source (form), while the coupon application path uses a different input source (query parameter). Cart total is decremented without being recalculated at checkout.

**Impact:**
Plankton can apply multiple coupons to his cart, getting a free order.

**Severity:** 🟡 Medium

#### 2. Authorization Confusion (Any vs. All)

- **Method:** `POST /orders/bulk-refund`
- **Scenario:** Sandy adds a bulk refund feature for restaurants. A restaurant can submit a list of `order_ids` to refund.
- **The Bug:** The authorization decorator is "efficient." It checks: "Does this restaurant own _any_ of the orders in this list?" (e.g., `SELECT 1 FROM orders WHERE id IN (...) AND owner_id = ... LIMIT 1`). The handler, however, iterates through the _entire_ list of `order_ids` from the request and processes a refund for each one.
- **Impact:** Plankton (Chum Bucket) sends `{"order_ids": [123, 456, 789]}`, where `123` is his own order, but `456` and `789` belong to Krusty Krab. The auth check passes (he owns `123`). The handler then refunds all three orders.
- **Severity:** 🔴 Critical

#### 3. Discount Stacking via Input Source Confusion

- **Method:** `POST /cart/{id}/apply-coupon`
- **Scenario:** Sandy introduces single-use coupons to be sent to Bikini Bottom citizens in physical envelopes. Stacking IS allowed now, as these are basically gift codes. But a single-use coupon should only be applied once.
- **The Bug:** The logic is split:
  1. The "check" valides all provided codes, filters out invalid ones, and schedules the single-use ones for deletion.
  2. The "apply" logic (add coupon to cart) iterates through the raw list of the codes, filters out the ones that are not in request.allowed_codes and applies the ones that are.
  3. This ensures that invalid codes don't get applied, but doesn't prevent the same code from being applied multiple times.
- **Impact:** Plankton can apply the same single-use coupon multiple times in one request, getting a much larger discount than intended.
- **Severity:** 🟡 High

#### 4. Cross-Restaurant Menu Item Modification

- **Method:** `PATCH /menu/items/{id}`
- **Scenario:** "Check" and "apply" logic both use the same helper for extracting the restaurant_id from the query arguments. This helper uses `.pop()` to remove the first item from the query args. So, for a regular request with a single `restaurant_id` query argument, the helper will return the first item for validation, and None for the database query. This bug was discovered, but it was fixed incorrectly - by adding a fallback in the header that returns `restaurant_id` from the request context if the argument is None.
- **The Bug:** If two `restaurant_id` query arguments are provided, the handler will validate first one but provide the second one to the database query.
- **Impact:** Attacker can modify menu items for other restaurants.
- **Severity:** 🔴 Critical

#### 5. Negative Multipliers

- **Method:** `POST /cart/{id}/items`
- **Scenario:** Sandy introduces a new feature, item counts, to avoid adding the same item multiple times.
- **The Bug:** The handler always adds at least one item, but total calculation just multiplies the count by the price.
- **Impact:** Attacker can get free items by abusing 0 or negative multipliers.
- **Severity:** 🟡 High

## r05: Normalization Issues

### What It Is

Character normalization confusion happens when two code paths apply **different string transformations** to the same logical input. One path might lowercase, the other might not. One might strip whitespace, the other might only trim. One might apply Unicode normalization, the other might ignore it.

Result: values that should be "equal" diverge when checked vs. used, bypassing uniqueness constraints, access controls, or security boundaries.

### Framework Features Introduced

- String manipulation
- Database constraints
- Text search/indexes
- Regular expressions
- Unicode handling

### Why Confusion Happens

- Different normalization in different layers
- Database does normalization automatically
- Case-insensitive vs case-sensitive comparisons
- Regex special characters
- Unicode normalization mismatches

### The Story

The platform is getting popular beyond Bikini Bottom! Sandy adds a review system, custom domains for restaurants, and public restaurant pages with human-readable URLs (slugs).

Plankton is relentless. He exploits every normalization bug to hijack Krusty Krab's reviews, steal their subdomain, and confuse customers into visiting his copycat restaurant.

### Endpoints:

| Method | Path                               | Auth       | Purpose                      | Input          | Response                                | Changes  |
| ------ | ---------------------------------- | ---------- | ---------------------------- | -------------- | --------------------------------------- | -------- |
| POST   | /restaurants                       | Restaurant | Create restaurant            | `name`, `slug` | `{restaurant_id, name, slug}`           | NEW      |
| GET    | /restaurants                       | Public     | List restaurants             | -              | `[{restaurant_id, name, slug}]`         | NEW      |
| PATCH  | /restaurants/{slug}                | Restaurant | Update restaurant info       | `name`, `slug` | `{restaurant_id, name, slug}`           | MODIFIED |
| GET    | /restaurants/{slug}                | Public     | Get restaurant info          | `slug`         | `{restaurant_id, name, slug}`           | NEW      |
| GET    | /restaurants/{slug}/menu           | Public     | Get restaurant menu          | `slug`         | `[{item_id, name, price}]`              | NEW      |
| GET    | /restaurants/{slug}/orders         | Public     | Get restaurant orders        | `slug`         | `[{order_id, customer, total, status}]` | NEW      |
| GET    | /restaurants/{slug}/coupons        | Public     | Get restaurant coupons       | `slug`         | `[{coupon_id, code, discount_percent}]` | NEW      |
| GET    | /restaurants/{slug}/reports/orders | Public     | Get restaurant orders report | `slug`         | `CSV`                                   | NEW      |
| PATCH  | /restaurants/{slug}                | Restaurant | Update restaurant info       | `name`, `slug` | `{restaurant_id, name, slug}`           | MODIFIED |
| DELETE | /restaurants/{slug}                | Restaurant | Delete restaurant            | `slug`         | `{restaurant_id, name, slug}`           | NEW      |

### Vulnerabilities to Implement

#### 1. Coupon Code Leak: Validation Pattern vs SQL Wildcard

**Endpoint(s):** `POST /v501/cart/{id}/apply-coupon`

**Setup:**
Sandy implements coupon validation. Codes must be alphanumeric. Database stores coupons with format `{restaurant_id}_{code}`, e.g., `1_BURGER20`.

**The Vulnerability:**

- Validation checks form parameter: `if re.match(r'^[A-Z0-9]+$', body.code): pass`
- Database query uses query parameter: `SELECT * FROM coupons WHERE code LIKE '{restaurant_id}_{query.code}%'`

_Note: If the framework makes `%` injection unlikely due to auto-escape, collect all the coupon codes 'for caching purposes' and match them using regex (replacing `%` in the attack with `.*`)_

**Attack Scenario:**

1. Krusty Krab has coupons: `1_BURGER20`, `1_BURGER50`, `1_BURGERMANIA`
2. Plankton sends: `POST /v501/cart/5/apply-coupon?code=%` with form data: `code=BURGER20`
3. Validation checks form data: `BURGER20` ✓ (alphanumeric)
4. Database searches: `LIKE '1_%'` (wildcard matches all restaurant 1 coupons)
5. Query returns multiple rows, exception reveals all codes in error message

**Root Cause:**
Validation operates on one input source (form), SQL query uses different source (query param), SQL wildcards not escaped.

**Impact:**
Information disclosure - leaking all restaurant coupon codes via error messages.

**Severity:** 🟡 Medium

**Framework Translation Notes:**

- SQL wildcards: `%`, `_` in LIKE clauses
- ORM query building: some auto-escape, others require explicit escaping
- Error message exposure varies by framework debug settings

#### 2. Domain Extraction from Email

**Endpoint(s):** `GET /v502/restaurants/{id}/settings`

**Setup:**
Sandy implements a "manager by domain" feature. If your email is `employee@krusty-krab.sea`, you automatically have manager access to any restaurant with domain `krusty-krab.sea`.

**The Vulnerability:**
Session contains `email` field. Middleware extracts domain by splitting on `@` and taking the second part: `session.domain = email.split('@')[1]`. Authorization checks if this domain matches the restaurant's domain.

**Attack Scenario:**

1. Plankton registers new user with email `plankton＠krusty-krab.sea@chum-bucket.sea` (the first character is `FULLWIDTH COMMERCIAL AT` / `U+FF20` – NOT regular `@` sign)
2. Email validation recognizes `chum-bucket.sea` as the email's domain
3. When storing the email in the session, the framework or database layer normalizes it (NFKC) to `plankton@krusty-krab.sea@chum-bucket.sea` (now both @ signs are the same)
4. Upon login, the middleware extracts `session.email = "plankton@krusty-krab.sea@chum-bucket.sea"`, based on which the domain is retrieved as `session.domain = "krusty-krab.sea"` and Plankton is granted manager access to Krusty Krab restaurant.

**The Vulnerability:**
Middleware extracts domain by: `domain = email.split('@')[1]` (takes second element, not last element). This assumes that the email has been validated on registration, however the normalization step was performed AFTER the email was validated!

**Root Cause:**
Naive email parsing that doesn't account for normalization steps that are performed after the email is validated.

**Impact:**
Complete account takeover of any restaurant by registering crafted email addresses.

**Severity:** 🔴 Critical

**Framework Translation Notes:**

- Email validation varies widely (regex vs library vs framework built-in)
- Some validators normalize, others preserve exact format
- String splitting is universal but implementation might use `rsplit`, `split(..., 1)`, regex
- Test what email formats your framework's validator accepts

#### 3. Privilege Escalation: Database Truncation

**Endpoint(s):** `POST /v503/auth/register`

**Setup:**
Sandy implements email verification. Certain domains (e.g., `@krusty-krab.sea`) are privileged – users with those domains are automatically considered managers.

**The Vulnerability:**

Validation path sends the email verification token to the email address.

Registration path inserts the user into the database without checking for the length of the email address.

**Attack Scenario:**

1. Database email column is `VARCHAR(50)`
2. Plankton registers: `long-prefix-xxxxxxxxxxxxxxxxxx@krusty-krab.sea.chum-bucket.sea`
3. Validation path sends the email verification token to the email address.
4. Plankton receives the email (as it arrives to the subdomain under his control)
5. Plankton verifies the email address and completes the registration form.
6. Registration path inserts the user into the database, causing truncation of the email address to `long-prefix-xxxxxxxxxxxxxxxxxx@krusty-krab.sea`
7. Plankton knows password and can login as a manager for Krusty Krab.

**Root Cause:**
Validation operates on full string, database silently truncates.

**Impact:**
Privilege escalation - registering as manager for Krusty Krab.

**Severity:** 🔴 Critical

#### 4. Review Theft: Case Sensitivity

**Endpoint(s):**

- `POST /v504/restaurants` (creation with uniqueness check)
- `POST /v504/webhooks/reviews?restaurant_name={name}`

**Setup:**
Sandy integrates a review aggregation service. Reviews are attributed by restaurant name. She enforces unique restaurant names during creation.

**The Vulnerability:**
Creation endpoint checks uniqueness: `Restaurant.query.filter_by(name=name).first()` (case-sensitive)

Webhook looks up: `Restaurant.query.filter(Restaurant.name.ilike(name)).first()` (case-insensitive)

**Attack Scenario:**

1. Krusty Krab exists with name `Krusty Krab`
2. Plankton creates restaurant: `KRUSTY KRAB` (passes uniqueness check - different case)
3. Review service sends webhook: `POST /webhooks/reviews?restaurant_name=krusty%20krab`
4. Webhook looks up case-insensitively, finds two restaurants
5. Reviews attributed to the first restaurant (time descending order)
6. Plankton's restaurant receives Krusty Krab's positive reviews

**Root Cause:**
Uniqueness enforcement is case-sensitive, lookup is case-insensitive, creating collision opportunity.

**Impact:**
Review theft - hijacking another restaurant's reputation.

**Severity:** 🟡 Medium

**Framework Translation Notes:**

- Database collation: some databases are case-insensitive by default (MySQL), others case-sensitive (PostgreSQL)
- ORM query methods: `.filter()`, `.filter_by()`, `.ilike()`, `.lower()`
- Index case-sensitivity affects lookups
- Framework may normalize strings in validation but not in queries

#### 5. Review Theft: Whitespace Normalization

**Endpoint(s):**

- `PATCH /v505/restaurants/{id}` (update with normalization)
- `POST /v505/webhooks/reviews?restaurant_name={name}`

**Setup:**
Sandy fixes the case sensitivity issue by normalizing both sides: `name.lower().strip()`. She updates both endpoints to normalize consistently.

**The Vulnerability:**
Update endpoint strips: `name.lower().replace(r' ', '')` (removes space only)
Webhook strips differently: `name.lower().replace(r'\s', '')` (removes ALL whitespace via regex)

**Attack Scenario:**

1. Krusty Krab has name `Krusty Krab` (with space)
2. Plankton updates his restaurant to: `Krusty Krab\t` (with tab character `\t`)
3. Update normalization: `'Krusty Krab\t'.lower().replace(r' ', '') = 'krustykrab\t'`
4. Uniqueness check passes (different from `krustykrab`)
5. Webhook normalization: `'krustykrab\t'.replace(r'\s', '') = 'krustykrab'` and `'krustykrab'.replace(r'\s', '') = 'krustykrab'`
6. Both normalize to the same value, Plankton hijacks reviews

**Root Cause:**
Different whitespace normalization rules - `.replace(' ', '')` vs `.replace('\s', '')` - match different whitespace classes.

**Impact:**
Review theft via whitespace exploitation.

**Severity:** 🟡 Medium

**Framework Translation Notes:**

- Whitespace characters: space, tab, newline, carriage return, etc.
- Regex `\s` matches all whitespace, `.strip()` only leading/trailing
- URL encoding of whitespace: `%20`, `%09`, `%0A`
- Framework may normalize URLs before they reach application code

#### 6. Review Theft: Unicode Normalization

**Endpoint(s):**

- `PATCH /v506/restaurants/{id}` (update with comprehensive normalization)
- `POST /v506/webhooks/reviews?restaurant_name={name}` (with database index)

**Setup:**

Sandy adds even more normalization: lowercase, trim, and validates uniqueness against all existing restaurants. The webhook uses a Postgres search index for performance: `CREATE INDEX idx_restaurant_name_searchable ON restaurants (lower(unaccent(name)))`.

**The Vulnerability:**

Application-level uniqueness check: `existing_names = [r.name.lower().replace(r'\s', '') for r in all_restaurants]; if normalized_name in existing_names: reject`

Database index for webhook: `lower(unaccent(name))` where `unaccent()` removes diacritics

**Attack Scenario:**

1. Krusty Krab has name `Krusty Krab`
2. Plankton updates his restaurant to: `Krusty Krạb` (with Vietnamese `ạ` instead of Latin `a`)
3. Application check compares: `'Krusty Krаb'` vs `'Krusty Krạb'` (different, passes)
4. Webhook searches database using `unaccent()`: both normalize to `Krusty Krab`
5. Plankton hijacks reviews

**Root Cause:**

Application logic doesn't apply same normalization as database index - missing diacritic/script removal.

**Impact:**

Review theft via Unicode exploitation.

**Severity:** 🟡 Medium

**Framework Translation Notes:**

- Unicode normalization forms: NFC, NFD, NFKC, NFKD
- Database functions: `unaccent()` (Postgres), `CONVERT()` (MySQL)
- Lookalike characters: Cyrillic vs Latin, fullwidth vs halfwidth
- Framework may have built-in Unicode normalization, but it must match database behavior

#### 7. Review Theft: Underscore Wildcard

**Endpoint(s):** `POST /v507/restaurants`

**Setup:**
Sandy is frustrated with Plankton's exploits. She implements aggressive sanitization:

1. Lowercase and trim
2. Apply NFKC normalization
3. Filter to alphanumeric with regex `\w+`
4. Database uniqueness check
5. Before insertion, remove all non-alphanumeric (except whitespace)
6. Auto-capitalize the name in UI

**The Vulnerability:**

- Validation path: Regex `\w` matches: `[A-Za-z0-9_]` (includes underscore)
- Insertion path: Non-alphanumeric filter before insertion: `re.sub(r'[^A-Za-z0-9\s]', '', name)` (removes everything except letters, numbers, spaces)

**Attack Scenario:**

1. Krusty Krab has name `Krusty Krab`
2. Plankton registers: `Krusty Krab_`
3. Sanitization: lowercase + trim + NFKC → `krusty krab_`
4. Regex validation: `\w+` matches (underscore is `\w`) ✓
5. Database check: `krusty krab_` vs `krusty krab` (unique) ✓
6. Pre-insertion filter: removes `_` → `krusty krab`
7. Database stores `krusty krab`, colliding with existing restaurant

**Root Cause:**
Inconsistent character filtering - validation allows underscore (`\w`), insertion removes it, creating collision.

**Impact:**
Review theft.

**Severity:** 🟠 High

**Framework Translation Notes:**

- Regex character classes: `\w`, `\d`, `\s` definitions vary by language/locale
- Some regex engines support Unicode character classes
- Double-sanitization patterns common in refactored code

#### 8. Slug Collision: Non-Idempotent Normalization

**Endpoint(s):** `PATCH /v508/restaurants/{slug}`

**Setup:**
Sandy replaces numeric IDs with slugs for SEO. She generates slugs from restaurant names with a helper function `slugify(name)`. Uniqueness is checked by calling `slugify()` on the new name and comparing to existing slugs.

**The Vulnerability:**
The `slugify()` helper is non-idempotent:

```python
def slugify(name):
    s = name.lower()
    s = re.sub(r'-+', '-', s)  # Collapse multiple hyphens FIRST
    s = re.sub(r'[^a-z0-9]+', '-', s)  # Replace non-alphanum with hyphens
    return s.strip('-')
```

First call: `slugify('krusty!-krab') → 'krusty--krab'`
Second call: `slugify('krusty--krab') → 'krusty-krab'` (same)

But during validation, we call it once on the existing slug. During insertion, we call it again on potentially different input.

**Attack Scenario:**

1. Krusty Krab has slug `krusty-krab`
2. Plankton registers: `krusty!-krab`
3. Validation: `slugify('krusty!-krab') = 'krusty--krab'` (unique) ✓
4. Insertion: `slugify('krusty--krab') = 'krusty-krab'` (collides) ✗

**Root Cause:**
Non-idempotent slugification + validation and insertion operating on different input fields.

**Impact:**
Slug collision, takeover of restaurant profile URLs.

**Severity:** 🟠 High

**Framework Translation Notes:**

- Slug generation libraries vary (language-specific)
- Idempotency: calling `f(f(x)) = f(x)` vs `f(f(x)) ≠ f(x)`
- Validation vs persistence field mapping

#### 9. Slug Collision: Domain to Slug Conversion

**Endpoint(s):** `POST /v509/restaurants`

**Setup:**
Sandy decides to use domain names as slugs (one slug per domain, auto-enforced uniqueness). She converts domain to slug by replacing dots with hyphens.

The idea is that since domain names are unique, and slugs are generated from domain names, slugs should be unique as well. No need to check for uniqueness again.

**The Vulnerability:**

Slug generation: `slug = domain.replace('.', '-')`

Domains `krusty.krab.sea` and `krusty-krab.sea` both produce slug `krusty-krab-sea`

**Attack Scenario:**

1. Krusty Krab has domain `krusty-krab.sea` → slug `krusty-krab-sea`
2. Plankton registers domain `krusty.krab.sea` → slug `krusty-krab-sea`

**Root Cause:**
Lossy conversion - multiple distinct inputs (domains with dots vs hyphens) map to same output (slug).

**Impact:**
Slug collision, URL confusion, profile takeover.

**Severity:** 🟠 High

**Framework Translation Notes:**

- DNS restrictions: dots are required in domains, hyphens are allowed
- Character replacement in slugs: dots, spaces, special chars → hyphens
- Reversibility: slug should ideally be convertible back to original or have separate storage

#### 10. Slug Collision: Unescaped Dots in Regex

**Endpoint(s):** `POST /v510/restaurants`

**Setup:**

Sandy is tired of Plankton's shenanigans. She decides to use domain names as slugs, without any modifications.

**The Vulnerability:**

- Even though domain names are not manged anymore, the matching logic still relies on regex, and it doesn't escape the dots in the domain names.

**Attack Scenario:**

1. Plankton registers: `krusty.krab.sea`
2. Registration succeeds
3. Plankton uses API with the slug `/restaurants/krusty.krab.sea`
4. Authorization middleware identifies Plankton's restaurant by the slug and grants access to the restaurant's resources
5. Data access layer retrieves the restaurant by the slug, and comes up with Mr. Krabs' restaurant's resources instead - authorization bypass!

**Impact:**

Authorization bypass, potential data exfiltration.

**Severity:** 🔴 Critical

#### 11. Domain Verification: String Suffix Matching

**Endpoint(s):**

- `POST /v511/restaurants`
- `PATCH /v511/restaurants/{id}/domain`

**Setup:**
Sandy implements domain ownership verification. To change a restaurant's domain, you must verify ownership by receiving an email at that domain. The system sends an email with a verification token.

**The Vulnerability:**
Verification check: `if token.email.endswith(restaurant.domain): approve`

**Attack Scenario:**

1. Krusty Krab has domain `krusty-krab.sea`
2. Plankton owns domain `not-krusty-krab.sea`
3. He starts registering a new restaurant with domain `not-krusty-krab.sea`
4. System sends verification email to `admin@not-krusty-krab.sea` (his verified email)
5. He verifies the domain change for Chum Bucket to `krusty-krab.sea`, providing the token received for `admin@not-krusty-krab.sea`
6. The domain change is approved, and Chum Bucket's domain is changed to `krusty-krab.sea`

Now when customers visit `/restaurants/krusty-krab.sea` (slug from domain), they get Plankton's restaurant instead of Krusty Krab's.

**Root Cause:**
String suffix matching without anchor - `endswith()` matches any suffix, not just after `@`.

**Severity:** 🟠 High

**Framework Translation Notes:**

- String matching: `.endswith()`, `.ends_with()`, regex `$` anchor
- Email parsing: split on `@` vs proper email validation library
- Framework may have email validation utilities, but domain extraction requires careful implementation

# Ideas to consider in the future

1. JWT specific vulnerabilities
2. Multi-stage email verification
   - The way we implement it right now is within the same handler (it generates token and sends email when no `token` provided, and validates it when available)
   - This avoids the need to have pending-intent tables, reducing cognitive load on the student
   - However, there migth be some nice 'Confusion / Inconsistent Interpretation' vulnerabilities lurking in those multi-request flows
3. Session storage as stateful source of confusion
   - Similarly how many vulnerabilities are based on mixing the input source, there could be vulnerabilities where first request adds something to the session, and second request accesses that value for check / data access, instead of the regular request params
4. Other state management issues between endpoints?
5. Should we split r05 Normalization into:
   - Character Normalization (case, whitespace, unicode, regex)
   - Structural Normalization (truncation, slug generation, ID collisions)
