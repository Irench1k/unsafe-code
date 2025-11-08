## r05: Normalization Issues

### What It Is

Character normalization confusion happens when two code paths apply **different string transformations** to the same logical input. One path might lowercase, the other might not. One might strip whitespace, the other might only trim. One might apply Unicode normalization, the other might ignore it.

Result: values that should be "equal" diverge when checked vs. used, bypassing uniqueness constraints, access controls, or security boundaries.

### Framework Features Introduced

- String manipulation
- Database constraints
- Text search/indexes
- Regular expressions
- Unicode handling

### Why Confusion Happens

- Different normalization in different layers
- Database does normalization automatically
- Case-insensitive vs case-sensitive comparisons
- Regex special characters
- Unicode normalization mismatches

### The Story

The platform is getting popular beyond Bikini Bottom! Sandy adds a review system, custom domains for restaurants, and public restaurant pages with human-readable URLs (slugs).

Plankton is relentless. He exploits every normalization bug to hijack Krusty Krab's reviews, steal their subdomain, and confuse customers into visiting his copycat restaurant.

### Endpoints:

| Method | Path                               | Auth       | Purpose                      | Input          | Response                                | Changes  |
| ------ | ---------------------------------- | ---------- | ---------------------------- | -------------- | --------------------------------------- | -------- |
| POST   | /restaurants                       | Restaurant | Create restaurant            | `name`, `slug` | `{restaurant_id, name, slug}`           | NEW      |
| GET    | /restaurants                       | Public     | List restaurants             | -              | `[{restaurant_id, name, slug}]`         | NEW      |
| PATCH  | /restaurants/{slug}                | Restaurant | Update restaurant info       | `name`, `slug` | `{restaurant_id, name, slug}`           | MODIFIED |
| GET    | /restaurants/{slug}                | Public     | Get restaurant info          | `slug`         | `{restaurant_id, name, slug}`           | NEW      |
| GET    | /restaurants/{slug}/menu           | Public     | Get restaurant menu          | `slug`         | `[{item_id, name, price}]`              | NEW      |
| GET    | /restaurants/{slug}/orders         | Public     | Get restaurant orders        | `slug`         | `[{order_id, customer, total, status}]` | NEW      |
| GET    | /restaurants/{slug}/coupons        | Public     | Get restaurant coupons       | `slug`         | `[{coupon_id, code, discount_percent}]` | NEW      |
| GET    | /restaurants/{slug}/reports/orders | Public     | Get restaurant orders report | `slug`         | `CSV`                                   | NEW      |
| PATCH  | /restaurants/{slug}                | Restaurant | Update restaurant info       | `name`, `slug` | `{restaurant_id, name, slug}`           | MODIFIED |
| DELETE | /restaurants/{slug}                | Restaurant | Delete restaurant            | `slug`         | `{restaurant_id, name, slug}`           | NEW      |

### Vulnerabilities to Implement

#### 1. Coupon Code Leak: Validation Pattern vs SQL Wildcard

**Endpoint(s):** `POST /v501/cart/{id}/apply-coupon`

**Setup:**
Sandy implements coupon validation. Codes must be alphanumeric. Database stores coupons with format `{restaurant_id}_{code}`, e.g., `1_BURGER20`.

**The Vulnerability:**

- Validation checks form parameter: `if re.match(r'^[A-Z0-9]+$', body.code): pass`
- Database query uses query parameter: `SELECT * FROM coupons WHERE code LIKE '{restaurant_id}_{query.code}%'`

_Note: If the framework makes `%` injection unlikely due to auto-escape, collect all the coupon codes 'for caching purposes' and match them using regex (replacing `%` in the attack with `.*`)_

**Attack Scenario:**

1. Krusty Krab has coupons: `1_BURGER20`, `1_BURGER50`, `1_BURGERMANIA`
2. Plankton sends: `POST /v501/cart/5/apply-coupon?code=%` with form data: `code=BURGER20`
3. Validation checks form data: `BURGER20` ✓ (alphanumeric)
4. Database searches: `LIKE '1_%'` (wildcard matches all restaurant 1 coupons)
5. Query returns multiple rows, exception reveals all codes in error message

