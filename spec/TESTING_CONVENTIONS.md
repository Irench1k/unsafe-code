# E2E Testing Conventions

Guidelines for consistent, maintainable httpyac e2e specs.

## Request Dependencies: @ref vs @forceRef

### The Rule

Use `@ref` when multiple tests can share the same setup state.
Use `@forceRef` when you need fresh state for each test.

```http
# Good: Multiple tests share the same cart
### Patrick adds item
# @name patricks_cart_with_item
# @forceRef patricks_cart
POST /cart/{{cart_id}}/items
...

### Plankton cannot checkout Patrick's cart - Test 1
# @ref patricks_cart_with_item    # ← Reuses existing state
POST /cart/{{patricks_cart_id}}/checkout
Authorization: {{auth.basic("plankton")}}
...

### Plankton cannot checkout Patrick's cart - Test 2
# @ref patricks_cart_with_item    # ← Reuses existing state
POST /cart/{{patricks_cart_id}}/checkout
Cookie: {{auth.login("plankton")}}
...
```

### The Chain Rule

**Setup steps referenced by `@forceRef` leaves MUST keep `@forceRef` for their own dependencies.**

This ensures `-a` mode (run all) works correctly by recreating fresh state chains.

```http
# Setup chain - each step uses @forceRef for dependencies
### Create cart
# @name cart
POST /cart?restaurant_id=1

### Add item (needs @forceRef to cart)
# @name cart_with_item
# @forceRef cart                  # ← MUST be @forceRef
POST /cart/{{cart_id}}/items

### Checkout (needs @forceRef to add_item)
# @name checkout
# @forceRef cart_with_item        # ← MUST be @forceRef
POST /cart/{{cart_id}}/checkout

# Leaf tests can use @ref to share state
### Customer can cancel order
# @forceRef checkout              # ← First leaf: @forceRef for fresh order
PATCH /orders/{{order_id}}/status
...

### Cannot cancel already delivered
# @ref checkout                   # ← Subsequent: @ref shares state
PATCH /orders/{{order_id}}/status
...
```

### Running Modes

```bash
httpyac v301 -a            # Runs ALL requests in file order, then @forceRef reruns
httpyac v301 --tag ci      # Runs only tagged leaves with their dependencies
```

## Authentication Pattern Coverage

For guardrail tests, cover all auth methods that the endpoint supports:

```http
### Action fails - Basic Auth + JSON
# @ref setup
POST /endpoint
Authorization: {{auth.basic("attacker")}}
Content-Type: application/json
{ ... }

### Action fails - Basic Auth + Form
# @ref setup
POST /endpoint
Authorization: {{auth.basic("attacker")}}
Content-Type: application/x-www-form-urlencoded
key=value

### Action fails - Cookie Auth + JSON
# @ref setup
POST /endpoint
Cookie: {{auth.login("attacker")}}
Content-Type: application/json
{ ... }

### Action fails - Cookie Auth + Form
# @ref setup
POST /endpoint
Cookie: {{auth.login("attacker")}}
Content-Type: application/x-www-form-urlencoded
key=value
```

## State-Based Test Organization

Organize order/cart status tests by state groups:

```http
# -----------------------------------------------------------------------------
# Tests on PENDING orders
# -----------------------------------------------------------------------------

### Customer can cancel pending order
...

### Restaurant can deliver pending order
...

# -----------------------------------------------------------------------------
# Tests on DELIVERED orders
# -----------------------------------------------------------------------------

### Cannot cancel already delivered order
...

### Cannot re-deliver already delivered order
...

# -----------------------------------------------------------------------------
# Tests on CANCELLED orders
# -----------------------------------------------------------------------------

### Cannot deliver cancelled order
...

### Cannot re-cancel cancelled order
...
```

## Seed Placement

Place seeds in the first named request, not in global scope:

```http
# Good - seed runs once when cart is created
### Patrick creates a cart
{{
  await platform.seed({
    patrick: 200,
    plankton: 200
  });
}}
# @name patricks_cart
POST /cart?restaurant_id=1
Authorization: {{auth.basic("patrick")}}

# Bad - seed runs before EVERY request
{{
  await platform.seed({ patrick: 200 });  # This runs too often!
}}

### Test 1
...

### Test 2
...
```

## Parameter Pollution Testing

Test that path parameters cannot be overridden via query or body:

```http
# Path: /cart/{cart_id}/checkout
# Attack: Try to inject different cart_id

### Injection via query param
# @ref setup
POST /cart/{{victims_cart}}/checkout?cart_id={{attackers_cart}}
Authorization: {{auth.basic("attacker")}}
...
?? js $(response).isError() == true

### Injection via body param
# @ref setup
POST /cart/{{victims_cart}}/checkout
Authorization: {{auth.basic("attacker")}}
Content-Type: application/json
{ "cart_id": "{{attackers_cart}}", ... }
?? js $(response).isError() == true

### Injection via query + body
# @ref setup
POST /cart/{{victims_cart}}/checkout?cart_id={{attackers_cart}}
Authorization: {{auth.basic("attacker")}}
Content-Type: application/json
{ "cart_id": "{{attackers_cart}}", ... }
?? js $(response).isError() == true
```

## File Naming

```
{endpoint-group}-{action}-{type}.http

endpoint-group: cart, orders, account, auth, menu, restaurants
action: create, checkout, items, status, refund, list, info, etc.
type: happy, guardrails, params, ownership, v{version}
```

Examples:
- `cart-checkout-happy.http` - Happy path tests for checkout
- `cart-checkout-ownership.http` - Ownership enforcement tests
- `cart-checkout-params.http` - Parameter injection tests
- `orders-status-guardrails.http` - Status change guardrails
- `orders-refund-status-v302.http` - Version-specific refund tests

## Tags

```http
# @tag ci, r03, vulnerable

ci        - Run in CI (auto-added to leaf nodes by spec-sync)
r03       - Release/vulnerability category
vulnerable - Endpoint under test has known vulnerability
```

## Assertion Helpers

```http
# Status checks
?? js $(response).status() == 201
?? js $(response).isOk() == true
?? js $(response).isError() == true

# Field checks
?? js $(response).field("status") == delivered
?? js $(response).hasFields("order_id", "total", "items") == true

# User data checks
?? js $(response).hasOnlyUserData("plankton") == true

# Order calculations (from utils.cjs)
?? js $(response).total() == {{order.total([4, 5], 2)}}
?? js $(response).field("balance") == {{order.balanceAfter(200, [4, 5], 2)}}
```
