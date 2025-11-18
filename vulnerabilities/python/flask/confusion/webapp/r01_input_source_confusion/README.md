## r01: Input Source Confusion

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

### Endpoints

| Lifecycle | Method | Path                | Auth                | Purpose                   | Vulnerabilities |
| --------- | ------ | ------------------- | ------------------- | ------------------------- | --------------- |
| v101+     | GET    | /account/credits    | Customer            | View balance              |                 |
| v106+     | GET    | /account/info       | Customer            | View account summary      |                 |
| v101+     | GET    | /menu               | Public              | List available menu items |                 |
| v101+     | GET    | /orders             | Customer/Restaurant | List orders               |                 |
| v101-v102 | POST   | /orders             | Customer            | Create new order          | v101, v102      |
| v103+     | POST   | /cart               | Customer            | Create cart               |                 |
| v103+     | POST   | /cart/{id}/items    | Customer            | Add item to cart          |                 |
| v103+     | POST   | /cart/{id}/checkout | Customer            | Checkout cart             | v103, v104      |
| v105+     | POST   | /orders/{id}/refund | Customer            | Request refund            | v105            |
| v106+     | POST   | /auth/register      | Public              | Register user             | v106, v107      |

### Vulnerabilities to Implement

#### [v101] Premium Meal for Side Dish Price

> The initial in-restaurant tablet pilot (single-item promo combos only) went great, so Mr. Krabs now wants the full menu. Sandy updates the kiosk app (still Basic Auth, still physically inside Krusty Krab) so a single `POST /orders` can hold multiple items.

**The Vulnerability**

- Sandy adds support for multi-item orders via a new `items[]` parameter while keeping legacy `item` for backwards compatibility.
- Price calculation checks if `item` exists first; if present, it only prices that single item—ignoring `items[]` entirely.
- Order fulfillment prioritizes `items[]`; it falls back to `item` only if `items[]` is empty.
- Sending both parameters prices only the single `item` but fulfills the entire `items[]` array.

**Exploit**

1. Send form data with both `item=3` (a $2 side) and `items=1&items=2&items=3` (three items totaling $31).
2. Price calculator sees `item` is present and charges only $2.
3. Order fulfillment sees `items[]` has values and creates an order with all three items.

**Impact:** Customer pays for one cheap item but receives multiple expensive items. \
**Severity:** 🟠 High \
**Endpoints:** `POST /orders`

_Aftermath: With positive kiosk feedback, Mr. Krabs signs off on the delivery service trial next._

---

#### [v102] Delivery Fee Bypass

> Sandy lends tablets to a few VIP customers for home delivery orders. She adds a `delivery_address` field and implements free delivery for orders over $25 (otherwise $5 flat fee).

**The Vulnerability**

- `calculate_delivery_fee()` totals `request.values`, so query parameters override form data.
- The order creation only reads the request data from the body, ignoring the query string.

**Exploit**

1. Add $10 worth of items to your order (body parameter).
2. Include expensive items in the query string `?items=6&items=1` to push the calculated total over $25.
3. The delivery fee calculator sees query + form data (crossing the $25 threshold), while order creation only reads the form data.

**Impact:** Free delivery on low-value orders. \
**Severity:** 🟢 Low \
**Endpoints:** `POST /orders`

_Aftermath: Beta testers love the convenience—Mr. Krabs wants a native mobile app that customers can install on their own phones._

---

#### [v103] Order Overwrite for Free Upgrades

> Sandy ships a proper mobile app (still in closed beta) that testers install on their own phones. The basic order checkout gets replaced with a modern cart-based checkout flow to support item modification and other features Sandy wants to add later.

**The Vulnerability**

- Sandy builds the order using Pydantic validation: `Order.model_validate({**user_data, **safe_order_data})`.
- The pattern merges user input first, then overwrites with calculated values (total, items, user_id, etc.) to prevent tampering.
- However, `order_id` isn't in `safe_order_data` (database generates it for new orders), so if present in `user_data`, it survives the merge.
- Checkout using JSON (not form data) allows injecting `order_id`, which causes the database to UPDATE an existing order instead of INSERT a new one.

**Exploit**

1. Create and checkout a cheap cart ($1 item), capturing the returned `cheap_order_id`.
2. Create a new cart and add expensive items ($26+ worth).
3. Checkout the expensive cart using JSON with injected order ID: `{"delivery_address": "...", "order_id": "cheap_order_id"}`.
4. The handler builds an order object with your injected ID, which the database treats as an UPDATE.
5. Your cheap order's items get replaced with expensive items, but you've only paid for the cheap one.

**Impact:** Expensive order overwrites cheap one without recharging. \
**Severity:** 🟠 High \
**Endpoints:** `POST /cart/{id}/checkout`

