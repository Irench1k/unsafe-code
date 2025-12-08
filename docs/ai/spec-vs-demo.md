# E2E Specs vs Interactive Demos

> Quick reference for the critical differences between internal test specs and student-facing demos.

---

## Purpose Comparison

| Aspect | E2E Specs (`spec/vNNN/`) | Interactive Demos (`http/eNN/`) |
|--------|--------------------------|--------------------------------|
| **Audience** | CI/CD, maintainers | Students learning security |
| **Goal** | Behavioral contracts | Teach vulnerability impact |
| **Completeness** | Cover ALL edge cases | Show KEY business impact |
| **Style** | Dense, technical | Narrative, engaging |

---

## Syntax Differences

### Authentication

**E2E Specs** (use helpers):
```http
Authorization: {{auth.basic("plankton")}}
Cookie: {{auth.login("plankton")}}
X-API-Key: {{auth.restaurant("krusty_krab")}}
```

**Interactive Demos** (plain):
```http
@plankton_creds = plankton:i_love_my_wife
Authorization: Basic {{Buffer.from(plankton_creds).toString("base64")}}
```

---

### Response Assertions

**E2E Specs** (wrapper helpers):
```http
?? js $(response).status() == 200
?? js $(response).isOk() == true
?? js $(response).field("email") == {{user("plankton").email}}
?? js $(response).hasFields("id", "email", "balance")
?? js $(response).hasOnlyUserData("plankton")
```

**Interactive Demos** (plain access):
```http
?? js response.parsedBody.email == plankton@chum-bucket.sea
```

---

### Number of Asserts

**E2E Specs**: Multiple asserts OK (comprehensive coverage)
```http
### Cart checkout creates order
POST {{base}}/cart/checkout
?? js $(response).status() == 200
?? js $(response).hasFields("order_id", "total", "tip")
?? js $(response).field("total") == {{expected_total}}
?? js await user("plankton").balance() == {{before - total}}
```

**Interactive Demos**: ONE assert per test (focus on impact)
```http
### EXPLOIT: Plankton checks out someone else's cart
POST {{base}}/cart/checkout
?? js response.parsedBody.order_id != null
# IMPACT: Plankton just charged Patrick's credit card!
```

---

### State Management

**E2E Specs** (platform helpers):
```http
{{
  await platform.seed({ plankton: 200, patrick: 100 });
  exports.before = await user("plankton").balance();
}}
```

**Interactive Demos** (minimal setup):
```http
# Note: Reset state before running
{{ await seedBalance("v301", "plankton@chum-bucket.sea", 100); }}
```

---

### Imports and DRY

**E2E Specs** (heavy imports):
```http
# @import ../_imports.http
# @import ../../../cart/checkout/post/~happy.http
# @ref order_checkout_plankton
```

**Interactive Demos** (self-contained):
```http
@base = http://localhost:8000/api/v301
# Each request is standalone for readability
```

---

## Annotation Style

### E2E Specs (Technical, precise)
```http
### Customer retrieves own order list with valid session cookie
GET {{base}}/orders
Cookie: {{auth.login("plankton")}}
?? js $(response).isOk() == true
```

### Interactive Demos (Behavioral, narrative)
```http
### SpongeBob checks his recent orders
GET {{base}}/orders
Cookie: session=spongebob_session_token

# SpongeBob sees his Krabby Patty orders from this week
```

---

## When to Use Which

### Use E2E Specs For:
- Regression testing
- CI/CD gates
- Comprehensive coverage
- Authentication boundary tests
- Authorization matrix tests
- Input validation tests

### Use Interactive Demos For:
- Teaching vulnerability impact
- Showing attack chains
- Demonstrating business harm
- Student self-guided learning
- "Aha moment" creation

---

## Common Mistakes

### In E2E Specs
- ❌ Hardcoding credentials instead of using `auth.basic()`
- ❌ Using raw response access instead of `$(response).field()`
- ❌ Not using `@forceRef` for stateful chains
- ❌ Duplicating setup instead of importing from `happy.http`

### In Interactive Demos
- ❌ Multiple asserts (loses focus)
- ❌ Using `utils.cjs` helpers (too technical for students)
- ❌ Technical jargon in annotations
- ❌ Explaining root cause (save for README)
- ❌ Using `@base` in examples 1-2 (students need full URLs first)

---

## File Naming

### E2E Specs
```
spec/v301/
├── cart/checkout/post/
│   ├── happy.http         # Success path
│   ├── authn.http         # Auth required tests
│   ├── authz.http         # Authorization tests
│   ├── validation.http    # Input validation
│   └── vuln-*.http        # Vulnerability demonstrations
```

### Interactive Demos
```
vulnerabilities/.../http/e01/
├── e01_dual_auth_refund.exploit.http   # Shows vuln
└── e01_dual_auth_refund.fixed.http     # Shows fix works
```

---

## Verification Commands

### E2E Specs
```bash
uctest v301/cart/checkout/post/happy.http
uctest @authn v301/
uctest -v v301/  # Verbose for debugging
```

### Interactive Demos
```bash
ucdemo r03/e01  # Run all demos for exercise e01
ucdemo path/to/e01_dual_auth_refund.exploit.http  # Single file
```
