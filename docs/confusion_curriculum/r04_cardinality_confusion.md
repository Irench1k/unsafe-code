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
