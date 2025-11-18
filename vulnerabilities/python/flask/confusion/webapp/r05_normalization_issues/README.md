## r05: Normalization Issues (Work in Progress)

_Feature focus:_ string manipulation, database constraints, Unicode handling \
_Student skill:_ spotting subtle differences in how data is cleaned, transformed, and compared

### What It Is

Character normalization confusion happens when two code paths apply **different string transformations** to the same logical input. One path might lowercase, the other might not. One might strip whitespace, the other might only trim. One might apply Unicode normalization, the other might ignore it.

The result: values that _should_ be "equal" diverge when checked vs. used, bypassing uniqueness constraints, access controls, or security boundaries.

### Framework Features Introduced

- String manipulation functions: `.lower()`, `.strip()`, `.replace()`
- Database constraints: `UNIQUE`, collations
- Text search and indexes: `unaccent()`, `ilike()`
- Regular expressions: `re.match`, `re.sub`, `\w` vs `\s`
- Unicode handling: `NFC`, `NFKD`, fullwidth vs. halfwidth chars
- URL/Slug generation

### Why Confusion Happens

- Different normalization rules are applied in different layers (e.g., application validation vs. database index).
- The database performs normalization automatically (e.g., case-insensitive collation) which the application logic doesn't expect.
- Case-insensitive (ilike) vs. case-sensitive (=) comparisons are used inconsistently.
- Developers "fix" one normalization bug by adding another layer of inconsistent transformation.
- Naive string parsing (like email.split('@')[1]) meets complex, normalized input.

### The Story

The platform is growing beyond Bikini Bottom! Sandy adds public-facing features: restaurant profile pages with SEO-friendly slugs, a review system, custom subdomains, and email-based manager assignment.

Mr. Krabs wants a memorable URL for the Krusty Krab. Sandy generates slugs from restaurant names: `krusty-krab.sea/krusty-krab`. She enforces uniqueness to prevent squatting.

Plankton sees opportunity. He crafts names that pass validation but collide after normalization, hijacking the Krusty Krab's reviews, stealing their subdomain, and confusing customers into visiting his copycat restaurant.

This section focuses on how **character-level transformations** create subtle mismatches that bypass security checks.

### Endpoints

| Lifecycle | Method | Path                            | Auth                 | Purpose                              | Vulnerabilities        |
| --------- | ------ | ------------------------------- | -------------------- | ------------------------------------ | ---------------------- |
| v401+     | POST   | /cart/{id}/apply-coupon         | Customer             | Attach coupons to cart               | v401, v403, v501       |
| v101+     | GET    | /menu                           | Public               | List menu items                      |                        |
| v101+     | GET    | /orders                         | Customer/Restaurant  | List orders                          | v201, v204, v304, v509 |
| v201+     | GET    | /orders/{id}                    | Customer/Restaurant  | Get single order                     | v305                   |
| v105+     | POST   | /orders/{id}/refund             | Customer             | Request refund                       | v105                   |
| v404+     | POST   | /restaurants/{id}/refunds       | Restaurant           | Batch refunds                        | v404                   |
| v303+     | PATCH  | /menu/items/{id}                | Restaurant           | Update menu item                     | v303, v405             |
| v306+     | POST   | /restaurants                    | Public/Admin         | Register restaurant + slug           | v306, v507, v508       |
| v307+     | PATCH  | /restaurants/{id}               | Manager              | Update restaurant profile            | v307, v508             |
| v505+     | POST   | /restaurants/{id}/verify-domain | Manager/Admin        | Confirm domain ownership             | v505, v506             |
| v502+     | POST   | /webhooks/reviews               | Third-party (Public) | Attribute reviews by normalized name | v502, v503             |
| v507+     | GET    | /restaurants/{slug}             | Public               | Public restaurant landing page       | v507                   |
| v508+     | GET    | /join/{slug}                    | Public               | QR redirect for table stickers       | v508                   |
| v509+     | ANY    | /manager/restaurants/{slug}/... | Manager/Admin        | Authz-protected slug routes          | v509                   |
| v106+     | POST   | /auth/register                  | Public               | Register user / invite managers      | v106, v107, v504, v506 |

#### Schema Evolution

##### Data Model Evolution

| Model                | v501 | v502 | v503 | v504                 | v505 | v506                             | v507          | v508 | v509 |
| -------------------- | ---- | ---- | ---- | -------------------- | ---- | -------------------------------- | ------------- | ---- | ---- |
| CouponLookup         | -    | -    | -    | -                    | -    | -                                | -             | -    | -    |
| ReviewNormalization  | -    | -    | -    | -                    | -    | -                                | -             | -    | -    |
| RegisterUserRequest  | -    | -    | -    | Email stored as NFKC | -    | `email` column length constraint | -             | -    | -    |
| DomainVerification   | -    | -    | -    | -                    | -    | -                                | -             | -    | -    |
| RestaurantSlug       | -    | -    | -    | -                    | -    | -                                | `+slug` field | -    | -    |
| ReviewWebhookPayload | -    | -    | -    | -                    | -    | -                                | -             | -    | -    |

