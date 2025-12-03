---
name: http-interactive-demos
description: Creating student-facing exploit demos run with httpyac in vulnerabilities/.../http/ directories. Auto-invoke when working with .exploit.http or .fixed.http files, directories like http/e01/, http/e02/, demo annotations, narrative-style request titles, or IMPACT comments. Do NOT use for E2E specs in spec/ - those use utils.cjs helpers like $(response) and auth.basic() which are NOT available here.
---

# Interactive Demo Writing

Create student-facing exploit demonstrations run with `httpyac` (NOT uctest!).

## When to Use This Skill

- Creating `.exploit.http` or `.fixed.http` files
- Working in `vulnerabilities/.../http/eNN/` directories
- Writing demos for students to run in VSCode REST Client
- Using plain `response.parsedBody` syntax

## When NOT to Use

- **E2E specs** in `spec/vNNN/` directories
  - Those use `uctest` (NOT httpyac)
  - Those use `$(response).field()` (NOT `response.parsedBody`)
  - Those use `{{auth.basic()}}` (NOT manual headers)
  - Use the `http-e2e-specs` skill instead

**How to tell the difference:**
- If you see `$(response)` → you're in E2E spec territory
- If you see `{{auth.basic()}}` → you're in E2E spec territory
- If you see `@forceRef` → you're in E2E spec territory

## CRITICAL Differences from E2E Specs

| This Skill (Demos) | E2E Specs (spec/) |
|--------------------|-------------------|
| `response.parsedBody.field` | `$(response).field()` |
| Raw `Authorization:` header | `{{auth.basic()}}` |
| ONE assert per test | Multiple asserts OK |
| NO imports from other .http | Heavy imports |
| NO @ref/@forceRef | Complex dependency chains |
| Self-contained linear flow | Shared fixtures |
| Run with `httpyac` | Run with `uctest` |
| NO database seeding helpers | `platform.seed()` available |

## Running Demos

```bash
httpyac file.http -a    # Run ALL requests in file
```

Students run demos using VSCode REST Client extension, clicking each request manually.

## File Structure

```
vulnerabilities/.../http/
├── common/
│   └── setup.http           # Shared variables only
├── e01/
│   ├── e01_dual_auth_refund.exploit.http   # Shows vuln succeeds
│   └── e01_dual_auth_refund.fixed.http     # Shows vuln is fixed
├── e02/
│   ├── e02_cart_swap_checkout.exploit.http
│   └── e02_cart_swap_checkout.fixed.http
```

**Note**: Fix for vulnerability X is in directory e(X+1), not eX!

## Basic Structure

```http
# @import ../common/setup.http
@host = {{base_host}}/v301

### SpongeBob checks his recent orders
GET {{host}}/orders
Authorization: Basic {{btoa("spongebob:bikinibottom")}}

?? status == 200

### EXPLOIT: Plankton reads SpongeBob's orders
GET {{host}}/orders?user=spongebob
Authorization: Basic {{btoa("plankton:i_love_my_wife")}}

?? status == 200
?? js response.parsedBody.orders.length > 0
```

## Assertion Rules (Same Gotchas!)

### Operator Required

```http
# CORRECT
?? js response.parsedBody.email == plankton@chum-bucket.sea
?? status == 200

# WRONG - no operator, becomes request body!
?? js response.parsedBody.email.includes("plankton")
```

### No Quotes on RHS

```http
# CORRECT
?? js response.parsedBody.status == approved

# WRONG - quotes become part of literal
?? js response.parsedBody.status == "approved"
```

## ONE Assert Per Test Rule

Focus on the **single most impactful proof** of the vulnerability:

```http
### WRONG - too many asserts
POST /cart/checkout
?? status == 200
?? js response.parsedBody.order_id != null
?? js response.parsedBody.total > 0
?? js response.parsedBody.items.length > 0

### CORRECT - one focused assert
POST /cart/checkout
?? js response.parsedBody.order_id != null
# IMPACT: Plankton just charged Patrick's credit card!
```

## Character Logic (CRITICAL)

**Attacker uses THEIR OWN credentials!**

The exploit comes from **confusion** in the application logic, not password theft.

```http
# WRONG - using victim's password (that's password theft!)
Authorization: Basic {{btoa("spongebob:bikinibottom")}}

# CORRECT - attacker's own credentials
Authorization: Basic {{btoa("squidward:clarinet123")}}
GET /messages?user=spongebob  # confusion happens HERE
```

See the `spongebob-characters` skill for full character rules.

## Annotation Style

### Good (Behavioral, Narrative)
```http
### SpongeBob checks his messages
### Plankton tries to read SpongeBob's messages
### EXPLOIT: Squidward reads SpongeBob's private notes
```

### Bad (Technical Jargon)
```http
### User authenticates via Basic Auth and retrieves messages
### Authentication validation with consistent parameter sourcing
### Vulnerability: Parameter source confusion in authentication
```

## NO Imports (Except common/setup.http)

```http
# CORRECT - only import shared setup
# @import ../common/setup.http

# WRONG - don't import other .http files
# @import ../e01/e01_exploit.http
# @ref some_named_request
```

## NO Database Reset/Seeding

Interactive demos run against a **live database** that students may have modified. Account for this:

```http
### Record Plankton's starting balance
# @name initial_balance
GET /account/credits
Authorization: {{plankton_auth}}

### ... (exploit happens) ...

### Verify balance changed
GET /account/credits
Authorization: {{plankton_auth}}

?? js parseFloat(response.parsedBody.balance) > {{parseFloat(initial_balance.balance)}}
```

## Using Variables for Clarity

```http
# Good - variables make flow clear
# @name cart
POST /cart?restaurant_id=1
Authorization: {{plankton_auth}}

POST /cart/{{cart.cart_id}}/items
Authorization: {{plankton_auth}}
Content-Type: application/json

{ "item_id": "4" }
```

## Console Output for Insight

Use `console.info()` to show values that aren't visible otherwise:

```http
{{
  console.info("Cart ID:", cart.cart_id);
  console.info("Order total:", order.total);
}}
```

## See Also

- [syntax.md](syntax.md) - Plain httpyac syntax reference
- [narrative-guide.md](narrative-guide.md) - Character voice and impact writing
- [HTTP Syntax Quick Reference](../../references/http-syntax-quickref.md) - Cheat sheet
- [Character Profiles](../../references/character-profiles.md) - Quick character lookup
- [http-assertion-gotchas](../http-assertion-gotchas/SKILL.md) - Assertion pitfalls
- [spongebob-characters](../spongebob-characters/SKILL.md) - Character rules
