# Interactive Demo Syntax Reference

Plain httpyac syntax for student-facing demos. NO utils.cjs helpers available.

## Request Structure

```http
### Request title (narrative style)
HTTP_METHOD {{host}}/endpoint
Header-Name: header-value

{ "body": "here" }

?? status == 200
?? js response.parsedBody.field == expected
```

## Variables

### File Variables

```http
@host = http://localhost:8000/api/v301
@plankton_email = plankton@chum-bucket.sea
@plankton_password = i_love_my_wife
```

### Computed Variables

```http
@plankton_auth = Basic {{btoa(plankton_email + ":" + plankton_password)}}
```

### Response Capture (via @name)

```http
### Create cart
# @name cart
POST {{host}}/cart?restaurant_id=1
Authorization: {{plankton_auth}}

### Use cart ID from previous response
POST {{host}}/cart/{{cart.cart_id}}/items
Authorization: {{plankton_auth}}
```

**Access pattern**: `{{named_request.field}}`

## Authentication (Manual)

### Basic Auth

```http
# Option 1: Pre-computed variable
@plankton_auth = Basic {{btoa("plankton@chum-bucket.sea:i_love_my_wife")}}
Authorization: {{plankton_auth}}

# Option 2: Inline
Authorization: Basic {{btoa("plankton@chum-bucket.sea:i_love_my_wife")}}
```

### Cookie Auth

```http
### Login to get cookie
# @name login
POST {{host}}/auth/login
Content-Type: application/json

{
  "email": "plankton@chum-bucket.sea",
  "password": "i_love_my_wife"
}

### Use cookie from login
GET {{host}}/account/info
Cookie: {{login.headers["set-cookie"]}}
```

### API Key Auth

```http
X-API-Key: {{krabs_api_key}}
```

## Assertions

### Status Check

```http
?? status == 200
?? status == 401
?? status == 403
```

### Response Body (JavaScript)

```http
?? js response.parsedBody.email == plankton@chum-bucket.sea
?? js response.parsedBody.orders.length > 0
?? js response.parsedBody.status == approved
```

### Numeric Comparisons

```http
?? js parseFloat(response.parsedBody.balance) > 100
?? js parseFloat(response.parsedBody.balance) < {{parseFloat(initial.balance)}}
```

### CRITICAL: Operator Required

Without `== != < > <= >=`, becomes request body (500 error):

```http
# WRONG
?? js response.parsedBody.isValid

# CORRECT
?? js response.parsedBody.isValid == true
```

### CRITICAL: No Quotes on RHS

```http
# CORRECT
?? js response.parsedBody.status == approved

# WRONG
?? js response.parsedBody.status == "approved"
```

## Named Requests

```http
### Store response for later use
# @name cart
POST {{host}}/cart?restaurant_id=1

### Reference stored values
POST {{host}}/cart/{{cart.cart_id}}/items

### Reference in assertions
?? js parseFloat(response.parsedBody.balance) > {{parseFloat(initial_balance.balance)}}
```

## JavaScript Blocks

```http
{{
  // Run before request
  console.info("Starting exploit...");
  exports.timestamp = Date.now();
}}
POST {{host}}/endpoint

{{
  // Run after request (for logging)
  console.info("Balance:", response.parsedBody.balance);
}}
```

## Cookie Extraction

```http
{{
  exports.pickCookie = (resp, name = "session_id") => {
    const raw = resp?.headers?.["set-cookie"];
    const cookieHeader = Array.isArray(raw)
      ? raw.find(h => h.startsWith(`${name}=`))
      : raw;
    if (!cookieHeader) return "";
    return cookieHeader.split(";")[0];
  };
}}

### Login
# @name login_response
POST {{host}}/auth/login
...

### Use extracted cookie
GET {{host}}/account/info
Cookie: {{pickCookie(login_response)}}
```

## Content Types

### JSON

```http
POST {{host}}/endpoint
Content-Type: application/json

{
  "field": "value"
}
```

### Form URL Encoded

```http
POST {{host}}/endpoint
Content-Type: application/x-www-form-urlencoded

field=value&other=data
```

## Common setup.http Pattern

```http
# common/setup.http
@base_host = http://localhost:8000/api

# Character credentials
@spongebob_auth = Basic {{btoa("spongebob@krusty-krab.sea:bikinibottom")}}
@squidward_auth = Basic {{btoa("squidward@krusty-krab.sea:clarinet123")}}
@plankton_auth = Basic {{btoa("plankton@chum-bucket.sea:i_love_my_wife")}}

# Restaurant API keys
@krabs_api_key = key-krusty-krub-z1hu0u8o94
@chum_bucket_api_key = key-chum-bucket-xyz123
```

## Imports (Only common.http)

```http
# ALLOWED
# @import ../common/setup.http

# NOT ALLOWED - no cross-file references
# @import ../e01/exploit.http
# @ref named_from_other_file
```