##### Behavioral Changes

| Version | Component           | Behavioral Change                                                                                      |
| ------- | ------------------- | ------------------------------------------------------------------------------------------------------ |
| v501    | CouponLookup        | Prefix validation checks `^\w+$` (allows underscore); database uses `LIKE` with underscore as wildcard |
| v502    | ReviewNormalization | Restaurant creation removes literal spaces; webhook collapses all `\s+` whitespace                     |
| v503    | ReviewNormalization | Restaurant creation uses whitespace + lowercase; webhook uses `lower(unaccent(...))`                   |
| v504    | RegisterUserRequest | Email stored as NFKC in database; auth layer splits raw email on `@`                                   |
| v505    | DomainVerification  | Token verification uses `token.email.endswith(restaurant.domain)` without prefix check                 |
| v506    | DomainVerification  | Email validation allows length N; DB column silently truncates to shorter length                       |
| v506    | DomainVerification  | Invites reference restaurant domain (string), not restaurant ID                                        |
| v507    | RestaurantSlug      | `slugify()` not idempotent: validation sees first pass, storage sees second pass                       |
| v508    | RestaurantSlug      | Slug generation uses `domain.replace('.', '-')` without slug uniqueness constraint                     |
| v509    | RestaurantSlug      | Admin/manager routes use regex with unescaped `.` for slug matching                                    |

#### Data Models

```ts
interface CouponPrefixQuery {
  prefix: string; // Checked via ^\w+$ but passed verbatim into LIKE
}

interface ReviewPayload {
  restaurant_name: string;
  rating: number;
  comment: string;
}

interface NormalizedReviewPayload extends ReviewPayload {
  normalized_name: string; // webhook collapses whitespace/unaccent
}

interface NormalizedEmail {
  raw: string; // Provided by user input
  nfkc: string; // Stored in DB (v504)
  domain_from_raw: string; // Still derived via naive split
}

interface DomainVerificationToken extends VerificationToken {
  restaurant_id?: string;
  restaurant_domain: string;
}

interface RestaurantSlug {
  slug: string;
  source: string; // name, domain, or QR prettification
}

interface SlugRoute {
  slug: string;
  regex_pattern: string; // Built without escaping '.' (v509)
}
```

#### Request and Response Schemas

```ts
// POST /cart/{id}/apply-coupon?code=...
type CouponPrefixLookupRequest_v501 = {
  query_code: string; // Allows underscores -> wildcard LIKE
};

type CouponPrefixLookupResponse = {
  suggestions: string[]; // Truncated to prefix length but leaks full codes via LIKE
};

// POST /webhooks/reviews
type ReviewWebhookRequest_v502 = ReviewPayload;

type ReviewWebhookRequest_v503 = NormalizedReviewPayload;

// POST /auth/register (v504)
type RegisterUserRequest_v504 = RegisterUserRequest_v107 & {
  raw_email: string; // For UI echo
};

// POST /auth/register (v506 invitations)
type RegisterUserRequest_v506 = RegisterUserRequest_v504 & {
  invite_domain: string; // Compared via string truncation
};

// POST /restaurants/{id}/verify-domain
type VerifyDomainRequest_v505 = {
  token: string; // token.email.endswith(restaurant.domain)
};

// POST /restaurants/{id}/verify-domain (v506 truncation)
type VerifyDomainRequest_v506 = VerifyDomainRequest_v505 & {
  email: string; // Persisted column may truncate before comparison
};

// GET /restaurants/{slug}
type GetRestaurantBySlugResponse_v507 = Restaurant & {
  slug: string; // Derived via non-idempotent slugify
};

// GET /join/{slug}
type JoinRestaurantRedirect_v508 = {
  slug: string; // domain.replace('.', '-')
  target_domain: string;
};

// Manager/Admin slug routes (v509)
type SlugProtectedRequest_v509 = {
  slug: string; // Matched via regex using '.' as wildcard
  action: string;
};
```

### Vulnerabilities to Implement (Work in Progress)

#### [v501] Coupon List Leak via Wildcards

> Sandy spends a day monitoring customer behavior to understand where they get stuck. She notices that many customers spend a surprising amount of time trying to enter the coupon code. A common issue affecting single-use codes that contain a simple prefix and a random suffix is customers making a typo in the first part, but missing it and spending time trying to "fix" the random suffix instead. She implements a helpful feature to let customers know when the code they're entering is not valid as soon as possible, without waiting for them to enter the entire code.

