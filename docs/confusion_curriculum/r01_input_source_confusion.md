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

### Endpoints:

| Lifecycle | Method | Path                       | Auth                | Purpose                   | Vulnerabilities |
| --------- | ------ | -------------------------- | ------------------- | ------------------------- | --------------- |
| v101+     | GET    | /account/credits           | Customer            | View balance              |                 |
| v101+     | GET    | /menu                      | Public              | List available menu items |                 |
| v101+     | GET    | /orders                    | Customer/Restaurant | List orders               |                 |
| v101-v102 | POST   | /orders                    | Customer            | Create new order          | v101, v102      |
| v103+     | POST   | /cart                      | Customer            | Create cart               |                 |
| v103+     | POST   | /cart/{id}/items           | Customer            | Add item to cart          |                 |
| v103+     | POST   | /cart/{id}/checkout        | Customer            | Checkout cart             | v103, v104      |
| v103+     | PATCH  | /orders/{id}/status        | Restaurant          | Update order status       |                 |
| v105+     | POST   | /orders/{id}/refund        | Customer            | Request refund            |                 |
| v105+     | PATCH  | /orders/{id}/refund/status | Restaurant          | Update refund status      | v105            |
| v106      | POST   | /auth/register             | Public              | Register user             | v106            |

> [!IMPORTANT]
> Don't add complex authorization yet – that's r03. Use database-level ownership checks (e.g., `WHERE user_id = current_user`) to avoid accidental IDORs, but don't build a full RBAC system.

This section uses rudimentary authentication and authorization:

- Beta-users are onboarded manually by Sandy (using direct database inserts)
- Customers are authenticated using Basic Auth (username/password)
- Restaurants are authenticated using API keys (X-API-Key header)

> [!TIP]
> Add a docker compose service for https://github.com/axllent/mailpit to capture verification emails sent during user registration

#### Schema Evolution

Track how schemas change across versions:

| Model               | v101              | v102            | v103       | v104   | v105 | v106 |
| ------------------- | ----------------- | --------------- | ---------- | ------ | ---- | ---- |
| Cart                | -                 | -               | ✅         | -      | -    | -    |
| CheckoutCartRequest | -                 | -               | Base       | `+tip` | -    | -    |
| CreateOrderRequest  | `item \| items[]` | `items[]` only  | -          | -      | -    | -    |
| MenuItem            | ✅                | -               | -          | -      | -    | -    |
| Order               | Base              | `+delivery_fee` | `+cart_id` | `+tip` | -    | -    |
| OrderItem           | ✅                | -               | -          | -      | -    | -    |
| Refund              | -                 | -               | -          | -      | ✅   | -    |
| RegisterUserRequest | -                 | -               | -          | -      | -    | ✅   |

#### Data Models

```ts
/**
 * A single item available on a restaurant's menu.
 */
interface MenuItem {
  id: string;
  name: string;
  price: decimal;
  available: boolean;
}

/**
 * An item that has been added to an order.
 * Note: price is copied at time of purchase.
 */
interface OrderItem {
  item_id: string;
  name: string;
  price: decimal;
}

/**
 * Represents a customer's shopping cart.
 */
interface Cart {
  cart_id: string;
  items: string[]; // Array of item IDs
}

/**
 * Represents a completed Order.
 * This model evolves throughout r01.
 */
interface Order {
  order_id: string;
  total: decimal;
  delivery_address: string;
  created_at: timestamp;
  items: OrderItem[];

  // Added in v102
  delivery_fee?: decimal;

  // Added in v103 (cart-based checkout)
  cart_id?: string;

  // Added in v104
  tip?: decimal;
}

/**
 * Represents a refund request.
 */
interface Refund {
  refund_id: string;
  order_id: string;
  amount: decimal;
  reason?: string;
  status: "pending" | "accepted" | "rejected";
}

/**
 * Represents a registered user.
 */
interface User {
  user_id: string;
  email: string;
  name: string;
  balance: decimal;
}
```

#### Request and Response Schemas