_Aftermath: Sandy adds middleware to block any user-supplied `order_id` from reaching the handler._

---

#### [v104] Negative Tip Cashouts

> Couriers request tip support. Since Sandy just moved security checks to middleware in v103, she validates the new tip field there as well—negative tips should obviously be blocked.

**The Vulnerability**

- Middleware validates tips using a helper that checks query args first, then JSON body, then form data—returning the first non-empty value found.
- The checkout handler reads tip from either `request.json` or `request.form` (never from query args).
- When an attacker provides `?tip=20` in the URL plus `tip=-50` in the body, middleware validates the positive query value while the handler applies the negative body value.

**Exploit**

1. Append `?tip=20` to the checkout URL to pass middleware validation.
2. Send `{ "tip": -50 }` in the request body.
3. Middleware approves the positive query value; handler applies the negative body value, crediting $50 back to your account.

**Impact:** Free orders or direct payouts via negative tips. \
**Severity:** 🔴 Critical \
**Endpoints:** `POST /cart/{id}/checkout`

_Aftermath: Sandy wraps the user-supplied tip with `abs()` in the handler, forcing it positive regardless of what middleware validated._

---

#### [v105] Unlimited Refund Payouts

> Courier delays are inevitable, so Sandy adds `POST /orders/{order_id}/refund` so the mobile app can auto-refund 20% when drivers are late. While there, she also lets app users request full refunds, although those would need to be manually approved by Sandy herself.

**The Vulnerability**

- The auto-approval check reads `amount` only when the body is JSON; form-encoded or query data fall back to `order_total * 0.2`.
- The handler later consumes `amount` from _any_ container (query, form, JSON) when creating the refund record.

**Exploit**

1. Plankton sends `POST /orders/{order_id}/refund` with `Content-Type: application/x-www-form-urlencoded` and `amount=2000`.
2. The guard sees a non-JSON payload, assumes a 20% refund, and auto-approves it.
3. The handler reads the form value and pays out $2000.

**Impact:** Sandy pays out refunds far exceeding the original purchase. \
**Severity:** 🔴 Critical \
**Endpoints:** `POST /orders/{order_id}/refund`

---

#### [v106] Signup Token Email Swap

> Sandy hand-created every beta account so far, but she's preparing to launch a public web UI alongside the mobile app. She implements two-step email verification (send token, then confirm) to automate onboarding.

**The Vulnerability**

- The user registration handler contains two branches:
  - The first branch is entered if there's NO `token`, and expects to only receive `email` in the body. It checks email uniqueness and sends the verification token to the email address.
  - The second branch expects to receive `token` and `password`, verifying the token and creating the user record if it's valid.
- Token verification checks signature/expiry and ensures the token email hasn’t been used before. It does not check that there's no `body.email` present or that `body.email == token.email`.
- During account creation, handler prioritizes `body.email` if it's available over the `token.email`.
- If the `body.email` matches existing user, the handler overwrites the user's password with the one provided in the request body.

**Exploit**

1. Plankton registers `plankton@chum-bucket.sea` and receives a valid verification token.
2. He replays the request with `body.email = spongebob@krusty-krab.sea`, `password = "hijack"`, and the original token.
3. Handler trusts the token signature, then overwrites SpongeBob’s password with Plankton’s choice.

**Impact:** Full account takeover of existing users. \
**Severity:** 🔴 Critical \
**Endpoints:** `POST /auth/register`

_Aftermath: Sandy patches the handler to compare token and body emails, and to prevent accidental overwrites._

---

#### [v107] Signup Bonus Replay

> To drive adoption before the web launch, Sandy offers $2 signup credit to new users.

**The Vulnerability**

- Sandy refactored the registration flow to use middleware for token validation (centralizing authentication logic, similar to v104).
- Two middleware functions run sequentially: one extracts email from the token into `g.email`, then another extracts email from Basic Auth (also into `g.email`).
- The second middleware overwrites the first, so authenticated requests use Basic Auth email instead of token email.
- The handler applies the signup bonus to `g.email` before checking if the user already exists.
- If you replay registration with your own valid token + Basic Auth credentials, you pass all checks but credit yourself $2 each time without creating a duplicate account.

**Exploit**

1. Register and verify your account to obtain a valid token.
2. Replay the second registration step (with token + password) but include Basic Auth credentials in the request.
3. Each replay credits $2 to your existing account without creating a duplicate user.

**Impact:** Unlimited credit inflation without creating new accounts. \
**Severity:** 🟠 High \
**Endpoints:** `POST /auth/register`

_Aftermath: Sandy patches the handler to be super explicit about the input sources used, and prioritizes Basic Auth -> cookie session migration for the web UI launch._
