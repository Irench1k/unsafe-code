# Demo Style Philosophy

> **The Golden Rule:** Every line must justify its existence.
> If it doesn't serve the exploit demonstration, remove it.

---

## Core Principles

| Priority | Principle |
|----------|-----------|
| 1 | **CLEAN > VERBOSE** - Fewer lines, less noise |
| 2 | **SIMPLE > COMPLEX** - Built-in features over custom code |
| 3 | **MINIMAL > COMPREHENSIVE** - Only assert what matters |
| 4 | **OBVIOUS > DOCUMENTED** - Code should explain itself |
| 5 | **PRESERVE > REWRITE** - Surgical changes to good work |

---

## Post-Request Element Ordering (STRICT)

After each request, elements MUST appear in this order:

```http
### Request title
GET /endpoint
Authorization: {{plankton_auth}}

@session = {{refreshCookie(response, session)}}     # 1. Session renewal FIRST
@cart_id = {{response.parsedBody.cart_id}}          # 2. Other variable extractions

?? body email == plankton@chum-bucket.sea           # 3. Assertions
?? status == 200

{{                                                   # 4. console.info LAST
  console.info("💰 Balance: $" + response.parsedBody.balance);
}}
```

**Why this order?**
- Session must be captured before anything else (may be needed by next request)
- Variables extracted before assertions (assertions may use them)
- Assertions before logging (we verify before we celebrate)

---

## Variable Extraction: Inline > @name

**Prefer inline extraction:**
```http
POST /cart
Authorization: {{plankton_auth}}

@cart_id = {{response.parsedBody.cart_id}}
```

**Avoid @name unless truly needed:**
```http
# ❌ Verbose - adds indirection
# @name cart
POST /cart
Authorization: {{plankton_auth}}

@cart_id = {{cart.cart_id}}
```

**When @name IS appropriate:**
- Distinguishing multiple similar requests (e.g., two GET /orders with different auth)
- When httpyac requires it for certain variable scoping

---

## console.info: Strategic Placement Only

**Target:** 2-3 per demo file, at key state transitions.

### ✅ KEEP - Adds value

```http
# State tracking between requests
{{ console.info("💰 Balance BEFORE: $" + response.parsedBody.balance); }}

# Exploit impact summary
{{ console.info("🚨 EXPLOIT: Balance increased without payment!"); }}

# Business impact narrative
{{ console.info("📈 Free " + kelp.name + " worth $" + order_total + "!"); }}
```

### ❌ REMOVE - Redundant noise

```http
# Echoes what assertion already shows
?? body email == plankton@chum-bucket.sea
{{
  console.info("Logged in as:", response.parsedBody.email);  // REDUNDANT!
}}

# Narrates obvious action
{{ console.info("Sending login request..."); }}  // We can see the request!

# Every single request
{{ console.info("Step 1 complete"); }}
{{ console.info("Step 2 complete"); }}
{{ console.info("Step 3 complete"); }}  // TOO MANY!
```

---

## Section Markers: Complexity-Based

### Simple Demos (≤4 requests, linear flow)

**No markers needed** - the flow is obvious:

```http
### Plankton logs in
POST /auth/login
...

### Plankton checks his balance
GET /account/credits
...

### Plankton exploits the flaw
GET /account/credits
Content-Type: application/x-www-form-urlencoded

amount=100
```

### Complex Demos (>4 requests, mixed stages)

**Use section markers** as standalone comment lines:

```http
# --- Legitimate Usage ---

### Sandy demonstrates normal refund flow
POST /orders/123/refund
...


# --- EXPLOIT ---

### Plankton discovers the loophole
POST /orders/123/refund
X-API-Key: trust_me_bro
...
```

**Marker placement:** ABOVE the `###` title, as a standalone `#` comment line.

---

## Visual Spacing

| Context | Blank Lines |
|---------|-------------|
| Between related requests | 1 |
| Before section markers | 2 |
| Before major transitions | 2 |
| After file header/imports | 2 |

Keep files **scannable**, not cluttered.

---

## Assertions: Minimal and Meaningful

### Prefer body shorthand

```http
# ✅ Clean
?? body email == plankton@chum-bucket.sea

# ❌ Verbose (only when computation needed)
?? js response.parsedBody.email == "plankton@chum-bucket.sea"
```

### Skip redundant status checks

