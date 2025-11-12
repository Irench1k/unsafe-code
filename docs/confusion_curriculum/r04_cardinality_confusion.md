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

| Lifecycle | Method | Path                       | Auth                | Purpose                 | Vulnerabilities  |
| --------- | ------ | -------------------------- | ------------------- | ----------------------- | ---------------- |
| v101+     | GET    | /account/credits           | Customer            | View balance            | v202             |
| v202+     | POST   | /account/credits           | Admin               | Add credits             | v202             |
| v101+     | GET    | /menu                      | Public              | List available items    |                  |
| v101+     | GET    | /orders                    | Customer/Restaurant | List orders             | v201, v204, v304 |
| v201+     | GET    | /orders/{id}               | Customer/Restaurant | Get single order        | v305             |
| v105+     | POST   | /orders/{id}/refund        | Customer            | Request refund          | v105             |
| v201+     | PATCH  | /orders/{id}/refund/status | Restaurant          | Update refund status    | v301             |
| v103+     | PATCH  | /orders/{id}/status        | Restaurant          | Update order status     | v305             |
| v103+     | POST   | /cart                      | Customer            | Create cart             | v201             |
| v103+     | POST   | /cart/{id}/items           | Customer            | Add item to cart        | v402             |
| v103+     | POST   | /cart/{id}/checkout        | Customer            | Checkout cart           | v103, v104, v302 |
| v401+     | POST   | /cart/{id}/apply-coupon    | Customer            | Attach coupons to cart  | v401, v403       |
| v201+     | GET    | /cart/{id}                 | Customer/Restaurant | Get single cart         |                  |
| v404+     | POST   | /restaurants/{id}/refunds  | Restaurant          | Batch refund initiation | v404             |
| v303+     | PATCH  | /menu/items/{id}           | Restaurant          | Update menu item        | v303, v405       |

#### Schema Evolution

##### Data Model Evolution

| Model              | v401                         | v402        | v403                              | v404                         | v405 |
| ------------------ | ---------------------------- | ----------- | --------------------------------- | ---------------------------- | ---- |
| Coupon             | Single `code` field          | -           | `codes[]`, `+single_use`, `+used` | -                            | -    |
| ApplyCouponRequest | `code` field                 | -           | `codes[]` array                   | -                            | -    |
| CartItem           | `sku` only                   | `+quantity` | -                                 | -                            | -    |
| BatchRefundRequest | -                            | -           | -                                 | ✅ (`order_ids[]`, `reason`) | -    |
| RestaurantBinding  | `bind_to_restaurant()` added | -           | -                                 | -                            | -    |

##### Behavioral Changes

| Version | Component            | Behavioral Change                                                                          |
| ------- | -------------------- | ------------------------------------------------------------------------------------------ |
| v401    | ApplyCouponRequest   | Validation checks `request.form.get('code')`; application reads `request.args.get('code')` |
| v402    | CartItem Reservation | Reservation loop adds items one at a time; always adds at least one even if quantity is 0  |
| v403    | ApplyCouponRequest   | Validation deduplicates and uppercases `codes[]`; application iterates original array      |
| v403    | Coupon Usage         | `used` flag set only once after all iterations complete                                    |
| v404    | BatchRefundRequest   | Authorization uses `SELECT ... LIMIT 1` (any match); handler refunds all IDs in array      |
| v405    | get_restaurant_id()  | First `pop()` validates and stores in context; second `pop()` drives ORM binding           |

#### Data Models

```ts
// Coupon definitions now track single-use metadata.
interface Coupon {
  code: string;
  type: "discount_percent" | "fixed_amount" | "free_item_sku";
  value: decimal | string;
  single_use?: boolean;
  used?: boolean;
}

interface ApplyCouponPayload {
  code?: string; // Legacy single code (form body)
  codes?: string[]; // JSON array added in v403
  source?: "query" | "body";
}

interface CartItemV2 extends CartItem {
  quantity: number; // Introduced in v402; backend still stores ≥1 even if 0 sent
}

interface CartWithCoupons extends Cart {
  items: CartItemV2[];
  coupons: Coupon[];
}

interface BatchRefundRequest {
  restaurant_id: string;
  order_ids: string[];
  reason?: string;
}

interface BatchRefundResult {
  processed_ids: string[];
  skipped_ids: Array<{ order_id: string; reason: string }>;
}
```

#### Request and Response Schemas

```ts
// POST /cart/{id}/apply-coupon (v401)
type ApplyCouponRequest_v401 = {
  form_code?: string; // Checked by validation
  query_code?: string; // Applied to cart regardless of validation source
};

// POST /cart/{id}/apply-coupon (v403)
type ApplyCouponRequest_v403 = {
  codes: string[]; // Validation dedupes uppercase set, application loops original array
};

type ApplyCouponResponse = CartWithCoupons;

// POST /cart/{id}/items (v402)
type AddItemsToCartRequest_v402 = {
  items: Array<{ sku: string; quantity: number }>;
};

// POST /restaurants/{id}/refunds (v404)
type CreateBatchRefundRequest = BatchRefundRequest;

type CreateBatchRefundResponse = BatchRefundResult;

// PATCH /menu/items/{id} (v405)
type PatchMenuItemRequest_v405 = {
  restaurant_id?: string; // First pop validates, second pop drives ORM helper
  price?: decimal;
  available?: boolean;
};
```

### Vulnerabilities to Implement

#### [v401] Free Orders Due to Coupon Stacking

> Sandy implements a frequently requested feature: passing coupons via query params, to make it easier for influencers to embed them in their content.

(adds query coupons for shareable links while the legacy form body stays in place for kiosk compatibility, and validation still only inspects the body)

