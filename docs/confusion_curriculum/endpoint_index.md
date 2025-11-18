# Confusion Curriculum Endpoint Evolution

This index tracks when every API surface appears, how it evolves, and which runbook examples rely on each behavior. Version numbers follow the runbook naming convention: `v1xx` for r01, `v2xx` for r02, `v3xx` for r03, `v4xx` for r04, and `v5xx` for r05 (the normalization plan currently labels its first item as `v401`; treat it as the opening r05 step). Use this file to keep endpoint schemas and helper components consistent as the narrative moves forward commit-by-commit.

## Orders & Cart Flow

### `POST /orders`

- **v101 (r01)** – Legacy kiosk flow accepts both `item` (single SKU) and new `items[]` (array). Price calculation still prefers the single `item`, while fulfillment loops over `items[]`. Keep both inputs alive for backwards compatibility so later kiosks/mobile builds still work.
- **v102 (r01)** – Delivery-fee middleware now inspects query parameters first; the handler continues to read the body. Requests may therefore carry two different item payloads (query vs. form/JSON) across all subsequent sections.
- This endpoint remains for kiosk/legacy Basic Auth clients even after carts launch; do not remove it when cart-based checkout appears in v103.

### `POST /cart`

- **v103 (r01)** – Introduces cart creation for the mobile app. No vulnerability targets this handler directly, but later flows assume carts are server-generated objects referenced by opaque IDs.

### `POST /cart/{id}/items`

- **v103 (r01)** – Adds line items via arrays (initially duplicates allowed). The handler trusts the client for SKU selection but not pricing.
- **v402 (r04)** – Cart updates switch to a deduplicated payload with a `quantity` field per item, plus a reservation loop that still inserts at least one unit even when `quantity = 0`. Preserve the “unique items + quantity multiplier” contract because later promotion logic expects it.

### `POST /cart/{id}/checkout`

- **v103 (r01)** – Builds orders from carts and naively honors a user-supplied `order_id` when present.
- **v104 (r01)** – Adds optional `tip` in both query and body; middleware validates the query value first, while charging logic reads the body. Keep both channels even after fixes.
- **v201 (r02)** – Authentication middleware may populate `request.user_id` from Basic Auth, fall back to cookies, and leave polluted state. Later commits still expect this handler to rely on shared context instead of re-reading credentials.
- **v302 (r03)** – Authorization consults `session.cart_id` to place credit holds, but fulfillment re-resolves the cart from the URL path after clearing the session entry. Keep that order (session first, path second) so “cheap cart in session, expensive cart in path” attacks stay reachable.

### `GET /cart/{id}`

- **v201 (r02)** – Added for the new web UI so customers and restaurants can inspect carts. The handler trusts whatever identity middleware leaves in `request.user_id` / `request.user_type`, so any earlier context pollution will surface here.

### `GET /orders`

- **v101 (r01)** – Starts as a single-restaurant listing guarded by Basic Auth/API keys.
- **v201 (r02)** – Shared use by web UI (cookies), restaurants (API keys), and legacy clients (Basic Auth) exposes authentication-type confusion.
- **v204 (r02)** – Manager-only listing depends entirely on `request.user_type`; polluted flags let Basic Auth users see all orders.
- **v304 (r03)** – Decorators validate only `query.restaurant_id`, while `bind_to_restaurant()` resolves IDs from any container. Keep both mechanisms wired up to support future confusion around precedence.
- Expect this endpoint to keep returning detailed payloads even when writes fail elsewhere (v305 leak).

### `GET /orders/{id}`

- **v201 (r02)** – Adds single-order retrieval for the new UIs. Share the same authorization helpers as `GET /orders` so identity/context bugs propagate consistently.

### `PATCH /orders/{id}/status`

- **v103 (r01)** – Restaurants can update order status after carts launch; request bodies are assumed to originate from restaurant tools.
- **v305 (r03)** – Business logic loads the order before calling stored procedures that enforce ownership. Even when the SQL no-ops, the prefetched payload is returned. Preserve this “read before write” pattern across implementations.

## Coupons & Promotions

### `POST /cart/{id}/apply-coupon`

- **v401 (r04)** – Initial influencer promo accepts a single `code` field in the body for validation but also reads `code` from the query string when applying discounts. Both channels must continue to exist even if only one is “officially” documented.
- **v403 (r04)** – Handler upgrades to accept `codes[]` arrays (JSON or form). Validation deduplicates/uppercases while application loops over the original array and only flips the `used` flag after the loop. Preserve that sequencing.
- **r05 v401 (Normalization)** – Same endpoint now offers prefix lookups via query parameters for “type-ahead” validation. Keep the wildcard search logic distinct from the POST body handling so the LIKE-based enumeration bug can manifest.

