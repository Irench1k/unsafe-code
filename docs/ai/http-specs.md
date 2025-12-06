# E2E Spec Conventions (uctest)

Single-source guidance for `.http` files under `spec/`, executed with **uctest**. Focused on regression coverage and inheritance.

---

## Purpose
1. Specify behavior before implementation (TDD).
2. Support multi-framework ports (language-agnostic).
3. Model SaaS evolution through inheritance.
4. Maximize reuse; minimize overrides.

---

## Directory & File Patterns
```
spec/
├── spec.yml              # Inheritance configuration
├── utils.cjs             # All helper functions
├── common.http           # Root imports
├── v201/
│   ├── _imports.http
│   ├── .env              # VERSION=v201
│   └── account/credits/get/
│       ├── happy.http
│       └── authn.http
└── v301/
    ├── _imports.http
    ├── ~happy.http       # Inherited (generated)
    └── cart/checkout/post/
        ├── happy.http    # Override
        └── multi-tenant.http # New test
```

### File Naming & Tags
| Pattern | Purpose | Tags |
|---------|---------|------|
| `happy.http` | Happy path success | `happy` |
| `authn.http` | Auth required | `authn` |
| `authz.http` | Authorization checks | `authz` |
| `validation.http` | Input validation | — |
| `vuln-*.http` | Vulnerability demo | `vulnerable` |
| `~*.http` | Inherited (generated) | from parent |
| `_imports.http` | Import chain | — |

Tags are managed by `ucsync` using `spec.yml` `tag_rules`; never edit tags in inherited files.

---

## Response Wrapper Helpers
```http
?? js $(response).status() == 200
?? js $(response).isOk() == true
?? js $(response).isError() == true
?? js $(response).field("email") == {{user("plankton").email}}
?? js $(response).field("order.status") == pending
?? js $(response).hasFields("email", "balance") == true
?? js $(response).hasOnlyUserData("plankton") == true
?? js $(response).hasMultipleUsers(2) == true
?? js $(response).total() == 12.99
?? js $(response).balance() == 187.01
```

---

## Helper Catalog

### Authentication
```http
Authorization: {{auth.basic("plankton")}}
Authorization: {{auth.basic("plankton", "wrongpassword")}}
Cookie: {{auth.login("plankton")}}
X-API-Key: {{auth.restaurant("krusty_krab")}}
X-Admin-API-Key: {{auth.admin()}}
```

### Users
```http
{{user("plankton").email}}      # plankton@chum-bucket.sea
{{user("plankton").shortId}}    # plankton
{{user("plankton").password}}   # i_love_my_wife
{{user("plankton").id}}         # 3 (v301+)
?? js await user("plankton").canLogin() == true
?? js await user("plankton").balance() == 200
```
Available users: sandy, patrick, plankton, spongebob, mrkrabs, squidward, karen.

### Platform Setup
```http
{{ await platform.seed({ plankton: 200, patrick: 150 }); }}
{{ await platform.seedCredits("plankton", 200); }}  # Idempotent single balance
{{ await platform.reset(); }}
```
Seed **inside** named requests, not at file scope.

### Menu & Orders
```http
{{menu.item(1).id}}                    # By ID
{{menu.item("Krabby Patty").id}}      # By name
{{menu.firstAvailable(1).id}}          # At restaurant 1
{{menu.cheapest().id}}                 # Lowest price
{{menu.total([4, 5])}}
?? js $(response).total() == {{order.total([4, 5], 2)}}
?? js $(response).field("balance") == {{order.balanceAfter(200, [4, 5], 2)}}
```

### Cookies
```http
@sessionCookie = {{extractCookie(response)}}
?? js hasCookie(response) == false
```

### References (`@ref` / `@forceRef`)
```http
# @name setup_cart
POST /cart?restaurant_id=1
Authorization: {{auth.basic("patrick")}}

@cart_id = {{$(response).field("cart_id")}}

### Cached result
# @ref setup_cart
POST /cart/{{cart_id}}/items

### Fresh each time
# @forceRef setup_cart
POST /cart/{{cart_id}}/checkout
```
If A uses `@forceRef B`, then B must `@forceRef` its dependencies.

---

## Inheritance Model (`spec.yml`)
- Child inherits entire directory tree from parent.
- Inherited files get `~` prefix.
- New/override files in child take precedence.
- `exclude` blocks specific files from inheriting (typically vuln tests once fixed or genuine breaking API changes).

Example:
```yaml
v301:
  description: Dual-Auth Refund Approval
  tags: [r03, v301]
  inherits: v206
  exclude:
    - cart/create/post/happy.http
    - orders/refund/post/vuln-fake-header.http
  tag_rules:
    "**/authn.http": [authn]
    "**/happy.http": [happy]
    "**/vuln-*.http": [vulnerable]
```

---

## Test Templates

### Happy Path
```http
# @import ../_imports.http

### Success case
# @name resource_created
POST /resource
Authorization: {{auth.basic("patrick")}}
Content-Type: application/json

{ "field": "value" }

@resource_id = {{$(response).field("id")}}
?? js $(response).status() == 201
?? js $(response).hasFields("id", "field") == true
```

### Authentication Guardrail
```http
# @import ../_imports.http

### Missing auth
POST /resource
Content-Type: application/json

{ "field": "value" }

?? js $(response).isError() == true
```

### Vulnerability Test
```http
# @import ../_imports.http
# =============================================================================
# VULNERABILITY: Description
# ATTACK: Steps
# IMPACT: Attacker gain
# STATUS: VULNERABLE in vXXX
# =============================================================================

### Exploit
# @name exploit
# @forceRef setup
POST /endpoint
...

?? js $(response).isOk() == true
?? js $(response).hasOnlyUserData("victim") == true
```

---

## Import Chain Discipline
```
spec/common.http           <- Loads utils.cjs
  |
spec/v301/_imports.http   <- @import ../common.http
  |
spec/v301/cart/_imports.http  <- @import ../_imports.http
  |
spec/v301/cart/checkout/post/happy.http  <- @import ../_imports.http
```

---

## Version Code Mapping
| Section | Exercise | Version | Description |
|---------|----------|---------|-------------|
| r02 | e01 | v201 | Session Hijack |
| r02 | e02 | v202 | Credit Top-ups |
| r02 | e06 | v206 | Session Overwrite Fixed |
| r03 | e01 | v301 | Dual-Auth Refund |
| r03 | e07 | v307 | Token Swap |

---

## Debugging & Execution

| Error | Likely Cause | Fix |
|-------|--------------|-----|
| `ref "X" not found` | Typo or missing `@name` | Fix spelling / add named request |
| Assertion mismatch | Code regression OR test drift | Check README and intended behavior |
| Stale `~` files | Inheritance out of sync | Run `ucsync` |
| Type error | Syntax issue | Check helper usage and imports |

- `uctest v301/` – run all specs in version.
- `uctest v301/cart/checkout/post/happy.http` – single file.
- `uctest @vulnerable` – tag filter.
- `uctest -k` – keep going after failures.
- `ucsync` after changes to `spec/spec.yml` or inheritance questions.
- `uclogs --since 30m` for backend stack traces.
- Avoid editing `~` files; override or exclude instead.
