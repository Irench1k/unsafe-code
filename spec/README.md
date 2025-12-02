# E2E Spec Suite

End-to-end specs for the Confusion tutorial apps using `uctest` (our fork of httpyac). The suite uses a nested, endpoint-first layout so every file focuses on a single responsibility and delegates shared setup to reusable fixtures.

## Layout

The spec suite mirrors the API surface with nested directories:

```
v301/
  _imports.http               # version-wide imports
  cart/checkout/post/…        # endpoint directories by resource/method
  orders/status/patch/…       # happy/authn/authz/guardrails per verb
  orders/refund-status/get/…  # separate files per endpoint

v302/                         # inherits from v301
  cart/create/post/
    v302.http                 # new test for v302 behavior
    ~happy.http               # inherited from v301 (generated)
  orders/refund-status/patch/
    v302.http                 # tests the fix for dual-auth
    ~happy.http               # inherited (generated)
    # vuln-dual-auth-refund excluded (v302 fixes this)
```

Each leaf spec tests one endpoint behavior; prerequisites are pulled in with `@ref` / `@forceRef` rather than being reimplemented inline. State setup belongs to the endpoint that creates it (e.g., checkout lives in `cart/checkout/post/happy.http`; order delivery lives in `orders/status/patch/happy.http`), and downstream endpoints import those named requests.

## Running the Suite

The `uctest` CLI (npm package from `github:execveat/uctest`) provides a streamlined test runner:

```bash
# Run all tests (default, fail-fast)
uctest

# Run tests with specific tags (AND logic)
uctest @vulnerable             # Vulnerability demos only
uctest @authn @orders          # Auth tests in orders/ (BOTH tags)
uctest @happy @cart            # Happy path tests in cart/

# Run by path
uctest v301/orders             # All tests in orders/
uctest v302/cart/checkout      # Specific path

# Control behavior
uctest -a                      # All tests (no tag filter)
uctest -k                      # Keep going (no fail-fast)
uctest -r                      # Resume from last failure
uctest -v                      # Verbose output

# Combined examples
uctest @vulnerable @cart -v    # Verbose cart vulnerabilities
uctest @authn -k               # All auth tests, keep going
```

Tab completion is available for tags (`@<TAB>`), names (`:<TAB>`), and paths.

## Structure and Imports

- `spec/v301/_imports.http` pulls shared utilities (`../common.http`), auth helpers, and version-aware env.
- Each resource folder has its own `_imports.http` to keep relative paths simple.
- Endpoint folders are organized as `resource/<action>/<verb>/<focus>.http` (e.g., `orders/refund-status/patch/happy.http`).
- Shared fixtures live next to the endpoint they prepare (e.g., `cart/checkout/post/_fixtures.http` exports `@name order_checkout_plankton`).

## Inheritance & Tag Management (ucsync)

Use `ucsync` (or `uv run ucsync`) to manage inherited specs and tags:

```bash
# Generate inherited files + sync tags (default action)
ucsync

# Generate for specific version
ucsync v302

# Preview changes without modifying files
ucsync -n

# Clean up generated files
ucsync clean
```

### Inheritance Rules (`spec.yml`)

- `inherits: v301` - inherit entire directory tree from v301
- `exclude: [path/to/file.http]` - skip specific files from parent
- New files in child version override inherited ones at same path
- Generated files use `~` prefix: `~happy.http` (tracked in git)

### Tag Management

**ucsync OWNS all `@tag` lines** in .http files. Never edit them manually - configure tags in `spec.yml`:

```yaml
v301:
  description: Dual-Auth Refund Approval
  tags: [r03, v301]               # All tests get these tags
  tag_rules:
    "**/authn.http": [authn]      # Authentication tests
    "**/authz.http": [authz]      # Authorization tests
    "**/happy.http": [happy]      # Happy path tests
    "**/vuln-*.http": [vulnerable] # Vulnerability demos
    "auth/**": [auth]             # Auth endpoints
    "cart/**": [cart]             # Cart endpoints
    "orders/**": [orders]         # Order endpoints

v302:
  inherits: v301
  tags: [r03, v302]               # Override version tag
  # Inherits tag_rules from v301
```

