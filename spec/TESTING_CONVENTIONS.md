# E2E Testing Conventions

The e2e suite in `spec/v301/` (and inherited versions like `spec/v302/`) is endpoint-first: every file owns a single HTTP verb for a single endpoint and defers all shared state to fixtures or upstream endpoints. This keeps specs readable, debuggable, and composable as the tutorial grows (r01–r05).

## Run Modes

```bash
# Run all tests (fail-fast by default)
uctest

# Run tests by tag
uctest @vulnerable           # Vulnerability tests
uctest @happy @orders        # Happy path tests in orders/

# Run by path
uctest v301/orders           # All tests in orders/

# Control behavior
uctest -k                    # Keep going (no fail-fast)
uctest -r                    # Resume from last failure
```

## Layout

```
spec/v301/                              # base version
  _imports.http                         # version-wide imports
  cart/checkout/post/_fixtures.http     # reusable setups (named, untagged)
  cart/checkout/post/happy.http         # leaf tests for this endpoint
  cart/checkout/post/authn.http         # auth guardrails
  orders/refund-status/patch/happy.http # approve/reject success path
  orders/refund-status/patch/vuln-dual-auth-refund.http  # vulnerability test

spec/v302/                              # inherits v301
  cart/create/post/v302.http            # new test (git-tracked)
  cart/create/post/~happy.http          # inherited (generated, git-tracked)
  orders/refund-status/patch/v302.http  # tests the fix
  # vuln-dual-auth-refund.http excluded (v302 fixes this)
```

Rules:

- One endpoint/verb per file. If you start making carts, adding items, delivering, refunding, and reading status in one file—split it and import dependencies instead.
- Each folder has its own `_imports.http` to keep relative imports short; version root `_imports.http` pulls `../common.http`.

## Naming, Tagging, and Dependencies

- Every request must have **either** `@name` (referenced elsewhere) **or** be in a tagged file. Do not leave unreferenced requests in untagged files.
- Use `@ref` to reuse immutable or "good enough" state (list/lookups). Use `@forceRef` when state must be fresh for each test (state machines, balances, ownership you mutate).
- Chain discipline: if request A uses `@forceRef B`, then B must use `@forceRef` for its own prerequisites. This keeps test ordering faithful.
- Fixtures (`_fixtures.http`) export named requests only—no tags. Leaf files import them; tags are managed by ucspec.

## File Roles

- `happy.http` – canonical success path, tagged when it is a leaf.
- `authn.http` – authentication required/forbidden checks, tagged when they are leaves.
- `authz.http` – ownership/role checks, tagged when they are leaves.
- `params.http`, `validation.http`, `ownership.http`, `reuse.http`, etc. – focused behaviors per endpoint.
- `_fixtures.http` – reusable building blocks (named, untagged) that perform setup once.

## Setup and Seeding

- Seed inside the first named request of a chain, not at file scope. Never call `platform.reset()` right after `platform.seed()`—`seed` already resets.
- Seed only the actors/credits you need. Let upstream endpoints own their setup; downstream specs import them.
- Keep fixtures minimal: create the resource, return IDs, stop. Assertions and cross-cutting checks belong in the leaf files.

## State Machines and Ownership

- Status/refund transitions must use `@forceRef` chains so each test runs on clean state. Example chain (refund status):
  1. `cart/checkout/post/_fixtures.http` → `@name order_checkout_plankton`
  2. `orders/status/patch/happy.http` → `@forceRef order_checkout_plankton` → `@name delivered_order`
  3. `orders/refund/post/happy.http` → `@forceRef delivered_order` → `@name large_refund_pending`, `small_refund_auto`
  4. `orders/refund-status/patch/happy.http` → `@forceRef large_refund_pending` → approve/reject
  5. `orders/refund-status/get/happy.http` → `@forceRef refund_approved` / `refund_rejected`
- Do not recreate upstream flows inside downstream files.

## Authentication Coverage

- Cover all auth methods an endpoint accepts, but keep them in the right file:
  - `happy.http` proves valid auth + happy path.
  - `authn.http` proves unauthenticated requests fail.
  - `authz.http` proves wrong tenant/role cannot act.
- Avoid mixing authn/authz and happy assertions in the same request unless the endpoint surface is trivial.

## Assertions

- Always assert status + semantics (ownership, totals, balances, state).
- Use helpers from `utils.cjs`: `$(response).isOk()`, `isError()`, `field()`, `hasFields()`, `hasOnlyUserData()`, `order.total()`, `order.balanceAfter()`.
- Prefer precise numeric expectations (Decimal strings) and explicit state fields.

## Splitting and Delegation

- If a file grows long, split by concern (happy vs authn vs authz vs params). Keep each file scoped to its endpoint.
- When two endpoints share setup, move it to `_fixtures.http` under the producer endpoint, not into consumers.

## Common Pitfalls

- Untagged files: a request with no `@name` in an untagged file may never run.
- Inline mega-flows: creating carts/checkouts/refunds inside refund-status files leads to brittle, duplicated state.
- Seed in globals: causes multi-request chains to reset between steps—always seed inside the first named step.
- Missing `@forceRef` in state chains: stale state will mask bugs.

## ucspec

`ucsync` (alias for `uv run ucspec`) manages inherited test files for the nested directory structure:

- Scans source version's directory tree and generates `~`-prefixed inherited files
- Preserves `@name`/`@ref`/`@forceRef` chains and file structure
- Infrastructure files (`_imports.http`, `_fixtures.http`) are copied without prefix
- Syncs `@tag` lines based on `spec.yml` configuration
- New/override files in child version take precedence over inherited
- Removes orphaned inherited files when source files are removed or excluded

After updating specs, run `ucsync` to regenerate inherited files and sync tags.