**The Vulnerability**

- Validation checks `request.form.get('code')` to ensure only one coupon is set per cart (if the cart already has a coupon, the handler returns 200 if it matches the one in the form to ensure idempotency, and 400 otherwise).
- Application logic reads `request.args.get('code')`, with every request invocation adding another coupon to the cart.

**Exploit**

1. Begin checkout with no coupon.
2. Repeatedly send `POST /cart/{id}/apply-coupon?code=BURGER20`.
3. Validation never fires (form is empty) while the query adds another coupon to the cart, driving the total toward zero.

**Impact:** Unlimited stacking of “single use” coupons. \
**Severity:** 🟡 Medium \
**Endpoints:** `POST /cart/{id}/apply-coupon`

---

#### [v402] Quantity Manipulation Exploit

> Influencer promotions are a resounding sucess and krabby patty becomes a viral sensation. However, during the peak of popularity, Krusty Krab had to disable new orders because they run out of ingredients, leading to bad customer experience. Mr. Krabs is so excited that he immediately forgets about the out of stock issue and asks Sandy to implement a `Buy 2 Get 1 Free` promotion immediately.

**The Vulnerability**

- While working on the new promotion type, Sandy redesigns order creation with a new 'reservation' system in mind (she plans to let restaurants set stock limits per item, although this isn't exposed via manager endpoints yet).
- The new system reserves one item at a time, to ensure that the restaurant capacity is not exceeded.
- She updates the frontend to deduplicate items, and send them with a new `quantity` field - to simplify the `Buy 2 Get 1 Free` logic implementation.
- Backend enforces item uniqueness now, and calculates the total cost as `price * quantity`.
- The item assignment has a bug and always adds at least one item to the cart.

**Exploit**

1. POST `/cart/{id}/items` with `{ "items": [{ "sku": "krabby-patty", "quantity": 0 }] }`.
2. Reservation loop adds one item to the cart.
3. Price calculation multiplies by zero, so nothing is charged.

**Impact:** Free items. \
**Severity:** 🔴 Medium \
**Endpoints:** `POST /cart/{id}/items`

---

#### [v403] Single-Use Coupon Reuse

> A marketing startup offers to mail coupon bundles, but insists on enabling multiple coupons per order: "Four smaller discounts feel more generous than one big one." Sandy dreads adding coupon stacking and has been avoiding it, but the business case is undeniable.

**The Vulnerability**

- Three coupon types: `discount_percent`, `fixed_amount` and `free_item_sku`
- Sandy adds `single_use` and `used` flags to prevent cross-request reuse
- Validation deduplicates the `codes[]` array (incl. force uppercase) and stores approved codes in a set
- Application logic iterates the _original_ array with duplicates, checking each against the set
- The code is marked `used = true` only once, after all iterations complete

**Exploit**

1. Add items to cart, send `POST /cart/{id}/apply-coupon`:

```json
{
  "codes": ["HOLIDAY10-E7B2A", "FREE-FRIES-BQ8IX", "HOLIDAY10-E7B2A"]
}
```

2. Validation: deduplicates → `{"HOLIDAY10-E7B2A", "SAVE5-E6V22-BQ8IX"}`, both valid
3. Application: loops original array, applying "SAVE5" three times
4. The total discount is 2x10$ + Free Fries

**Impact:** Multiplication of single-use discounts within one request \
**Severity:** 🟠 Medium \
**Endpoints:** `POST /cart/{id}/apply-coupon`

_Despite the exploit, the campaign succeeds wildly and there is a major boom in sales. However, new customers face unavailable items and missed deliveries. Even beta testers complain about degraded service. Sandy needs better tools for restaurants to handle the chaos._

---

#### [v404] Restaurant Refunds: Any vs All Authorization

> Sandy builds a new endpoint to allow restaurants to initiate refunds pre-emptively, without waiting for customer to report the issue.

**The Vulnerability**

- Authorization decorator ensures the caller manages restaurant `{id}`.
- Handler then checks `SELECT 1 FROM orders WHERE order_id IN (...) AND restaurant_id = ? LIMIT 1`.
- As soon as _one_ order matches, the handler loops through the entire list and calls the customer refund flow for each item.

**Exploit**

1. Include one legitimate order from your restaurant plus many victim orders.
2. Submit the batch; the SQL EXISTS returns true because of the first order.
3. Handler issues refunds for every ID in the list, even those from other restaurants.

**Impact:** Cross-tenant refunding of arbitrary orders. \
**Severity:** 🔴 Critical \
**Endpoints:** `POST /restaurants/{id}/refunds`

---

#### [v405] Cross-Restaurant Menu Item Modification

> While working on the v404 fix, Sandy introduces a standardized helper, that automatically extracts `restaurant_id` from that path or query argument.

**The Vulnerability**

- `get_restaurant_id()` pops (uses `pop()`) the first value from the query list, validates it, and stores it in context.
- When the ORM helper runs later, it calls the same function again to fetch the ID for SQL binding.
- If the attacker provides `?restaurant_id=1&restaurant_id=2`, the first call validates `1` but the second pop returns `2`, which drives the database update.

**Exploit**

1. Manager of restaurant 2 calls `PATCH /menu/items/99?restaurant_id=1&restaurant_id=2`.
2. Authorization validates `1` and okays the request.
3. ORM helper pops `2` and writes the change against restaurant 2’s context, effectively editing someone else’s menu item.

**Impact:** Cross-restaurant menu edits despite dual validation. \
**Severity:** 🔴 Critical \
**Endpoints:** `PATCH /menu/items/{id}`