Pattern syntax (fnmatch-style):
- `"auth/**"` → all files under auth/
- `"**/authn.http"` → all authn.http files anywhere
- `"**/vuln-*.http"` → filename pattern matching

Tags are computed by combining:
1. Version-level tags (`tags: [r03, v301]`)
2. Pattern-matched tags from `tag_rules`
3. Inherited rules from parent versions

All matching tags are applied to all requests in matching files. uctest handles test deduplication at runtime via `@ref` / `@forceRef` chains.

## Roles of Files

- `happy.http`: the canonical success path for that endpoint; tagged as a leaf when not referenced elsewhere.
- `authn.http`: authentication required/forbidden checks.
- `authz.http`: authorization/ownership/role guardrails.
- `params.http`, `validation.http`, `ownership.http`, `reuse.http`, etc.: focused cross-cutting behaviors.
- `_fixtures.http`: minimal reusable setups (named requests only, no `@tag`).

## Naming and Dependencies

- Every request must either declare `@name` (to be referenced) or be in a tagged test file. Do not leave unreferenced requests in untagged files.
- Use `@ref` when sharing an immutable or already-sufficient state (e.g., listing orders).
- Use `@forceRef` when you need a fresh state each time (state machines like status/ refund transitions).
- Keep seeds and mutations inside the first named request of a chain (never in file-level globals). Let upstream fixtures own reset/seed; downstream specs import them.

## Philosophy: One Endpoint, One Purpose

- Each file tests exactly one endpoint/verb. If you find yourself creating carts, adding items, delivering orders, and refunding all in one file—split it. Let `cart/checkout` create orders; let `orders/status` change status; let `orders/refund` create refunds; let `orders/refund-status` change refund status.
- Prefer importing the canonical setup from the endpoint that owns it. Example:
  - Need a delivered order? `@forceRef delivered_order` from `orders/status/patch/happy.http`.
  - Need a pending refund? `@forceRef large_refund_pending` from `orders/refund/post/happy.http`.
  - Need a checkout? `@forceRef order_checkout_plankton` from `cart/checkout/post/_fixtures.http`.
- If a file grows unwieldy, split by concern (happy vs authn vs authz vs validation) instead of mixing behaviors.

## Utilities (utils.cjs)

**Auth helpers:**
- `auth.basic("plankton")` - Basic Auth header (version-aware username)
- `auth.basic("plankton", "wrongpw")` - Test with wrong password
- `auth.login("plankton")` - Get session cookie for known user
- `auth.restaurant("krusty_krab")` - Restaurant API key
- `auth.admin()` - Admin API key

**User helpers:**
- `user("plankton").email`, `.shortId`, `.password`, `.id` - User properties
- `user("plankton").canLogin()` - Async check if user can login
- `user("plankton").canLogin("wrongpw")` - Test wrong password
- `user("plankton").balance()` - Get current balance

**Dynamic user verification** (for registration tests):
- `verify.canLogin(email, password)` - Check arbitrary credentials
- `verify.canAccessAccount(email, password)` - Check account access

**Platform helpers:**
- `platform.seed({ plankton: 200 })` - Reset DB and seed balances
- `platform.seedCredits("plankton", 200)` - Set balance only (no DB reset)
- `platform.reset()` - Reset database state

**Response wrapper `$(response)`:**
- `.status()`, `.isOk()`, `.isError()` - Status checks
- `.field("email")`, `.hasFields("email", "balance")` - Data access
- `.hasOnlyUserData("plankton")` - Ownership validation
- `.total()`, `.balance()` - Financial data (already parsed as float)

**Cookie helpers:**
- `extractCookie(response)` - Extract session cookie from response
- `hasCookie(response)` - Check if response sets a cookie (for auth failures)

**See [HTTP_SYNTAX.md](./HTTP_SYNTAX.md)** for complete syntax reference and common gotchas.

## Authoring Checklist