**Root Cause:**
Validation operates on one input source (form), SQL query uses different source (query param), SQL wildcards not escaped.

**Impact:**
Information disclosure - leaking all restaurant coupon codes via error messages.

**Severity:** 🟡 Medium

**Framework Translation Notes:**

- SQL wildcards: `%`, `_` in LIKE clauses
- ORM query building: some auto-escape, others require explicit escaping
- Error message exposure varies by framework debug settings

#### 2. Domain Extraction from Email

**Endpoint(s):** `GET /v502/restaurants/{id}/settings`

**Setup:**
Sandy implements a "manager by domain" feature. If your email is `employee@krusty-krab.sea`, you automatically have manager access to any restaurant with domain `krusty-krab.sea`.

**The Vulnerability:**
Session contains `email` field. Middleware extracts domain by splitting on `@` and taking the second part: `session.domain = email.split('@')[1]`. Authorization checks if this domain matches the restaurant's domain.

**Attack Scenario:**

1. Plankton registers new user with email `plankton＠krusty-krab.sea@chum-bucket.sea` (the first character is `FULLWIDTH COMMERCIAL AT` / `U+FF20` – NOT regular `@` sign)
2. Email validation recognizes `chum-bucket.sea` as the email's domain
3. When storing the email in the session, the framework or database layer normalizes it (NFKC) to `plankton@krusty-krab.sea@chum-bucket.sea` (now both @ signs are the same)
4. Upon login, the middleware extracts `session.email = "plankton@krusty-krab.sea@chum-bucket.sea"`, based on which the domain is retrieved as `session.domain = "krusty-krab.sea"` and Plankton is granted manager access to Krusty Krab restaurant.

**The Vulnerability:**
Middleware extracts domain by: `domain = email.split('@')[1]` (takes second element, not last element). This assumes that the email has been validated on registration, however the normalization step was performed AFTER the email was validated!

**Root Cause:**
Naive email parsing that doesn't account for normalization steps that are performed after the email is validated.

**Impact:**
Complete account takeover of any restaurant by registering crafted email addresses.

**Severity:** 🔴 Critical

**Framework Translation Notes:**

- Email validation varies widely (regex vs library vs framework built-in)
- Some validators normalize, others preserve exact format
- String splitting is universal but implementation might use `rsplit`, `split(..., 1)`, regex
- Test what email formats your framework's validator accepts

#### 3. Privilege Escalation: Database Truncation

**Endpoint(s):** `POST /v503/auth/register`

**Setup:**
Sandy implements email verification. Certain domains (e.g., `@krusty-krab.sea`) are privileged – users with those domains are automatically considered managers.

**The Vulnerability:**

Validation path sends the email verification token to the email address.

Registration path inserts the user into the database without checking for the length of the email address.

**Attack Scenario:**

1. Database email column is `VARCHAR(50)`
2. Plankton registers: `long-prefix-xxxxxxxxxxxxxxxxxx@krusty-krab.sea.chum-bucket.sea`
3. Validation path sends the email verification token to the email address.
4. Plankton receives the email (as it arrives to the subdomain under his control)
5. Plankton verifies the email address and completes the registration form.
6. Registration path inserts the user into the database, causing truncation of the email address to `long-prefix-xxxxxxxxxxxxxxxxxx@krusty-krab.sea`
7. Plankton knows password and can login as a manager for Krusty Krab.

**Root Cause:**
Validation operates on full string, database silently truncates.

**Impact:**
Privilege escalation - registering as manager for Krusty Krab.

**Severity:** 🔴 Critical

#### 4. Review Theft: Case Sensitivity

**Endpoint(s):**

- `POST /v504/restaurants` (creation with uniqueness check)
- `POST /v504/webhooks/reviews?restaurant_name={name}`

