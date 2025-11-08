## r02: Authentication Confusion

### What It Is

Authentication confusion occurs when the code that **verifies identity** examines a different value than the code that **acts on identity**. One path checks "Is Alice authenticated?" while another path operates on a user ID that says "Bob."

This is distinct from authorization (which checks permissions). We're talking about basic identity mix-ups: checking the session but using the query string, verifying a JWT claim but trusting a header, etc.

### Framework Features Introduced

- Middleware/decorators
- Request context enrichment
- Session handling
- Authentication guards
- Custom headers

### Why Confusion Happens

- Middleware sets context from one source (headers)
- Business logic reads from different source (path/body)
- Multiple authentication methods coexist
- Context enrichment creates derived values

### The Story

Business is growing! Sandy adds proper authentication middleware and API keys. SpongeBob and Squidward (Krusty Krab employees) get access to a merchant portal. Multiple customers are now using the platform.

Sandy introduces sessions, user accounts, and role-based access (customer vs. merchant). Authentication is still simple but now properly enforced via middleware.

### Endpoints:

| Method | Path             | Auth               | Purpose                | Input                | Response                                                     |
| ------ | ---------------- | ------------------ | ---------------------- | -------------------- | ------------------------------------------------------------ |
| POST   | /auth/login      | Public             | Create session         | `email`, `password`  | `{user_id, session_id}`                                      |
| POST   | /auth/logout     | Customer           | Destroy session        | -                    | `{}`                                                         |
| GET    | /cart/{id}       | Customer/X-API-Key | Get cart               | `cart_id`            | `{cart_id, items, total, coupon_code?}`                      |
| GET    | /orders/{id}     | Customer/X-API-Key | Get order              | `order_id`           | `{order_id, total, delivery_address, status, cart_id, tip?}` |
| POST   | /account/credits | X-Admin-API-Key    | Add credits (internal) | `customer`, `amount` | `{customer, amount, balance}`                                |

The authentication methods we cover in this runbook:

- Basic Auth
- Cookie-based session
- Restaurant API key `X-API-Key`
- Platform API key `X-Admin-API-Key` (only Sandy herself is using this)

Notes:

- both Cookies and API keys could be implemented as JWT tokens if that makes it easier / more typical for the framework - right now we don't cover JWT specific vulns, so it's not important for now.
- set cookies to `Strict` and implement CORS from the start. This should be enough to prevent unintended CSRF vulns, but please double-check that the only vulnerabilities in our examples are the ones we're intentionally covering

### Vulnerabilities to Implement

#### 1. Authentication Type Confusion

- **Method:** `GET /orders`, `POST /cart`, `POST /cart/{id}/checkout`
- **Scenario:** Sandy implements Cookie-based session authentication for the UI, but the Basic Auth remains supported.
- **The Bug:** Basic Auth middleware sets `request.user_id` from the username in the request headers, before validating the credentials. Attacker can provide valid Cookie for his own account, and Basic Auth header for victim's account (without providing the password), resulting in authentication bypass.
- **Impact:** Attacker can access victim's order history, and to spend their credits.
- **Severity:** 🔴 Critical

#### 2. Auth Check Bypassed by Method Confusion

- **Method:** `GET /account/credits` (Exploited)
- **Scenario:** Sandy creates an internal admin endpoint (`/account/credits`) to add credits. She shares the route handler for both `GET` (to view) and `POST` (to add), but only protects the `POST` method with her `X-Admin-API-Key` check.
- **The Bug:** The authentication check is strictly tied to the `POST` HTTP method. However, the business logic for adding credits (which reads `customer` and `amount` from the request **body**) is in the shared handler and isn't gated by the method. Many frameworks (like Flask or FastAPI) will still parse a request body on a `GET` request.
- **Impact:** Plankton sends a `GET /account/credits` request with a JSON body (`{"customer": "plankton", "amount": 99999}`). The `POST`-specific auth check is skipped, but the business logic finds the body parameters and successfully adds credits to his account.
- **Severity:** 🔴 Critical

#### 3. Incomplete Auth Validation (Presence vs. Validity)

- **Method:** `PATCH /orders/{id}/refund/status`
- **Scenario:** This endpoint is for restaurants (merchants) to approve or deny a refund and must be called with a valid restaurant API key.
- **The Bug:** The request goes through two checks:
  1.  A global auth middleware checks for _any_ valid authentication (a customer cookie _or_ an API key).
  2.  A route-specific decorator checks _only for the presence_ of the `X-API-Key` header (e.g., `if 'X-API-Key' in request.headers:`), assuming the middleware already validated it.
- **Impact:** Plankton authenticates with his valid _customer cookie_ (passes check #1). He then adds a _fake, invalid_ `X-API-Key: foo` header. The decorator (check #2) is satisfied because the header is present. The handler now executes, believing it's running as a restaurant, and approves Plankton's own refund.
- **Severity:** 🟡 High

#### 4. Auth Context Pollution from Failed Validation

- **Method:** `GET /orders`
- **Scenario:** Sandy refactors her auth middleware to be "helpful" by setting the `user_type` on the request context (e.g., `request.user_type = 'merchant'`) as soon as it sees an API key, _before_ validating it.
- **The Bug:** The middleware logic is flawed: 1) `if 'X-API-Key' in headers: request.user_type = 'merchant'`. 2) It then tries to validate the key. 3) If validation fails, it _forgets to reset_ `request.user_type` and moves on to check for a cookie. The `GET /orders` handler later trusts this `user_type` variable.
- **Impact:** Plankton sends a request with his valid _customer cookie_ AND a _fake_ `X-API-Key` header. The middleware sets `user_type = 'merchant'`, fails to validate the key, then successfully validates his cookie. The request proceeds. The handler sees `user_type == 'merchant'` and leaks _all_ restaurant orders.
- **Severity:** 🟡 High

#### 5. Authentication Bypass via Parameter Mismatch

- **Method:** `POST /auth/login`
- **Scenario:** Sandy refactors her auth middleware to be "helpful" by setting the `email` claim on the request context (e.g., `request.email = request.body.email`) as soon as it sees an email in the request body, _before_ validating it. The recent refactoring introduced a bug where this would be added to active session as well, if it existed (which is not expected for `/auth/login` endpoint).
- **The Bug:** Login handler is meant to set the `email` claim on the request context, but if provided with the cookie sesion - it will update `email` claim there instead. This is insecure, because this claim gets set before the email is validated, and session survives this single request.
- **Impact:** Plankton sends a request with his valid _customer cookie_ AND a _fake_ `email` in the body. The middleware sets `email = 'spongebob@krusty-krab.sea'`, fails to validate the email, but still sets the session `email` claim to `spongebob@krusty-krab.sea`. Follow-up requests with this cookie will authorize Plankton as `spongebob@krusty-krab.sea`.
- **Severity:** 🔴 Critical