- Import the right `_imports.http` for your depth; avoid duplicate paths.
- Declare `@name` for any reusable step; don't manually edit `@tag` lines (ucsync manages them).
- Use `@forceRef` chains for mutable state machines; keep the chain consistent (setup steps that are `@forceRef` must continue to force-ref their own dependencies).
- Keep setup minimal: seed only the actors and balances you need; avoid double-resetting.
- Assertions should prove both status and semantics (ownership, balance, totals, state transitions).
- When testing parameter confusion or ownership, cover all supported auth methods for that endpoint (basic vs cookie vs API key) but keep each file scoped to its endpoint.

## Tools and Generation (ucsync)

`ucsync` (or `uv run ucsync`) manages inherited test files:

- Scans source version's directory tree and generates `~`-prefixed inherited files
- Preserves `@name` / `@ref` / `@forceRef` chains and file structure
- Infrastructure files (`_imports.http`, `_fixtures.http`) are copied without prefix
- New/override files in child version take precedence over inherited
- Syncs `@tag` lines based on `spec.yml` configuration
- Removes orphaned inherited files when source files are removed or excluded

Run `ucsync` after modifying `spec.yml` or adding new specs to regenerate inherited files.

### Import Rewriting in Inherited Files

When ucsync generates inherited files (~ prefix), it rewrites `@import` statements to reference the inherited versions of sibling files:

| Original Import | Rewritten To | Condition |
|-----------------|--------------|-----------|
| `./happy.http` | `./~happy.http` | Sibling test file exists in parent |
| `../_imports.http` | unchanged | Infrastructure files keep names |
| `../../../common.http` | unchanged | Files outside version directory |
| `./happy.http` | unchanged | Child has local override of `happy.http` |

**Override-Aware Rewriting**: If the child version has a **local override** for an imported file, the import is NOT rewritten to use `~`. This ensures inherited files correctly reference the local version instead of a non-existent `~` version.

### Acknowledging Local Overrides

When a local file shadows an inherited file, ucsync warns:

```
Warning: Local override 'cart/create/post/happy.http' shadows inherited file.
Add to 'exclude:' in spec.yml to acknowledge.
```

Silence this warning by adding the file to `exclude:` in `spec.yml`:

```yaml
v301:
  exclude:
    - cart/create/post/happy.http  # Multi-tenant version with restaurant_id
```

This explicit acknowledgment ensures intentional overrides are documented and prevents accidental shadowing.

## Versioning

The full inheritance chain is:

**r02 (Authentication Confusion):**
```
v201 (Session Hijack - Base)
  └── v202 (Credit Top-ups)
       └── v203 (Fake Header Refund)
            └── v204 (Manager Mode)
                 └── v205 (Session Overwrite)
                      └── v206 (Fixed Final)
```

**r03 (Authorization Confusion):**
```
v206
  └── v301 (Dual-Auth Refund)
       └── v302 (Cart Swap Checkout)
```

Future versions follow the same pattern: inherit, exclude fixed vulns, add new ones.

## Adding New Versions

Follow this workflow when adding a new API version to the spec suite:

### Step 1: Create Directory Structure and Wire into spec.yml

```bash
# 1. Add version entry to spec.yml first
#    Define inherits, tags, and any exclusions

# 2. Run ucsync to generate the directory structure
ucsync                    # or: uv run ucsync

# This creates:
#   spec/vXXX/.env        (VERSION=vXXX)
#   spec/vXXX/_imports.http
#   spec/vXXX/...         (inherited files with ~ prefix)
```

### Step 2: Copy Tests Incrementally

**Never copy all tests at once.** Work file-by-file or category-by-category:

```bash
# 1. Identify a test file you expect to pass
#    Manually inspect the source test and the API behavior

# 2. Copy ONE file
cp spec/v201/cart/create/post/happy.http spec/vXXX/cart/create/post/

# 3. Run uctest immediately to verify
uctest vXXX/cart/create/post/happy.http

# 4. If it passes, commit. If not, investigate before proceeding.
```

### Step 3: Handle Test Failures from Schema Differences

When tests fail due to API differences (e.g., `tip` returns `0` vs `"0.00"`):

**DO NOT:**
- Disable or skip the test
- Add workarounds to support both behaviors
- Fudge assertions to be looser
- Just delete the problematic test

**DO:**
1. **Evaluate significance**: Is this difference intentional for the vulnerability showcase?
   - Check `vulnerabilities/.../README.md` to see if the difference matters