**Setup:**
Sandy integrates a review aggregation service. Reviews are attributed by restaurant name. She enforces unique restaurant names during creation.

**The Vulnerability:**
Creation endpoint checks uniqueness: `Restaurant.query.filter_by(name=name).first()` (case-sensitive)

Webhook looks up: `Restaurant.query.filter(Restaurant.name.ilike(name)).first()` (case-insensitive)

**Attack Scenario:**

1. Krusty Krab exists with name `Krusty Krab`
2. Plankton creates restaurant: `KRUSTY KRAB` (passes uniqueness check - different case)
3. Review service sends webhook: `POST /webhooks/reviews?restaurant_name=krusty%20krab`
4. Webhook looks up case-insensitively, finds two restaurants
5. Reviews attributed to the first restaurant (time descending order)
6. Plankton's restaurant receives Krusty Krab's positive reviews

**Root Cause:**
Uniqueness enforcement is case-sensitive, lookup is case-insensitive, creating collision opportunity.

**Impact:**
Review theft - hijacking another restaurant's reputation.

**Severity:** 🟡 Medium

**Framework Translation Notes:**

- Database collation: some databases are case-insensitive by default (MySQL), others case-sensitive (PostgreSQL)
- ORM query methods: `.filter()`, `.filter_by()`, `.ilike()`, `.lower()`
- Index case-sensitivity affects lookups
- Framework may normalize strings in validation but not in queries

#### 5. Review Theft: Whitespace Normalization

**Endpoint(s):**

- `PATCH /v505/restaurants/{id}` (update with normalization)
- `POST /v505/webhooks/reviews?restaurant_name={name}`

**Setup:**
Sandy fixes the case sensitivity issue by normalizing both sides: `name.lower().strip()`. She updates both endpoints to normalize consistently.

**The Vulnerability:**
Update endpoint strips: `name.lower().replace(r' ', '')` (removes space only)
Webhook strips differently: `name.lower().replace(r'\s', '')` (removes ALL whitespace via regex)

**Attack Scenario:**

1. Krusty Krab has name `Krusty Krab` (with space)
2. Plankton updates his restaurant to: `Krusty Krab\t` (with tab character `\t`)
3. Update normalization: `'Krusty Krab\t'.lower().replace(r' ', '') = 'krustykrab\t'`
4. Uniqueness check passes (different from `krustykrab`)
5. Webhook normalization: `'krustykrab\t'.replace(r'\s', '') = 'krustykrab'` and `'krustykrab'.replace(r'\s', '') = 'krustykrab'`
6. Both normalize to the same value, Plankton hijacks reviews

**Root Cause:**
Different whitespace normalization rules - `.replace(' ', '')` vs `.replace('\s', '')` - match different whitespace classes.

**Impact:**
Review theft via whitespace exploitation.

**Severity:** 🟡 Medium

**Framework Translation Notes:**

- Whitespace characters: space, tab, newline, carriage return, etc.
- Regex `\s` matches all whitespace, `.strip()` only leading/trailing
- URL encoding of whitespace: `%20`, `%09`, `%0A`
- Framework may normalize URLs before they reach application code

#### 6. Review Theft: Unicode Normalization

**Endpoint(s):**

- `PATCH /v506/restaurants/{id}` (update with comprehensive normalization)
- `POST /v506/webhooks/reviews?restaurant_name={name}` (with database index)

**Setup:**

Sandy adds even more normalization: lowercase, trim, and validates uniqueness against all existing restaurants. The webhook uses a Postgres search index for performance: `CREATE INDEX idx_restaurant_name_searchable ON restaurants (lower(unaccent(name)))`.

**The Vulnerability:**

Application-level uniqueness check: `existing_names = [r.name.lower().replace(r'\s', '') for r in all_restaurants]; if normalized_name in existing_names: reject`

Database index for webhook: `lower(unaccent(name))` where `unaccent()` removes diacritics

