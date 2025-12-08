---
name: vulnerable-code-patterns
description: Implementing production-quality vulnerable code for Unsafe Code Lab. Auto-invoke when working in exercise directories (eNN_*/), adding @unsafe annotations, implementing auth decorators/middleware, or refactoring code that must stay vulnerable. Covers Flask patterns and annotation syntax.
---

# Vulnerable Code Implementation

## When to Use This Skill

- Implementing new exercise code in eNN_*/ directories
- Adding or updating @unsafe annotations
- Writing auth decorators, middleware, helpers
- Refactoring without accidentally fixing vulnerabilities

## When NOT to Use This Skill

- Designing what vulnerability to build (use vulnerability-design-methodology)
- Writing .http demos (use http-demo-conventions)
- Writing e2e specs (use http-spec-conventions)

## Code Quality Standards

### Production-Quality Requirements

Vulnerable code must look professional:
- Proper error handling (try/except with meaningful messages)
- Logging where appropriate (not security warnings!)
- Type hints on public functions
- Docstrings explaining features (not security issues)
- Clean separation of concerns

### What the Vulnerability Should Be

- **Subtle**: Not obvious code smell
- **Realistic**: Could happen in real codebases
- **Educational**: Teaches a specific concept
- **Documented**: With @unsafe annotation

### What the Vulnerability Should NOT Be

- `def vulnerable_endpoint()` - Never obvious names
- `# WARNING: Security issue here` - Never warning comments
- Missing error handling - That's just bad code
- Hardcoded credentials - Unless that IS the lesson

## @unsafe Annotation Format

```python
# @unsafe {
#     "vuln_id": "v301",
#     "severity": "high",
#     "category": "authorization-confusion",
#     "description": "Decorator checks session but handler uses URL param",
#     "cwe": "CWE-863",
#     "fixed_in": "v302"
# }
def get_cart_items(cart_id):
    # This cart_id comes from URL, but decorator checked session cart
    ...
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| vuln_id | string | Version where vuln is introduced (v301) |
| severity | string | critical, high, medium, low |
| category | string | authorization-confusion, input-source-confusion, etc. |
| description | string | One-line behavioral description |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| cwe | string | CWE identifier (CWE-863) |
| fixed_in | string | Version where fixed (v302) |
| owasp | string | OWASP category reference |

## Common Vulnerable Patterns

### Decorator That Checks Wrong Thing

```python
def require_cart_owner(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # @unsafe: Checks session cart, but handler uses URL cart_id
        cart = get_cart_from_session()  # ← Source A
        if not cart or cart.user_id != current_user.id:
            abort(403)
        return f(*args, **kwargs)
    return decorated

@require_cart_owner
def update_cart(cart_id):  # ← Source B (URL parameter)
    cart = Cart.query.get(cart_id)  # Uses different source!
    ...
```

### Helper That Looks in Wrong Place

```python
def bind_to_restaurant(request):
    """Bind request to restaurant context."""
    # @unsafe: Checks URL param first, but POST body can override
    restaurant_id = (
        request.args.get('restaurant_id') or  # URL param
        request.json.get('restaurant_id') or  # Body - attacker controlled!
        session.get('restaurant_id')          # Session
    )
    ...
```

### Middleware That Trusts User Input

```python
@app.before_request
def set_user_context():
    """Set current user from auth header or session."""
    # @unsafe: Header takes precedence over session
    if 'X-User-Id' in request.headers:
        g.current_user_id = request.headers['X-User-Id']  # Trusted!
    else:
        g.current_user_id = session.get('user_id')
```

### Copy-Paste Progression (Authorization + Processing Split)

The most realistic pattern: show the SAME pattern working correctly in some endpoints, then failing in the vulnerable one.

```python
# CORRECT: get_order uses filtered result
@bp.get("/orders/<int:order_id>")
def get_order(restaurant_id: int, order_id: int):
    orders = find_orders_by_restaurant(restaurant_id, [order_id])
    require_condition(orders, "Order not found")
    return serialize_order(orders[0])  # ✓ Uses filtered result

# CORRECT: get_refund uses same pattern (works because single ID)
@bp.get("/orders/<int:order_id>/refund")
def get_refund(restaurant_id: int, order_id: int):
    orders = find_orders_by_restaurant(restaurant_id, [order_id])
    require_condition(orders, "Order not found")
    refund = get_refund_by_order_id(order_id)  # Technically uses original, but single ID = safe
    return serialize_refund(refund)

# @unsafe: batch_refund uses original IDs, not filtered result!
@bp.post("/refunds")
def batch_refund(restaurant_id: int):
    order_ids, reason = validate_request()
    orders = find_orders_by_restaurant(restaurant_id, order_ids)
    require_condition(orders, "No orders found")
    # BUG: Uses order_ids (original) not [o.id for o in orders] (filtered)!
    results = [issue_refund(oid, reason) for oid in order_ids]
    return serialize_results(results)
```

**Why this is powerful:**
1. Developer sees `get_order` and `get_refund` working
2. Developer copies pattern for `batch_refund`
3. Bug emerges from "works for 1, breaks for N"
4. Each piece looks individually correct

**Infrastructure justification:** `issue_refund(order_id, ...)` takes `order_id` because that's how the existing refund API works. The choice to pass `order_ids` is REASONABLE.

## Directory Structure

```
eNN_vulnerability_name/
├── __init__.py           # Blueprint registration
├── routes/
│   ├── __init__.py
│   ├── orders.py         # Order endpoints
│   └── cart.py           # Cart endpoints
├── auth/
│   ├── __init__.py
│   └── decorators.py     # Auth decorators (@unsafe often here)
├── models/
│   └── __init__.py       # SQLAlchemy models
└── utils.py              # Shared utilities
```

## Refactoring Rules

### Before Changing Any Code

1. **Check for @unsafe annotations** - Don't accidentally fix them!
2. **Run exploit demos** - Verify vuln still works after change
3. **Compare to previous version** - Understand the delta

### When Refactoring

- **NEVER** move vulnerable code without updating annotations
- **ALWAYS** test that vulnerability still works
- **DOCUMENT** why refactoring doesn't affect vulnerability

### Red Flags During Refactoring

- Moving checks earlier in the pipeline
- Consolidating multiple sources into one
- Adding validation "for consistency"
- "Fixing" what looks like a bug

## Verification Checklist

Before completing implementation:
- [ ] App reloads successfully (check `uclogs --since 1m`)
- [ ] @unsafe annotation present and accurate
- [ ] Exploit demo passes (`ucdemo`)
- [ ] Vulnerability is subtle (no obvious warnings)
- [ ] Code looks professional
- [ ] Previous vulnerability is fixed (if applicable)

## See Also

- [vulnerability-design-methodology](../vulnerability-design-methodology/SKILL.md) - Design phase
- [http-demo-conventions](../http-demo-conventions/SKILL.md) - Demo creation
- `docs/ANNOTATION_FORMAT.md` - Full annotation specification