```http
# ❌ Redundant - if body assertion passes, status was 200
?? status == 200
?? body email == plankton@chum-bucket.sea

# ✅ Just the meaningful assertion
?? body email == plankton@chum-bucket.sea
```

### Use `?? js` only when computation is needed

```http
# Comparison/math requires js
?? js parseFloat(response.parsedBody.balance) > 100
?? js response.parsedBody.orders.length == 0
```

---

## File-Level Context

Start demos with brief explanatory comments:

```http
# @import ../common/setup.http
@host = {{base_host}}/v203

# Restaurant managers can approve or reject refunds themselves
# (previously this was done by Sandy herself, manually)

# Plankton discovers a loophole: restaurant managers approve refunds via X-API-Key,
# but the server only checks IF a key is present, not whether it's valid!
```

**Include:**
- What feature Sandy introduced (business context)
- Why it exists (motivation)
- The loophole being exploited (foreshadowing)

**Avoid:**
- Technical implementation details
- CWE numbers or security jargon
- Lengthy paragraphs

---

## exploit.http vs fixed.http: Parallel Structure

Both files should follow the **same flow** with different actors:

| Aspect | exploit.http | fixed.http |
|--------|--------------|------------|
| Actor | Attacker (Plankton) | Sandy (testing fix) |
| Flow | Same sequence | Same sequence |
| Outcome | Attack succeeds | Attack blocked |
| Assertions | Prove exploit worked | Prove fix holds |

**Why parallel?** Easier to compare, validates we're testing the same thing.

---

## Preserve Good Existing Work

When existing demos have quality content:

- **Surgical changes** - modify only what needs fixing
- **Minimal diffs** - don't rewrite for style preferences
- **Respect voice** - keep interesting phrases and character

**Rewrite ONLY when:**
- Fundamentally broken or incorrect
- Unreadable or confusing
- Missing critical elements

---

## No Inconsistent Enhancements

If you can't apply something **consistently everywhere**, DON'T add it:

- ❌ Emojis in some demos but not others
- ❌ Section markers in some but not others (unless complexity warrants)
- ❌ console.info density varies wildly between similar demos

**Either standardize or omit.**

---

## Anti-Patterns (DO NOT)

| Anti-Pattern | Why It's Wrong | Do This Instead |
|--------------|----------------|-----------------|
| `GET {{host}}/orders` or `GET {{base}}/orders` | httpyac auto-prefixes from @host | `GET /orders` |
| `# @disabled` | Demos are manually clicked, not CI-run | Fix or delete the file |
| `@name cart` → `cart.cart_id` | Generic, indirect | `@cart_id = {{response.parsedBody.cart_id}}` |
| `refreshCookie()` after GET | GET never sets cookies | Only after login/mutating POST |
| `/account/credits` for reset | Increments, not idempotent | `seedBalance()` helper |
| `{"item_id": "4"}` | Magic number | Fetch from /menu |
| 7+ console.info per file | Noise obscures exploit | 2-3 at key moments |
| `?? status == 200` everywhere | Implied by body assertions | Only when status IS the test |
| `@name` without using it | Dead code | Remove or use it |
| `@title`/`@description` | Not rendered anywhere | Remove |
| Mixing `#` and `//` comments | Inconsistent | Pick one per context |

---

## Quick Checklist

Before finalizing ANY demo change:

- [ ] No `{{base}}/` or `{{host}}/` prefixes in URLs
- [ ] No `@disabled` directives added
- [ ] `@name` only when truly needed (with descriptive name, not generic)
- [ ] `refreshCookie()` only after login or mutating POST (NOT after GETs)
- [ ] State reset uses `seedBalance()` not `/account/credits`
- [ ] Item IDs fetched from /menu, not hardcoded
- [ ] Is the file SHORTER or same length? (If longer, justify each line)
- [ ] Did I use the simplest syntax available?
- [ ] Does every assertion serve the exploit demonstration?
- [ ] Are console.info statements strategic (2-3 max)?
- [ ] Is post-request ordering correct (session → vars → asserts → logs)?
- [ ] Does it preserve existing quality where appropriate?

---

## See Also

- `demo-conventions/SKILL.md` - HOW: httpyac syntax patterns
- `http-syntax/SKILL.md` - REFERENCE: syntax details
- `http-gotchas/SKILL.md` - REFERENCE: critical pitfalls
- `spongebob-characters/SKILL.md` - Character rules