**Attack Scenario:**

1. Krusty Krab has name `Krusty Krab`
2. Plankton updates his restaurant to: `Krusty Krạb` (with Vietnamese `ạ` instead of Latin `a`)
3. Application check compares: `'Krusty Krаb'` vs `'Krusty Krạb'` (different, passes)
4. Webhook searches database using `unaccent()`: both normalize to `Krusty Krab`
5. Plankton hijacks reviews

**Root Cause:**

Application logic doesn't apply same normalization as database index - missing diacritic/script removal.

**Impact:**

Review theft via Unicode exploitation.

**Severity:** 🟡 Medium

**Framework Translation Notes:**

- Unicode normalization forms: NFC, NFD, NFKC, NFKD
- Database functions: `unaccent()` (Postgres), `CONVERT()` (MySQL)
- Lookalike characters: Cyrillic vs Latin, fullwidth vs halfwidth
- Framework may have built-in Unicode normalization, but it must match database behavior

#### 7. Review Theft: Underscore Wildcard

**Endpoint(s):** `POST /v507/restaurants`

**Setup:**
Sandy is frustrated with Plankton's exploits. She implements aggressive sanitization:

1. Lowercase and trim
2. Apply NFKC normalization
3. Filter to alphanumeric with regex `\w+`
4. Database uniqueness check
5. Before insertion, remove all non-alphanumeric (except whitespace)
6. Auto-capitalize the name in UI

**The Vulnerability:**

- Validation path: Regex `\w` matches: `[A-Za-z0-9_]` (includes underscore)
- Insertion path: Non-alphanumeric filter before insertion: `re.sub(r'[^A-Za-z0-9\s]', '', name)` (removes everything except letters, numbers, spaces)

**Attack Scenario:**

1. Krusty Krab has name `Krusty Krab`
2. Plankton registers: `Krusty Krab_`
3. Sanitization: lowercase + trim + NFKC → `krusty krab_`
4. Regex validation: `\w+` matches (underscore is `\w`) ✓
5. Database check: `krusty krab_` vs `krusty krab` (unique) ✓
6. Pre-insertion filter: removes `_` → `krusty krab`
7. Database stores `krusty krab`, colliding with existing restaurant

**Root Cause:**
Inconsistent character filtering - validation allows underscore (`\w`), insertion removes it, creating collision.

**Impact:**
Review theft.

**Severity:** 🟠 High

**Framework Translation Notes:**

- Regex character classes: `\w`, `\d`, `\s` definitions vary by language/locale
- Some regex engines support Unicode character classes
- Double-sanitization patterns common in refactored code

#### 8. Slug Collision: Non-Idempotent Normalization

**Endpoint(s):** `PATCH /v508/restaurants/{slug}`

**Setup:**
Sandy replaces numeric IDs with slugs for SEO. She generates slugs from restaurant names with a helper function `slugify(name)`. Uniqueness is checked by calling `slugify()` on the new name and comparing to existing slugs.

**The Vulnerability:**
The `slugify()` helper is non-idempotent:

```python
def slugify(name):
    s = name.lower()
    s = re.sub(r'-+', '-', s)  # Collapse multiple hyphens FIRST
    s = re.sub(r'[^a-z0-9]+', '-', s)  # Replace non-alphanum with hyphens
    return s.strip('-')
```

First call: `slugify('krusty!-krab') → 'krusty--krab'`
Second call: `slugify('krusty--krab') → 'krusty-krab'` (same)

But during validation, we call it once on the existing slug. During insertion, we call it again on potentially different input.

**Attack Scenario:**

1. Krusty Krab has slug `krusty-krab`
2. Plankton registers: `krusty!-krab`
3. Validation: `slugify('krusty!-krab') = 'krusty--krab'` (unique) ✓
4. Insertion: `slugify('krusty--krab') = 'krusty-krab'` (collides) ✗

**Root Cause:**
Non-idempotent slugification + validation and insertion operating on different input fields.