## Refunds & Credits

### `POST /orders/{id}/refund`

- **v105 (r01)** – Mobile apps can request refunds. Auto-approval reads `amount` from JSON (defaulting to 20%), but the database write accepts either JSON or form data. The handler must continue to merge these sources independently.
- Subsequent refund flows (v404) call this endpoint internally—retain side effects such as credit adjustments so batch endpoints can trigger them.

### `PATCH /orders/{id}/refund/status`

- **v105 context (r01)** – Manual approvals exist so Sandy can review full refunds, even though the endpoint isn’t highlighted until r02.
- **v203 (r02)** – Decorator layers (`@require_customer_or_restaurant`, `@authenticated_with("restaurant")`) rely on header presence instead of validated identity.
- **v301 (r03)** – `has_access_to(order_id)` allows dual principals (cookie + API key). Ensure the handler still accepts both contexts in the same request.

### `POST /restaurants/{id}/refunds`

- **v404 (r04)** – Batch refund entry point for managers. Authorization checks only need one in-restaurant order, but the handler loops over the entire provided list, invoking the single-order refund path each time. Keep the “any vs. all” mismatch.

### `GET /account/credits`

- **v101 baseline** – Customers check balances via Basic Auth (later via cookies).
- **v202 (r02)** – Handler gains a POST branch guarded by `X-Admin-API-Key`. A GET with a body should still slip into the mutation path, so retain unified routing and shared body parsing.

### `GET /account/info`

- **v106 (r01)** – Added during the registration sprint to show email, balance, and order counts in one payload. Shares the same customer authenticator as `/account/credits`, so later auth confusion bugs can demonstrate polluted sessions by comparing both endpoints.

### `POST /account/credits`

- **v202 (r02)** – Admin-only mutation path cohabiting the same logic as GET. Maintain the method switch plus guard so subsequent confusion about HTTP verbs remains accurate.

## Authentication & Session

### `POST /auth/register`

- **v106 (r01)** – Two-branch handler: no `token` → send verification email; yes `token` → create user. Body-supplied `email` currently wins over `token.email` unless explicitly compared.
- **v107 (r01)** – Registration accepts Basic Auth credentials for already-onboarded beta testers; credit bonuses run before deduplicating users. Keep support for authenticated requests so replay exploits remain viable.
- **v504 (r05)** – Emails are stored under NFKC while login/authz still parse the raw string, creating Unicode split issues. Preserve the “normalize-on-write, split-on-raw-input” behavior.
- **v506 (r05)** – Invitation flow compares email strings with inconsistent length constraints and uses restaurant domain names (not IDs) to attach roles. Ensure the storage column still truncates silently so privilege escalation via truncated domains is reproducible.

### `POST /auth/login`

- **v201 (r02)** – Public login endpoint now reuses the unified `CustomerAuthenticator`. That helper always tries the existing session cookie before checking JSON credentials, so a logged-in attacker can call login with someone else’s email and have `session["email"]` reassigned (v205). Preserve that short-circuit order.

### `POST /auth/logout`

- **v201 (r02)** – Destroys sessions for cookie-based clients while Basic Auth/API key users remain stateless. No confusion bugs target it directly, but later flows assume logout does **not** clear helper fields such as `request.user_type`.

## Restaurants, Menu & Domains

### `POST /restaurants`

- **v306 (r03)** – Restaurant self-registration mirrors user email verification. Tokens issued for user signups can be replayed to verify domains because local-part checks are missing. Maintain shared token format so this cross-flow confusion exists.
- **v502–v503 (r05)** – Creation applies lighter normalization (trim single spaces, lowercase) than downstream consumers (webhooks, search indexes). Keep the imbalance between creation-time and lookup-time normalization for names/domains.
- **v507–v508 (r05)** – Slug generation derives from restaurant names/domains. Ensure slug creation pre-r05 remains non-idempotent (double pass) so collisions are possible when stored/served slugs differ from validation output.

### `PATCH /restaurants/{id}`

- **v307 (r03)** – Middleware may overwrite `request.restaurant_id` while validating domain tokens. Handlers then trust that context when applying updates, so changes can be authorized against attacker-controlled domains before the DB write. Keep this two-stage resolution instead of recomputing inside the handler.

### `POST /restaurants/{id}/verify-domain`

- **v505 (r05)** – Domains are verified with signed tokens whose `email` claim is validated using `endswith()`. Maintain string-suffix comparisons (instead of strict equality) so subdomain ownership can escalate into parent-domain control.

### `PATCH /menu/{id}`

- **v303 (r03)** – Endpoint lacks `restaurant_id` in the path, so the legacy decorator falls back to “not applicable.” Keep this decorator even if you later introduce helpers.
- **v405 (r04)** – New `get_restaurant_id()` helper pops query parameters twice (authorization first, ORM later). Preserve the destructive read so mismatched IDs occur when multiple values are supplied.