```ts
// GET /account/credits
type GetCreditsResponse = {
  balance: decimal;
};

// GET /menu
type ListMenuResponse = MenuItem[];

// GET /orders
type ListOrdersResponse = Order[];

// POST /orders (v101)
type CreateOrderRequest_v101 = {
  item?: string; // Single item ID (initial MVP)
  items?: string[]; // Array of menu item IDs (new feature)
  delivery_address: string;
};

// POST /orders (v102)
// The 'item' parameter is deprecated and removed
type CreateOrderRequest_v102 = {
  items: string[];
  delivery_address: string;
};

// POST /cart
type CreateCartRequest = {
  items: string[]; // Array of item IDs
};

// POST /cart/{id}/items
type AddItemToCartRequest = {
  items: string[]; // Array of item IDs
};

// POST /cart/{id}/checkout (v103)
type CheckoutCartRequest_v103 = {
  delivery_address: string;
};

// POST /cart/{id}/checkout (v104)
type CheckoutCartRequest_v104 = {
  delivery_address: string;
  tip?: decimal; // Tip is added
};

// PATCH /orders/{order_id}/status
type OrderStatusUpdateRequest = {
  status: "preparing" | "delivering" | "finished" | "cancelled";
};

// POST /orders/{order_id}/refund
type RequestRefundRequest = {
  amount?: decimal; // Defaults to 20% if not provided
  reason?: string;
};

// PATCH /orders/{order_id}/refund/status
type UpdateRefundStatusRequest = {
  status: "accepted" | "rejected";
  reason?: string;
};

// POST /auth/register
type RegisterUserRequest = {
  email: string;
  password?: string; // Optional: not needed for first step
  token?: string; // Optional: provided in verification step
};

// POST /auth/register
type RegisterUserResponse = {
  user_id: string;
  email: string;
  name: string;
  balance: decimal; // New users get $2.00
};
```

### Vulnerabilities to Implement

#### [v101] Price Manipulation via Dual Parameters

**Scenario:** Sandy initially accepted a single `item` parameter. Later, she added support for `items` (array) but forgot to remove the old parameter.

**The Bug:**

- Price calculation reads `item` (single value)
- Order creation reads `items` (array)
- If both present, customer pays for one cheap item but receives expensive items

**Impact:** Customer pays for a $1 side of fries, gets a $20 Krabby Patty meal. \
**Severity:** 🔴 Critical

**Endpoints:** `POST /orders`

---

#### [v102] Delivery Fee Bypass

**Scenario:** Sandy is adding a free delivery feature for orders over $25.00.

**The Bug:**

- Fee calculation reads `items` from query parameters
- Checkout reads `items` from request body
- Attacker sends fake high-value items in query to trigger free delivery, real low-value items in body

**Impact:** Customer with $10 order gets free delivery by lying about cart total in query string. \
**Severity:** 🟡 Medium

**Endpoints:** `POST /orders`

---

#### [v103] Order Overwrite via ID Injection

**Scenario:** When introducing cart-based checkout, Sandy also added support for JSON bodies.

**The Bug:**

- For form data: the checkout handler creates new order with generated ID
- For JSON: the checkout handler merges request JSON **into** template (with `order_id: <new_id>`)
- Attacker includes existing `order_id` in JSON body, causing _upsert_ instead of _insert_

**Impact:** Attacker creates cheap order, then overwrites it with expensive items (without paying for them). \
**Severity:** 🔴 Critical

**Endpoints:** `POST /cart/{id}/checkout`

---

#### [v104] Negative Tip

**Scenario:** Sandy is adding a new feature to allow customers to tip their delivery driver.

**The Bug:**

- Tip validation reads `tip` from request body
- Charge calculation reads `tip` from query parameter
- Attacker sends negative tip in query to offset order price, then only pays the difference instead of full amount
- Attacker can also get more money back then what they paid for the order

**Impact:** Customer offsets order price by a negative tip, gets free orders or just steals money. \
**Severity:** 🔴 Critical

**Endpoints:** `POST /cart/{id}/checkout`

---

#### [v105] Refund Fraud

**Scenario:** Sandy is adding a new feature to allow customers to refund their orders. If the order gets delayed, the client app automatically requests a refund of 20% of the order total, so the backend implements logic to automatically accept refunds of up to 20% of the order total – and to wait for manual resolution for refunds over 20%.

**The Bug:**

- Refund amount validation reads `amount` from JSON body (no value -> default 20% is set)
- When applied, the refund `amount` is accessed from the merged dictionary of form data and JSON body
- Attacker can send negative amount in urlencode form, bypassing the validation and causing the refund to be auto-accepted

**Impact:** Customer paid $2.49, gets $20.00 refund. Steals $17.51. \
**Severity:** 🔴 Critical

**Endpoints:** `POST /orders/{order_id}/refund`

---

#### [v106] Onboarding Fraud

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

**Endpoints:** `POST /auth/register`