**Impact:**
Slug collision, takeover of restaurant profile URLs.

**Severity:** 🟠 High

**Framework Translation Notes:**

- Slug generation libraries vary (language-specific)
- Idempotency: calling `f(f(x)) = f(x)` vs `f(f(x)) ≠ f(x)`
- Validation vs persistence field mapping

#### 9. Slug Collision: Domain to Slug Conversion

**Endpoint(s):** `POST /v509/restaurants`

**Setup:**
Sandy decides to use domain names as slugs (one slug per domain, auto-enforced uniqueness). She converts domain to slug by replacing dots with hyphens.

The idea is that since domain names are unique, and slugs are generated from domain names, slugs should be unique as well. No need to check for uniqueness again.

**The Vulnerability:**

Slug generation: `slug = domain.replace('.', '-')`

Domains `krusty.krab.sea` and `krusty-krab.sea` both produce slug `krusty-krab-sea`

**Attack Scenario:**

1. Krusty Krab has domain `krusty-krab.sea` → slug `krusty-krab-sea`
2. Plankton registers domain `krusty.krab.sea` → slug `krusty-krab-sea`

**Root Cause:**
Lossy conversion - multiple distinct inputs (domains with dots vs hyphens) map to same output (slug).

**Impact:**
Slug collision, URL confusion, profile takeover.

**Severity:** 🟠 High

**Framework Translation Notes:**

- DNS restrictions: dots are required in domains, hyphens are allowed
- Character replacement in slugs: dots, spaces, special chars → hyphens
- Reversibility: slug should ideally be convertible back to original or have separate storage

#### 10. Slug Collision: Unescaped Dots in Regex

**Endpoint(s):** `POST /v510/restaurants`

**Setup:**

Sandy is tired of Plankton's shenanigans. She decides to use domain names as slugs, without any modifications.

**The Vulnerability:**

- Even though domain names are not manged anymore, the matching logic still relies on regex, and it doesn't escape the dots in the domain names.

**Attack Scenario:**

1. Plankton registers: `krusty.krab.sea`
2. Registration succeeds
3. Plankton uses API with the slug `/restaurants/krusty.krab.sea`
4. Authorization middleware identifies Plankton's restaurant by the slug and grants access to the restaurant's resources
5. Data access layer retrieves the restaurant by the slug, and comes up with Mr. Krabs' restaurant's resources instead - authorization bypass!

**Impact:**

Authorization bypass, potential data exfiltration.

**Severity:** 🔴 Critical

#### 11. Domain Verification: String Suffix Matching

**Endpoint(s):**

- `POST /v511/restaurants`
- `PATCH /v511/restaurants/{id}/domain`

**Setup:**
Sandy implements domain ownership verification. To change a restaurant's domain, you must verify ownership by receiving an email at that domain. The system sends an email with a verification token.

**The Vulnerability:**
Verification check: `if token.email.endswith(restaurant.domain): approve`

**Attack Scenario:**

1. Krusty Krab has domain `krusty-krab.sea`
2. Plankton owns domain `not-krusty-krab.sea`
3. He starts registering a new restaurant with domain `not-krusty-krab.sea`
4. System sends verification email to `admin@not-krusty-krab.sea` (his verified email)
5. He verifies the domain change for Chum Bucket to `krusty-krab.sea`, providing the token received for `admin@not-krusty-krab.sea`
6. The domain change is approved, and Chum Bucket's domain is changed to `krusty-krab.sea`

Now when customers visit `/restaurants/krusty-krab.sea` (slug from domain), they get Plankton's restaurant instead of Krusty Krab's.

**Root Cause:**
String suffix matching without anchor - `endswith()` matches any suffix, not just after `@`.

**Severity:** 🟠 High

**Framework Translation Notes:**

- String matching: `.endswith()`, `.ends_with()`, regex `$` anchor
- Email parsing: split on `@` vs proper email validation library
- Framework may have email validation utilities, but domain extraction requires careful implementation
