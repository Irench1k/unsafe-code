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
| v103+     | PATCH  | /orders/{id}/status | Restaurant          | Update order status       |                 |
| v105+     | POST   | /orders/{id}/refund | Customer            | Request refund            | v105            |
| v106+     | POST   | /auth/register      | Public              | Register user             | v106, v107      |

#### Schema Evolution

##### Data Model Evolution

| Model               | v101              | v102            | v103                      | v104   | v105 | v106                     | v107                       |
| ------------------- | ----------------- | --------------- | ------------------------- | ------ | ---- | ------------------------ | -------------------------- |
| Cart                | -                 | -               | ✅ (new entity)           | -      | -    | -                        | -                          |
| CartItem            | -                 | -               | `sku list`                | -      | -    | -                        | -                          |
| CheckoutCartRequest | -                 | -               | Base (`delivery_address`) | `+tip` | -    | -                        | -                          |
| CreateOrderRequest  | `item \| items[]` | `items[]` only  | (no change)               | -      | -    | -                        | -                          |
| Order               | Base              | `+delivery_fee` | `+cart_id`                | `+tip` | -    | -                        | -                          |
| Refund              | -                 | -               | -                         | -      | ✅   | -                        | -                          |
| RegisterUserRequest | -                 | -               | -                         | -      | -    | `Two-step (email/token)` | `+BasicAuth override path` |

##### Behavioral Changes

| Version | Component           | Behavioral Change                                                          |
| ------- | ------------------- | -------------------------------------------------------------------------- |
| v101    | CreateOrderRequest  | Accepts both `item` and `items[]` parameters                               |
| v102    | Delivery Fee Calc   | Prioritizes query args over body when calculating fees                     |
| v103    | CreateOrderRequest  | Legacy `item` parameter still read by price calculator                     |
| v103    | CheckoutCartRequest | Allows `order_id` injection from request body                              |
| v104    | CheckoutCartRequest | Middleware validates tip from query; handler applies tip from body         |
| v105    | RefundRequest       | Auto-approval reads amount from JSON body; database write uses form amount |
| v106    | RegisterUserRequest | Token verification uses token.email; account creation uses body.email      |
| v107    | RegisterUserRequest | Credit issuance occurs before user existence check; uses Basic Auth email  |

#### Data Models

```ts
/** Public menu entry (unchanged through r01). */
interface MenuItem {
  id: string;
  name: string;
  price: decimal;
  available: boolean;
}

/** Snapshot of a menu item captured inside an order/cart. */
interface OrderItem {
  item_id: string;
  name: string;
  price: decimal;
}

/** Cart line item introduced in v103 when the mobile app shipped. */
interface CartItem {
  sku: string;
}

/** Shopping cart produced by POST /cart (v103+). */
interface Cart {
  cart_id: string;
  user_id: string;
  items: CartItem[];
  subtotal: decimal;
}

/** Core order record; new fields are appended as features land. */
interface Order {
  order_id: string;
  user_id: string;
  items: OrderItem[];
  total: decimal;
  delivery_address?: string;
  // v102: delivery pilot introduces a fee based on cart value.
  delivery_fee?: decimal;
  // v103: cart-based checkout copies the originating cart ID when provided.
  cart_id?: string;
  // v104: couriers can see the gratuity Sandy stores alongside the order.
  tip?: decimal;
  created_at: timestamp;
}

/** Refund requests appear in v105. */
interface Refund {
  refund_id: string;
  order_id: string;
  amount: decimal;
  reason?: string;
  status: "pending" | "auto_approved" | "rejected";
  // v105 auto-approval flag records whether middleware granted 20% refunds.
  auto_approved: boolean;
}

/** Minimal user profile carried through r01 enrolment flows. */
interface User {
  user_id: string;
  email: string;
  password_hash: string;
  balance: decimal;
}

/** Verification token payload shared between email + domain confirmation. */
interface VerificationToken {
  token: string;
  email: string;
  issued_at: timestamp;
  expires_at: timestamp;
}
```

#### Request and Response Schemas

