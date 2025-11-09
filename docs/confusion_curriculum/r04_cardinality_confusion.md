## r04: Cardinality Confusion

_Feature focus:_ list parameters, bulk operations, array handling \
_Student skill:_ comparing singular vs plural assumptions across validation, authorization, and business logic

### What It Is

Cardinality Confusion is any bug where different parts of the system disagree about **how many**:

- values a field can contain (one vs many)
- resources a request may target (one vs many)
- times a side-effect should occur (once vs many / idempotent vs non-idempotent)

...and those disagreements lead to exploitable behavior.

### Framework Features Introduced

- List parameter parsing
- `.get()` vs `.getlist()` methods
- Array destructuring and first-element extraction
- Quantity fields and multipliers

### Why Confusion Happens

- Framework's `.get()` silently returns first element of array
- Validation checks "any valid" while business logic processes "all provided"
- Singular parameter names used for plural data
- Authorization optimized for "at least one" instead of "all"
- Quantity multipliers applied without bounds checking

### The Story

The platform is thriving! Customers want discounts and bulk ordering features. Restaurants want to manage promotions and process multiple orders efficiently. Sandy adds coupon codes, item quantities, and batch operations.

This section focuses on how **list-handling mismatches** create vulnerabilities even when all components read from the same source.

### Endpoints

| Lifecycle | Method | Path                      | Auth     | Purpose              | Vulnerabilities |
| --------- | ------ | ------------------------- | -------- | -------------------- | --------------- |
| v399+     | POST   | /account/credits          | Admin    | Top-up credits       |                 |
| v399+     | POST   | /auth/login               | Public   | Create session       |                 |
| v399+     | POST   | /auth/logout              | Customer | Destroy session      |                 |
| v399+     | POST   | /auth/register            | Public   | Register user        |                 |
| v399+     | POST   | /cart                     | Customer | Create cart          |                 |
| v399+     | GET    | /cart/{id}                | Customer | Get single cart      |                 |
| v399+     | POST   | /cart/{id}/checkout       | Customer | Checkout cart        |                 |
| v399+     | POST   | /cart/{id}/items          | Customer | Add item to cart     | v402            |
| v399+     | GET    | /menu                     | Public   | List menu items      |                 |
| v399+     | PATCH  | /menu/items/{id}          | Manager  | Update menu item     | v405            |
| v399+     | GET    | /orders                   | Customer | List orders          |                 |
| v399+     | GET    | /orders/{id}              | Customer | Get single order     |                 |
| v399+     | POST   | /orders/{id}/refund       | Customer | Request refund       |                 |
| v399+     | PATCH  | /orders/{id}/status       | Manager  | Update order status  |                 |
| v399+     | GET    | /restaurants              | Public   | List restaurants     |                 |
| v399+     | GET    | /restaurants/{id}         | Public   | Get restaurant info  |                 |
| v399+     | PATCH  | /restaurants/{id}         | Manager  | Update info          |                 |
| v401+     | POST   | /coupons                  | Manager  | Create coupon        |                 |
| v401+     | POST   | /cart/{id}/apply-coupon   | Customer | Apply coupon to cart | v401, v403      |
| v404+     | POST   | /restaurants/{id}/refunds | Manager  | Refund multiple      | v404            |

> [!IMPORTANT]
> Cardinality bugs often appear in bulk operations and quantity fields. Test with: single values, arrays, empty arrays, negative numbers, and zero.

> [!TIP]
> Framework documentation often shows `.get()` usage but doesn't warn it silently extracts first element from arrays. Check if your framework has `.get()` vs `.getlist()` (Flask/Django), `req.query` vs `req.query.getAll()` (Deno), or similar variants.

#### Schema Evolution

Track how schemas change across versions:

| Model     | v399 | v401         | v402        | v403                | v404 | v405 |
| --------- | ---- | ------------ | ----------- | ------------------- | ---- | ---- |
| Cart      | Base | `+coupons[]` | -           | -                   | -    | -    |
| CartItem  | -    | -            | ✅          | -                   | -    | -    |
| Coupon    | -    | ✅           | -           | `+single_use,+used` | -    | -    |
| OrderItem | Base | -            | `+quantity` | -                   | -    | -    |

#### Data Models

```ts
/**
 * Represents a discount coupon created by restaurants.
 * Introduced in v401 for promotional campaigns.
 */
interface Coupon {
  code: string; // Unique code (e.g., "BURGER20")
  discount_percent: decimal; // Percentage off (0-100)
  restaurant_id: string;
  created_at: timestamp;

  // Added in v403 (gift code campaign)
  single_use?: boolean; // Can only be used once across all customers
  used?: boolean; // Marked true after first use
}

/**
 * Represents a single item in a shopping cart.
 * Introduced in v402 to support quantities.
 */
interface CartItem {
  item_id: string; // Reference to MenuItem

  // Added in v402
  quantity: number; // Number of this item (default: 1)
}

/**
 * Cart from r01-r03, now supports coupons and quantities.
 */
interface Cart {
  cart_id: string;
  restaurant_id: string;
  items: CartItem[]; // Changed from string[] in v402

  // Added in v401
  coupon_codes?: string[]; // Applied coupon codes
}

/**
 * OrderItem from r01, now includes quantity.
 */
interface OrderItem {
  item_id: string;
  name: string;
  price: decimal;

  // Added in v402
  quantity: number; // How many of this item
}

/**
 * Order from r01-r03, unchanged in r04.
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
  restaurant_id: string;
}
```

#### Request and Response Schemas

