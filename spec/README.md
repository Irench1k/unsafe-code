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

## Inheritance & Tag Management (ucspec)

Use `ucsync` (or `uv run ucspec`) to manage inherited specs and tags:

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

**ucspec OWNS all `@tag` lines** in .http files. Never edit them manually - configure tags in `spec.yml`:

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

- Auth helpers: `auth.basic`, `auth.login`, `auth.restaurant`, `auth.admin`.
- Platform helpers: `platform.seed`, `platform.reset` (seed already resets), `order.balanceAfter`, `order.total`, `menuHelper.firstAvailable`, response wrapper `$(response)` (`status()`, `isOk()`, `isError()`, `field()`, `hasFields()`, `hasOnlyUserData()`).
- Place calculations in JS assertions, not handwritten arithmetic.

## Authoring Checklist

- Import the right `_imports.http` for your depth; avoid duplicate paths.
- Declare `@name` for any reusable step; don't manually edit `@tag` lines (ucspec manages them).
- Use `@forceRef` chains for mutable state machines; keep the chain consistent (setup steps that are `@forceRef` must continue to force-ref their own dependencies).
- Keep setup minimal: seed only the actors and balances you need; avoid double-resetting.
- Assertions should prove both status and semantics (ownership, balance, totals, state transitions).
- When testing parameter confusion or ownership, cover all supported auth methods for that endpoint (basic vs cookie vs API key) but keep each file scoped to its endpoint.

## Tools and Generation (ucspec)

`ucsync` (alias for `uv run ucspec`) manages inherited test files:

- Scans source version's directory tree and generates `~`-prefixed inherited files
- Preserves `@name` / `@ref` / `@forceRef` chains and file structure
- Infrastructure files (`_imports.http`, `_fixtures.http`) are copied without prefix
- New/override files in child version take precedence over inherited
- Syncs `@tag` lines based on `spec.yml` configuration
- Removes orphaned inherited files when source files are removed or excluded

Run `ucsync` after modifying `spec.yml` or adding new specs to regenerate inherited files.

## Versioning

- `spec/v301` targets v301 of the API (r03 authorization confusion dual-auth refund).
- `spec/v302` inherits from v301, adds cart-swap vulnerability, fixes dual-auth.
- Future versions follow the same pattern: inherit, exclude fixed vulns, add new ones.

## Example Dependency Chain (Refund Status)

```
cart/checkout/post/_fixtures.http        -> @name order_checkout_plankton
orders/status/patch/happy.http           -> @forceRef order_checkout_plankton => @name delivered_order
orders/refund/post/happy.http            -> @forceRef delivered_order        => @name large_refund_pending
orders/refund-status/patch/happy.http    -> @forceRef large_refund_pending   => approve/reject happy path (@tag ci)
orders/refund-status/get/happy.http      -> @forceRef refund_approved        => read status (@tag ci)
```

Each layer owns its setup, and downstream specs never rebuild state by hand.