```ts
// GET /account/credits
type GetCreditsResponse = { balance: decimal };

// GET /menu
type ListMenuResponse = MenuItem[];

// GET /orders
type ListOrdersResponse = Order[];

// POST /orders (v101: dual parameter era)
type CreateOrderRequest_v101 = {
  item?: string; // Legacy single-item kiosk payload
  items?: string[]; // Multi-item array added for newer tablets
  delivery_address?: string;
};

// POST /orders (v102: delivery fees depend on query/body divergence)
type CreateOrderRequest_v102 = {
  items: string[]; // Legacy `item` is ignored except for price calc bugs
  delivery_address?: string;
};

// POST /cart (v103)
type CreateCartRequest = {
  items: string[]; // Deduplicated later, but duplicates still accepted now
};

// POST /cart/{id}/items (v103)
type AddItemsToCartRequest = {
  items: string[]; // Legacy clients send repeated keys, server dedupes lazily
};

// POST /cart/{id}/checkout (v103)
type CheckoutCartRequest_v103 = {
  delivery_address?: string;
  order_id?: string; // Should be ignored but triggers overwrite confusion
};

// POST /cart/{id}/checkout (v104)
type CheckoutCartRequest_v104 = CheckoutCartRequest_v103 & {
  tip?: decimal; // Middleware reads query first, handler trusts body
};

// PATCH /orders/{id}/status
type OrderStatusUpdateRequest = {
  status: "pending" | "preparing" | "delivering" | "finished" | "cancelled";
};

// POST /orders/{id}/refund (v105)
type RequestRefundRequest_v105 = {
  amount?: decimal; // Auto-approval path defaults to 20% of order total
  reason?: string;
  source?: "auto" | "customer";
};

// POST /auth/register (v106 two-step enrollment)
type RegisterUserRequest_v106 =
  | { email: string; token?: undefined; password?: undefined }
  | { token: string; password: string; email?: string };

// POST /auth/register (v107 Basic Auth override keeps running during beta)
type RegisterUserRequest_v107 = RegisterUserRequest_v106 & {
  basic_auth_email?: string; // Copied from Authorization header when present
};

// POST /auth/register response
type RegisterUserResponse = {
  user_id: string;
  email: string;
  bonus_credit: decimal; // $2 signup promo rolls out in v107
};
```

### Vulnerabilities to Implement

#### [v101] Premium Meal for Side Dish Price

> The initial in-restaurant tablet pilot (single-item promo combos only) went great, so Mr. Krabs now wants the full menu. Sandy updates the kiosk app (still Basic Auth, still physically inside Krusty Krab) so a single `POST /orders` can hold multiple items.

**The Vulnerability**

- Order endpoint accepts a new `items[]` parameter now, but still accepts the legacy `item` parameter for backwards compatibility until all tablets are upgraded to the new version.
- Price calculation still trusts the legacy `item` field if available
- Order creation preferrably iterates over the new `items[]` array to insert rows in the database.
- When both parameters appear, the `item` drives price while `items[]` drives fulfillment.

**Exploit**

1. Submit `item=coleslaw` ( $1 ).
2. Also send `items[]=["krabby-patty-meal"]` (or `items=krabby-patty-meal&items=something-else`) in the form body.
3. Checkout charges $1 but kitchen receives the premium meal line items.

**Impact:** Customer pays for a $1 side, receives a $20 meal. \
**Severity:** 🟠 High \
**Endpoints:** `POST /orders`

_Aftermath: With positive kiosk feedback, Mr. Krabs signs off on the delivery service trial next._

---

#### [v102] Delivery Fee Bypass

> Riding the pilot’s success, Sandy lends a few tablets to VIP customers (Plankton included) so they can place orders from home. She updates the API with a `delivery_address` and a delivery fee calculation algorithm (flat $4.99 fee for the orders under $25).

**The Vulnerability**

- `calculate_delivery_fee()` totals `request.values`, so query parameters override form data.
- The order creation only reads the request data from the body, ignoring the query string.

**Exploit**

1. Populate a cart with $10 worth of items.
2. Hit checkout with `?items=deluxe-mega&items=krabby-combo` while the body contains only the cheap item IDs.
3. Middleware thinks the order crosses the free-delivery threshold, while the handler still charges the $10 body payload.

