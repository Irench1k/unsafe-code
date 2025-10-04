# Trust Boundary Errors

Trust boundary errors happen when **your code reads data as if a trusted component set it**, but attackers can inject that data directly. This is about **code-level trust decisions**: reading `X-Forwarded-For` for rate limiting, trusting `X-User-ID` for identity, checking `X-Forwarded-Proto` to enforce HTTPS, or assuming a cache validated authorization. The application treats these values as authoritative without verifying they actually came from infrastructure. The result: attackers spoof identity, bypass security policies, or manipulate routing and caching by injecting the headers or data your code expects from a trusted layer.

**Key distinction**: This is about **what your code trusts** (reading headers/data assuming infrastructure set them). The **configuration mistakes** that enable these bugs (like enabling `ProxyFix` globally or misconfiguring `PREFERRED_URL_SCHEME`) are covered in [Unsafe Defaults and Misconfiguration](../unsafe-defaults-and-misconfiguration/). For **protocol-level semantic disagreements** between components, see [Cross-Component Semantics](../cross-component-semantics/).

## How to spot it
- For every piece of data the app uses to make security decisions (identity, client IP, scheme, host), ask: **"Who was supposed to set this? Can an attacker set it instead?"**
- Grep for headers like `X-Forwarded-*`, `X-Real-IP`, `X-User`, `X-Auth-*`, and `Host`—then verify they're only accepted from configured trusted sources (not arbitrary clients).
- Check environment flags and config (`PREFERRED_URL_SCHEME`, `SESSION_COOKIE_SECURE`, CORS allow-lists) that assume upstream components enforce security, and verify those components actually do what the app thinks.
- Trace the **trust boundary**: which layer terminates TLS, validates identity, enforces rate limits, or caches responses? Make sure the app only trusts data from those layers and validates or strips attacker-controlled values.

## Subcategories
- [Header Authority](header-authority/) — Trusting `X-Forwarded-*`, `X-Real-IP`, or `Host` headers without verifying they came from a configured trusted proxy, letting attackers spoof client identity or routing decisions.
- [Gateway Identity](gateway-identity/) — Reading identity/auth headers (like `X-User-ID`, `X-Auth-Email`) meant to be set by an API gateway, but accepting them directly from untrusted clients.
- [Origin & Scheme Assertions](origin-scheme-assertions/) — Assuming requests are HTTPS when they're not (due to misconfigured `PREFERRED_URL_SCHEME` or trusting `X-Forwarded-Proto` without validation), or accepting attacker-controlled CORS origins.
- [Cache & Edge Trust](cache-edge-trust/) — Assuming a CDN, cache, or reverse proxy enforced authentication, applied correct per-user/per-tenant keying, or otherwise validated requests—when it didn't.