```ts
// POST /coupons (v401)
type CreateCouponRequest = {
  code: string;
  discount_percent: decimal;
};

type CreateCouponResponse = Coupon;

// POST /cart/{id}/apply-coupon (v401)
// Reads coupon code from query OR form OR body (vulnerability!)
type ApplyCouponRequest = {
  code?: string; // Single code (v401)
  codes?: string[]; // Multiple codes (v403)
};

type ApplyCouponResponse = {
  cart_id: string;
  items: CartItem[];
  total: decimal;
  coupon_codes: string[]; // All applied coupons
  discount_total: decimal; // Total discount amount
};

// POST /cart/{id}/items (v402)
// Updated to support quantity
type AddItemToCartRequest = {
  items: string[]; // Array of item IDs (from r01)
  quantity?: number; // How many of each item (v402)
};

type AddItemToCartResponse = Cart;

// POST /restaurants/{id}/refunds (v404)
type RestaurantRefund = {
  order_id: string;
  amount: decimal;
  reason?: string;
};

type RestaurantRefundsRequest = RestaurantRefund[];

type RestaurantRefundsResponse = {
  refunded: string[];
  failed?: string[];
};

// PATCH /menu/items/{id} (v405)
// Query parameter: ?restaurant_id=... (can be repeated)
type UpdateMenuItemRequest = {
  name?: string;
  price?: decimal;
  available?: boolean;
};

type UpdateMenuItemResponse = MenuItem;
```

### Vulnerabilities to Implement

#### [v401] Free Orders Due to Coupon Stacking

**Scenario:** Sandy adds coupons for promotions. Initially, only one coupon per cart is allowed, enforced in validation.

**The Bug:**

- Validation checks for existing coupons using `request.form.get('code')` (expects single string, fails if none).
- Application logic uses `request.args.get('code')` (query param), applies discount, and overwrites DB coupon.
- No recalculation of total at apply; decrements persist across calls.

**Impact:** Plankton applies multiple coupons sequentially via query params (e.g., `?code=BURGER20`), reducing total to zero without validation triggering. Gets free orders. \
**Severity:** 🟡 Medium

**Endpoints:** `POST /cart/{id}/apply-coupon`

---

#### [v402] Quantity Manipulation Exploit

**Scenario:** Sandy cleans up UI by adding a quantity field for repeated items ("Krabby Patties, x3"), and she updates the API to support it. While working on this feature, Sandy thinks of what would happen if a user adds a large multiplier (x1000), exhausting the inventory? She envisions a new feature to add in the future – a stock management system to let restaurants define maximum quantities for each item. Although this does not exist yet, Sandy makes the multiple item addition reservation aware to be future-proof.

**The Bug:**

- Handler adds repeated items one at a time, by reserving the inventory for each item until the last one is added
- The quantity field is only validated to be non-negative
- The price calculation multiplies the price by the quantity
- Zero quantity cause a single item to be added to the cart without charging the customer

**Impact:** Attacker can order items for free, stealing from the restaurant. \
**Severity:** 🔴 Medium

**Endpoints:** `POST /cart/{id}/items`

---

#### [v403] Single-Use Coupon Reuse

**Scenario:** Sandy runs a marketing campaign: physical envelopes with single-use gift codes mailed to Bikini Bottom citizens. Multiple codes CAN be stacked now (they're gifts), but each code should only work once across all customers.

**The Bug:**

- Validation iterates through `codes[]` array, filters invalid ones, marks single-use codes for deletion
- Application iterates through raw `codes[]` array from request, but only applies codes that are in `request.allowed_codes`
- Duplicate codes in the request array aren't deduplicated and same code can be applied multiple times in single request

**Impact:** Attacker can apply the same single-use coupon multiple times within one request, getting free orders. \
**Severity:** 🟡 Low

**Endpoints:** `POST /cart/{id}/apply-coupon`

---

#### [v404] Restaurant Refunds: Any vs All Authorization

**Scenario:** Previously, only customer could request a refund for an order (`POST /orders/{order_id}/refund`). In order to keep customers happy, Sandy introduces a new functionality that allows restaurants to initiate refunds on their own when something goes wrong.

**The Bug:**

- The `/restaurants/{id}/` endpoints are protected by the common restaurant authorization decorator, so that only restaurant managers can access them
- The `POST /restaurants/{id}/refunds` handler performs an additional check:
  ```sql
  SELECT 1 FROM orders
  WHERE order_id IN (?, ?, ?)
    AND restaurant_id = ?
  LIMIT 1
  ```
- Handler dispatches individual refunds via existing customer refund functionality (`POST /orders/{order_id}/refund`)
- Effectively, authorization passes if ANY order in the list belongs to the restaurant, but ALL orders are processed

**Impact:** Attacker mixes one legitimate order with many victim orders, refunding competitors' transactions. \
**Severity:** 🔴 Critical

**Endpoints:** `POST /restaurants/{id}/refunds`

---

#### [v405] Cross-Restaurant Menu Item Modification

**Scenario:** Sandy unifies restaurant-level authorization for `/restaurants/{id}/` endpoints, and now wants to have similarly robust and convenient authorization for endpoints that don't have `restaurant_id` in the path.

**The Bug:**

- The `PATCH /menu/items/{id}` endpoint is updated to accept `?restaurant_id=...` query parameter
- A helper function is added that relies on this standardized query parameter to extract the restaurant_id for validation and database query
- The helper uses `.pop()` to remove the first item from the query args, validating it and saving it in the request context for convenience
- The database query uses the same helper again, – now popping the second value (or fallback to context if empty)
- If two `restaurant_id` query arguments are provided, the handler will validate first one but provide the second one to the database query

**Impact:** Attacker can modify menu items for other restaurants. \
**Severity:** 🔴 Critical

**Endpoints:** `PATCH /menu/items/{id}`
