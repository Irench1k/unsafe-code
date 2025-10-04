# Unsafe Defaults and Misconfiguration

This category focuses on **configuration mistakes**: development settings shipped to production, insecure defaults not changed, or deployment-specific values (like trusted proxy IPs) set incorrectly. These misconfigurations don't directly cause vulnerabilities—they **enable** them by making trust boundary errors exploitable, allowing weak crypto, or opening CORS/CSRF attack surface. The code may be trying to do the right thing, but the config tells it to trust the wrong sources or use weak values.

**Key distinction**: This is about **configuration errors** (settings files, environment variables, framework defaults). The **code patterns** that rely on these settings (like reading `X-Forwarded-*` headers or checking scheme) are covered in [Trust Boundary Errors](../trust-boundary-errors/). Think of it this way: Trust Boundary shows the vulnerable code; Unsafe Defaults shows the config mistakes that make it exploitable.

## How to spot it
- Audit environment variables and config files for placeholders or obvious defaults.
- Confirm any proxy or host trust settings match the real deployment topology.
- Treat CORS, HTTPS, and "secure" cookie flags as explicit decisions with tests, not silent defaults.

## Subcategories
- [Secret & Key Defaults](secret-and-key-defaults/) — Session secrets, signing keys, or crypto values left at development defaults or sample values, allowing attackers to forge tokens or decrypt data.
- [Host & Proxy Trust](host-and-proxy-trust/) — Proxy trust middleware (like `ProxyFix`) enabled globally or without IP allowlists, letting attackers inject forwarded headers without validation.
- [CORS & Scheme](cors-and-scheme/) — Incorrect `PREFERRED_URL_SCHEME`, permissive CORS origins, or wrong assumptions about TLS termination that enable CSRF or credential leakage.