2. **If NOT significant** → Standardize the source code:
   - Pick the more robust behavior (e.g., `"12.34"` strings are better than `12.34` floats for precision)
   - Fix ALL versions where the deviation appears
   - Keep fixes as similar as possible across versions to minimize drift

3. **If intentional** → Document it:
   - Use version-specific test files (not inherited)
   - Document why the difference exists

### Example: Fixing a Schema Deviation

```bash
# 1. Test fails: v201 returns tip as number, v205 returns as string
uctest v201/cart/checkout/post/happy.http
# ✖ $(response).field("tip") == "0" (got 0)

# 2. Check if the difference matters for vulnerability showcase
#    Read vulnerabilities/.../r02_authentication_confusion/README.md
#    → The tip format is NOT relevant to auth confusion vulnerabilities

# 3. Standardize: make v201-v204 return strings like v205-v206
#    Edit source code in webapp/r02_authentication_confusion/e01_*/
#    Ensure all examples return Decimal strings consistently

# 4. Re-run tests to verify the fix
uctest v201/cart -k
```

### Design Principles for Inheritance

- **Maximize inherited specs**: The goal is high inheritance rate across versions
- **Eliminate insignificant differences**: Drift between versions should be intentional
- **Keep intentional deviations**: Natural evolution (adding security controls, etc.) is expected
- **Standardize on robust behaviors**: When in doubt, pick the more precise/safe option

## Example Dependency Chain (Refund Status)

```
cart/checkout/post/_fixtures.http        -> @name order_checkout_plankton
orders/status/patch/happy.http           -> @forceRef order_checkout_plankton => @name delivered_order
orders/refund/post/happy.http            -> @forceRef delivered_order        => @name large_refund_pending
orders/refund-status/patch/happy.http    -> @forceRef large_refund_pending   => approve/reject happy path (@tag ci)
orders/refund-status/get/happy.http      -> @forceRef refund_approved        => read status (@tag ci)
```

Each layer owns its setup, and downstream specs never rebuild state by hand.

## Quick Reference (Troubleshooting)

### "ref X not found in scope Y.http"

This error means uctest can't find the named request `X` when processing `Y.http`.

**Common causes and fixes:**

1. **Path-based execution doesn't include the file defining X**
   ```bash
   uctest v301/orders           # Won't find cart refs!
   uctest @orders v301/         # Scans entire v301/, finds cross-deps
   ```

2. **Missing import chain**
   ```http
   # Check Y.http has the right imports
   # @import ../_imports.http
   # @import ../../cart/checkout/post/happy.http  # If you need cart refs
   ```

3. **Inherited file references wrong sibling**
   ```http
   # In ~multi-tenant.http
   # @import ./happy.http       # WRONG if happy is also inherited
   # @import ./~happy.http      # CORRECT
   ```
   Fix: Run `ucsync` to regenerate imports.

4. **The @name doesn't exist**
   ```bash
   grep -r "@name X" spec/v301/
   ```

### Debugging Commands

```bash
uctest --show-plan v301/cart     # See execution order without running
uctest -v v301/cart/create       # Verbose output
uctest -k v301/                  # Keep going after failures
uctest -r                        # Resume from last failure
```

### File Naming Quick Reference

| File | Purpose |
|------|---------|
| `happy.http` | Success paths (canonical fixtures) |
| `authn.http` | Authentication tests |
| `authz.http` | Authorization tests |
| `_fixtures.http` | Named setups only (no tags) |
| `_imports.http` | Import chain |
| `~*.http` | Inherited (NEVER edit!) |

### Common Gotchas

1. **Assertions run AFTER request** - Capture pre-state in JS block:
   ```http
   {{ exports.before = await user("x").balance(); }}
   POST /action
   ?? js await user("x").balance() == {{before + 10}}
   ```

2. **No quotes on RHS of assertions**:
   ```http
   ?? js $(response).field("status") == delivered     # CORRECT
   ?? js $(response).field("status") == "delivered"   # WRONG
   ```

3. **@forceRef chain must be consistent** - If A @forceRef B, then B must @forceRef its deps too.

4. **Never edit @tag lines** - Managed by ucsync via spec.yml.