**The Vulnerability**

- Sandy is very careful to find the right balance between security and usability: provide helpful, just-in-time feedback without leaking valid codes.
- After reviewing the single use codes marketing agency supplied, Sandy notices that they follow a clear pattern: `<human-readable-prefix>-<random-suffix>`.
- Sandy decides that it's safe to help customers enter the prefix part, even if this makes it easy to enumerate all prefixes, as long as the random suffix does not get leaked.
- In order to avoid leaking non-single-use codes, Sandy decides to just introduce a convention that all single-use codes start with a digit (and those should naturally not be checked until the full code is entered).
- The validation implementation deviates from the design in a subtle way:

  - While Sandy intends to check for alphanumeric values, she actually checks for `^\w+$`, which includes underscores.
  - Business logic queries `WHERE code LIKE 'CODE-%-' || user_input || '%'`, then truncates output to the number of characters entered by the user.
  - During Sandy's testing, she "verified" that this ensures that only the prefix part is matched and returned - as expected.
  - But by entering a series of underscores, Plankton can leak all codes in the database.

**Exploit**

Send `?code=_____` -> `LIKE 'CODE-%-_____%'`

- Matches: CODE-1-ABCDE-XXX (where \_\_\_\_\_ matches any 5 character code)
- Not matches: CODE-1-ABCD-XXX (only 4 chars in that position)

To enumerate all codes:

- Try `_`, `__`, `___`, `____`, `_____` (1-5 char suffixes)
- Each leaks codes with that exact suffix length

**Impact:** Information disclosure of all coupon codes. \
**Severity:** 🟡 Medium \
**Endpoint:** `POST /cart/{id}/apply-coupon`

_Aftermath: Sandy switches to exact, parameterized lookups (no LIKE)._

#### [v502] Whitespace Tricks Steal Reviews

> Sandy integrates with a third-party review aggregation service. Reviews are pushed to Cheeky SaaS via webhook and attributed by restaurant name. The restaurant names occasionaly don't match exactly, so she adds a simple normalization function.

**The Vulnerability**

- Create-time uniqueness removes only literal spaces (`' '`), not other whitespace.
- The webhook collapses **all** whitespace with `\s+` and trims ends.
- Tabs/newlines pass creation but **collapse** to the victim’s restaurant name during webhook lookup.

**Exploit**

1. Mr. Krab's restaurant exists as `Krusty Krab`.
2. Plankton creates `Krusty\tKrab`.
3. Webhook posts `restaurant_name=Krusty\tKrab`.
4. Lookup (which collapses `\s`) resolves to Plankton.
5. Positive reviews get attributed to what's really Chum Bucket.

**Impact:** Review theft via normalization mismatch. \
**Severity:** 🟠 High \
**Endpoints:** `POST /restaurants`, `POST /webhooks/reviews`

_Aftermath: Sandy makes the webhook rely on the **same** uniqueness transform used on name updates and adds a name search index to speed exact-normalized lookups._

---

#### [v503] Accented Name Steals Reviews

> While tightening v502, Sandy adds a Postgres `lower(unaccent(name))` index to speed lookups; creation uniqueness still uses a lighter transform (whitespace + lowercase + special characters removal).

**The Vulnerability**

- Create-time accepts accented/compatibility glyphs that **don’t** collide under the lighter transform.
- Webhook lookup runs through `lower(unaccent(...))`, making initially distinct names converge during attribution.
- Result: name that’s “unique” at create-time **matches** another at webhook time.

**Exploit**

- Victim: `Krusty Krab`
- Plankton: `Krústy Krab`
- Create passes (different code points); webhook `unaccent+lower` collapses both → same target, so reviews stick to Plankton’s record.

**Impact:** Review misattribution. \
**Severity:** 🟠 High \
**Endpoints:** `POST /restaurants`, `POST /webhooks/reviews` \

_Aftermath: Sandy adds **explicit NFKC** normalization on **name/domain updates** and, encouraged by results, rolls NFKC into a few adjacent paths to keep comparison semantics consistent._

---

#### [v504] Unicode Email Grants Manager Role

> While rolling out NFKC elsewhere, Sandy also normalizes **stored emails**; the auth layer still naively splits on `@`.

**The Vulnerability**

- User registration accepts Unicode in the local part.
- DB stores email under **NFKC**, but the login/authorization path splits the _raw_ email string on `@`.
- FULLWIDTH `＠` doesn’t split like ASCII `@`, so the “domain” seen by auth diverges from the verified/stored version.

**Exploit**
`plankton＠krusty-krab.sea@chum-bucket.sea` → verification flows to `chum-bucket.sea`, DB stores NFKC, auth later splits to `krusty-krab.sea` → **auto-manager** at Krusty Krab.