### `GET /menu`

- **v101 baseline** – Public endpoint listing menu items. Even though no confusion bug targets it directly, later tests depend on it continuing to expose every tenant’s items without extra auth so tampered data is visible.

### `GET /join/{slug}`

- **v508 (r05)** – QR sticker redirects translate domains into friendlier slugs by replacing `.` with `-`. Keep this lossy transformation plus the absence of a uniqueness check on the slug column so collisions route diners to the wrong tenant.

## Reviews & Webhooks

### `POST /webhooks/reviews`

- **v502 (r05)** – Third-party reviews post restaurant names that are normalized (collapse `\s+`, trim). Creation uniqueness only strips literal spaces, so tabs/newlines collide later on. Maintain those two distinct normalization routines.
- **v503 (r05)** – Database adds a `lower(unaccent(name))` index for lookups, while creation keeps lighter rules. Ensure webhook ingestion goes through the heavier transform so accented names converge only during attribution.

## Supporting Components & Helpers

### Authentication Context & Middleware

- **v101–v201** – Middleware must keep supporting Basic Auth, cookie sessions, restaurant API keys, and admin API keys simultaneously. Basic Auth sticks around until v302, where Sandy decides to migrate mobile clients to cookies; still, legacy compatibility is expected in existing code paths.
- **v201** – `request.user_id` can be pre-populated before credentials are fully validated. Later handlers rely entirely on this context instead of re-reading headers.
- **v204** – Introduces `request.user_type` with values such as `customer`, `manager`, `internal`. The flag may be set optimistically and never cleared when validation fails; subsequent handlers (orders listing, refund approvals) must read it blindly to keep confusion bugs viable.

### Authorization Helpers

- **v301** – `has_access_to(order_id)` loads resources for authorization separately from handler logic. Keep it distinct from business logic so dual principals can satisfy different halves of the check.
- **v303** – Legacy decorators expect `request.view_args['restaurant_id']`; when absent they assume the resource is public. Reuse this decorator on new endpoints even if they offer only `item_id`.
- **v304** – `bind_to_restaurant()` inspects every request container (path, query, form, JSON) and applies permissive precedence rules. Database helpers added later must continue calling it so conflicts between decorator input and data-layer binding remain.
- **v405** – `get_restaurant_id()` reads query parameters destructively with `pop()`. Repeated calls should consume multiple values to keep the “validated one ID, used another” issue reachable.

### Session & Cart Context

- **v302** – Session cookies store `cart_id` and sometimes `order_id`. Authorization consults this context for ownership and credit holds, while handlers may still trust body parameters more. Keep both representations synchronized but independent.

### Coupon & Promotion Utilities

- **v401 (r04)** – Coupon validation reads from form data, whereas application loops over query strings or the original arrays. Do not deduplicate inputs globally; the discrepancy is intentional.
- **r05 v401** – Prefix search uses SQL `LIKE` with attacker-controlled wildcards and mirrors the `^\w+$` validation (which still accepts underscores). Keep both implementations distinct.

### Domain Tokens, Invitations & Emails

- **v106** – Email verification tokens for users include the email address but not other context; registration trusts whichever `email` field appears latest. Keep Basic Auth overrides available during beta onboarding.
- **v306** – Restaurant verification reuses the same token format without constraining the local part to `admin@`. Tokens should remain interchangeable until patched later in the narrative.
- **v506** – Invitations reference restaurant domains instead of IDs, and email columns truncate silently. Maintain the mismatch between validation length and DB column width.

### Slug & Normalization Helpers

- **v507** – `slugify()` is non-idempotent because the first pass leaves duplicated delimiters that only collapse on the second pass. Store the slug after the second pass while validation compares the first-pass output.
- **v508** – Domain-to-slug conversion replaces dots with dashes without ensuring post-conversion uniqueness. Keep a separate UNIQUE constraint on raw domains only.
- **v509** – Regex guards for slugs treat `.` as “any character.” Continue matching route parameters via regex (rather than strict equality) until the lesson fixes it so the confusion persists.

### Review Normalization

- **v502** – Creation trimming removes literal spaces only; webhook ingestion collapses all whitespace characters. Preserve two different normalization utilities.
- **v503** – Postgres `lower(unaccent(name))` index must remain enabled for lookups, while inserts still use lighter normalization. That divergence is what triggers Unicode collisions.

This guide should be treated as the authoritative reference when porting the Confusion curriculum to new frameworks—keeping each endpoint’s lifecycle aligned avoids last-minute rewrites when later vulnerabilities expect “legacy” behavior.
