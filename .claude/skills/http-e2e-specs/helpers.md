# utils.cjs Helper Reference

Reference for helper functions available in E2E specs via `utils.cjs`.

## Authentication

### auth.basic(username, password?)

Returns Basic Auth header value. Version-aware username format.

```http
Authorization: {{auth.basic("plankton")}}
Authorization: {{auth.basic("plankton", "wrongpassword")}}
```

### auth.login(username)

Performs actual login and returns session cookie.

```http
Cookie: {{auth.login("plankton")}}
```

### auth.restaurant(restaurant_key)

Returns restaurant API key.

```http
X-API-Key: {{auth.restaurant("krusty_krab")}}
```

## User Data

### user(name)

Access user properties:

```http
{{user("plankton").email}}          # plankton@chum-bucket.sea
{{user("plankton").shortId}}        # plankton
{{user("plankton").password}}       # i_love_my_wife
{{user("plankton").id}}             # 3 (in v301+)
```

### Async User Methods

```http
?? js await user("plankton").canLogin() == true
?? js await user("plankton").canLogin("wrongpw") == false
?? js await user("plankton").balance() == 200
```

## Dynamic User Verification

For dynamically created users (registration tests):

```http
?? js await verify.canLogin(regEmail, "password123") == true
?? js await verify.canAccessAccount(regEmail, "password123") == true
```

## Response Wrapper: $(response)

### Status Checks

```http
?? js $(response).status() == 200
?? js $(response).isOk() == true           # 200-299
?? js $(response).isError() == true        # 400+
```

### Field Access

```http
?? js $(response).field("email") == {{user("plankton").email}}
?? js $(response).field("order.status") == pending   # Nested access
```

### Field Validation

```http
?? js $(response).hasFields("email", "balance") == true
?? js $(response).hasOnlyUserData("plankton") == true   # Security check
```

### Financial Values

```http
?? js $(response).total() == 12.99
?? js $(response).balance() == 187.01
```

## Platform Setup

### platform.seed(balances)

Full database reset + seed with specified balances. **Slow - use sparingly.**

```http
{{
  await platform.seed({ plankton: 200, patrick: 150 });
}}
```

### platform.seedCredits(user, amount)

Update balance only. **Fast - no DB reset.**

```http
{{
  await platform.seedCredits("plankton", 200);
  await platform.seedCredits("spongebob", 150);
}}
```

### platform.reset()

Full database reset without seeding specific balances.

```http
{{
  await platform.reset();
}}
```

## Menu Helpers

```http
{{menu.item(1, "Krabby Patty").id}}           # Get item by ID and name
{{menu.firstAvailable(restaurantId).id}}      # First available menu item
{{menu.filter(restaurantId, {active: true})}} # Filter menu items
```

## Order Helpers

```http
{{order.total(orderId)}}
{{order.balanceAfter(orderId, userId)}}
```

## Cookie Helpers

```http
# Extract cookie from response
@sessionCookie = {{extractCookie(response)}}

# Check if response sets a cookie
?? js hasCookie(response) == false
```

## Test Email Generation

```http
{{
  exports.regEmail = testEmail("reg");  # reg+1699012345@test.example
}}
```

## Best Practices

### Seeding Location

Seed **inside** the first named request, NOT at file scope:

```http
### Setup (CORRECT)
# @name setup
{{
  await platform.seed({ plankton: 200 });
}}
POST /first-step
...

### WRONG - at file scope
{{
  await platform.seed({ plankton: 200 });  # Runs once at load, breaks chains!
}}
```

### Financial Calculations

Always use `parseFloat()` for math with API values:

```http
{{
  exports.before = parseFloat(await user("plankton").balance());
}}
POST /refund
?? js parseFloat($(response).balance()) == {{before + 10}}
```