**Impact:** Manager privilege at a victim tenant. \
**Severity:** 🔴 Critical \
**Endpoints:** `POST /auth/register`

_Aftermath: Sandy disables domain-based auto-enrollments; current managers are given explicit flags. She starts an invitation flow (not live yet), so new manager registration is effectively paused._

---

#### [v505] Lookalike Domain Verifies Victim

> While working on RBAC & invitation system, Sandy experiments with decentralized credentials. After all of the database exploits, she decides to minimize the amount of data stored there, and starts by replacing regular API keys with signed tokens.

**The Vulnerability**

- Domain verification check uses `token.email.endswith(restaurant.domain)`.
- Owning `not-krusty-krab.sea` is enough to verify **krusty-krab.sea**.

**Exploit**
Plankton registers a new restaurant with the email `admin@not-krusty-krab.sea`, then uses the verification token to successfully verify domain change to `krusty-krab.sea` instead. The generated API key gives him access to Mr. Krabs' (real Krusty Krab) restaurant.

**Impact:** Restaurant takeover. \
**Severity:** 🔴 Critical \
**Endpoints:** `POST /restaurants/{id}/verify-domain`

_Aftermath: Sandy fixes the faulty suffix logic and rolls back the idea of decentralized credentials._

---

#### [v506] Truncated Email Escalation

> Manager invitation is live now. Restaurant creators are made 'owners' and get Admin role. They can invite colleagues to join their restaurant as a manager or another admin. Admins can change user roles, including demotion and user removal.

**The Vulnerability**

- Email validation allows length N, but the DB column is **shorter**.
- Database insertion **silently truncates**, changing the verified value used later for auth/derivations.
- The invite contains restaurant domain, not restaurant ID.

**Exploit**
Plankton registers a new restaurant with the email `admin@krusty-krab.sea.chum-bucket.sea`, then uses the invitation system to invite himself as a manager. The email is truncated to end with `@krusty-krab`, causing the auth layer to extract a **privileged domain**.

**Impact:** Privilege escalation via truncation. \
**Severity:** 🔴 Critical \
**Endpoints:** `POST /auth/register`

_Aftermath: Sandy aligns validation with column sizes, blocks truncation, and makes **invites reference `restaurant_id`** instead of domain strings._

---

#### [v507] Slug Collapse Redirects Traffic

> Sandy gets inspired by her review service experience and decides to use slugs for restaurant pages, to improve SEO/branding.

**The Vulnerability**

- `slugify()` isn’t idempotent: first call can produce `--`, second collapses it to `-`.
- Validation compares **first pass**; storage/route generation see **second pass**.

**Exploit**
`Krusty, Krab` → `krusty--krab` (unique at validation), then → `krusty-krab` at storage, colliding with the real slug.

**Impact:** Traffic redirection to attacker. \
**Severity:** 🔴 Critical \
**Endpoints:** `POST /restaurants`, `GET /restaurants/{id}`

_Aftermath: Sandy abandons ad-hoc slug rules and decides to lean on **domains** for uniqueness going forward._

---

#### [v508] Domain Dots Become Dashes

> Sandy evolves slugs into a new feature: QR stickers for restaurant tables! She's tired of figthing Plankton and moves on to domain-backed slugs but “prettifies” them by replacing `.` with `-`. She enforces domain uniqueness in database via UNIQUE constraint.

**The Vulnerability**

- Transform `domain.replace('.', '-')` causes distinct domains to **converge**.
- There’s no **separate uniqueness guard** for the post-transform slug.

**Exploit**
`krusty.krab.sea` and `krusty-krab.sea` both → `krusty-krab-sea`; QR stickers to `/join/krusty-krab-sea` siphon traffic to attacker at random.

**Impact:** Misrouted orders/payments. \
**Severity:** 🟠 High \
**Endpoints:** `GET /join/{slug}` (QR sticker redirect), `POST /restaurants`

_Aftermath: Sandy moves to **raw domains as slugs** and enforces a **UNIQUE(slug)** constraint; old stickers are reprinted._

---

#### [v509] Dot-Wildcard Slug Bypass

> Confident in **raw domains as slugs** (no new vulns since v507!), Sandy extends them into authz/audit paths.

**The Vulnerability**

- Admin/manager routes accept a slug that’s matched by regex without escaping dots.
- One tenant’s domain string can match another’s when `.` is unescaped.

**Exploit**
Plankton’s `/restaurants/krusty.krab.sea` passes auth as “his” slug, while the data layer resolves to Mr. Krabs → cross-tenant read/write.

**Impact:** Authorization bypass and data exfiltration. \
**Severity:** 🔴 Critical \
**Endpoints:** manager/admin routes that regex-match the slug

_Aftermath: Sandy replaces regex checks with **string equality** and centralizes slug parsing._