**Impact:** Free delivery on low-value orders. \
**Severity:** 🟢 Low \
**Endpoints:** `POST /orders`

_Aftermath: The pilot participants order twice as much as previously, so Mr. Krabs asks for a proper mobile app ASAP._

---

#### [v103] Order Overwrite for Free Upgrades

> Sandy ships a proper mobile app (still in closed beta) that testers install on their own phones. The basic order checkout gets replaced with a modern cart-based checkout flow to support item modification and other features Sandy wants to add later.

**The Vulnerability**

- The new cart-based checkout builds a new order record based on the user request data.
- It's careful to avoid merging untrusted user data into the order record, and explicitly takes the opposite "safe" approach (overwriting untrusted user input with calculated values).
- The `order_id` is not passed in though, as it gets generated by the database.
- If the attacker passes an explicit `order_id`, it's not overwritten – which can lead to rewriting an existing record.

**Exploit**

1. Create a $1 cart, make an order and record it's ID as `cheap_order_id`
2. Populate another cart with $20 worth of items, record it's ID as `expensive_cart_id`.
3. POST to `/cart/{expensive_cart_id}/checkout` with body `{ "destination_address": "123 Main St, Bikini Bottom", "order_id": "<cheap_order_id>" }`.
4. The handler overwrites existing cheap order with the expensive cart data, without charging the customer.
5. Restaurant receives the $20 order, and delivers it, despite customer only paying $1.

**Impact:** Expensive order overwrites cheap one without recharging. \
**Severity:** 🟠 High \
**Endpoints:** `POST /cart/{id}/checkout`

_Aftermath: Sandy blames poor coding practices on the crunch time, and promises to clean it up. She fixes the vulnerability by checking the presence of `order_id` in the request body via middleware._

---

#### [v104] Negative Tip Cashouts

> Couriers ask Sandy to add a tip field to the checkout flow.

**The Vulnerability**

- Sandy has implemented the tip validation via middleware. It blocks requests with negative tips.
- The middleware checks both query and body, prioritizing the query if present.
- If both are present, the body value isn't validated.
- An attacker supplies `tip=20` in the query string plus a negative tip in the body; validation sees the positive value, but charging logic subtracts the negative amount from the order total.

**Exploit**

1. Send body `{ "tip": -50 }` to satisfy validation.
2. Append `?tip=20` to the same request.
3. Middleware blesses the request, but the final charge applies `-5`, crediting money back to the attacker.

**Impact:** Free orders or direct payouts via negative tips. \
**Severity:** 🔴 Critical \
**Endpoints:** `POST /cart/{id}/checkout`

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

> Until now, Sandy hand-created accounts for every beta user. The platform is still in the beta phase, as there's only one restaurant (Krusty Krab), but Sandy feels she's ready to open up customer registration to the public.

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

> To juice adoption before the big web launch, Sandy pays $2 in promo credit to every verified signup.

**The Vulnerability**

- Credit issuance happens after token verification but before checking if the user record already exists.
- Sandy has implemented v106 mitigations by moving part of the validation logic to the middleware.
- The code is written with the assumption that the registration handler would only be used by new users, so it does not expect to receive a request authenticated with Basic Auth credentials.
- If the request contains Basic Auth credentials, the user creation uses the email address from the Authorization header, instead of `token.email`.
- Due to the user overwrite protection Sandy implemented addressing v106, the handler aborts user creation, but only _after_ topping up the existing user's credit balance with a $2 sign-up bonus.

**Exploit**

1. Plankton verifies his own account once to obtain a token.
2. He adds the valid Basic Auth credentials to the email validation request and keeps replaying it.
3. Each replay adds $2 to his credit balance even though no new user is created.

**Impact:** Unlimited credit inflation without creating new accounts. \
**Severity:** 🟠 High \
**Endpoints:** `POST /auth/register`

_Aftermath: Sandy patches the handler to be super explicit about the input sources used, and prioritizes Basic Auth -> cookie session migration for the web UI launch._
