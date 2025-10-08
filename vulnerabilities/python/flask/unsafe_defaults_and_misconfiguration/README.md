# Unsafe Defaults and Misconfiguration

This category focuses on **configuration mistakes**: development settings shipped to production, insecure defaults not changed, or deployment-specific values (like trusted proxy IPs) set incorrectly. These misconfigurations don't directly cause vulnerabilities—they **enable** them by making trust boundary errors exploitable, allowing weak crypto, or opening CORS/CSRF attack surface. The code may be trying to do the right thing, but the config tells it to trust the wrong sources or use weak values.

**Key distinction**: This is about **configuration errors** (settings files, environment variables, framework defaults). The **code patterns** that rely on these settings (like reading `X-Forwarded-*` headers or checking scheme) are covered in [Trust Boundary Errors](../trust_boundary_errors/). Think of it this way: Trust Boundary shows the vulnerable code; Unsafe Defaults shows the config mistakes that make it exploitable.

## Running the Examples

**Important**: Unlike other vulnerability categories, each subcategory in Unsafe Defaults and Misconfiguration has its own Docker Compose environment because they demonstrate different configuration scenarios:

- **Secret & Key Defaults** demonstrates Flask with weak cryptographic configuration (default SECRET_KEY, weak signing algorithms)
- **Host & Proxy Trust** requires reverse proxy setups to demonstrate ProxyFix misconfiguration with and without IP allowlists
- **CORS & Scheme** may include TLS termination proxies to demonstrate scheme detection issues and CORS origin validation

Navigate to the specific subcategory directory and start its environment:

```bash
# Example: Running Secret & Key Defaults examples
cd vulnerabilities/python/flask/unsafe_defaults_and_misconfiguration/secret_and_key_defaults
docker compose up -d

# View logs
docker compose logs -f

# Stop and clean up
docker compose down
```

Each subcategory's README provides specific instructions for its infrastructure setup and available endpoints.

## How to spot it

- **Audit configuration sources**: Review every environment variable, config file, and framework default used by the application. Look for placeholders (`SECRET_KEY='changeme'`), obvious defaults (`'dev'`, `'localhost'`), or empty strings where values should be set.
- **Verify deployment-specific settings match topology**: Confirm proxy trust settings (`ProxyFix` IP allowlists), CORS origins, and trusted host lists reflect the actual infrastructure—not copied from examples or set to wildcard values.
- **Treat security flags as explicit decisions**: Settings like `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY`, `PREFERRED_URL_SCHEME`, and CORS configurations should be consciously set with tests verifying behavior, not left to defaults or guessed.
- **Separate development from production config**: Ensure development-mode settings (debug enabled, permissive CORS, weak keys) are never deployed to production. Use environment-specific config files or validation that fails fast on startup if production settings are missing.
- **Test crypto and signing operations**: For session secrets and signing keys, verify that changing the value invalidates old tokens/sessions—proving the key is actually used and not silently ignored or supplemented by a hardcoded fallback.

## Subcategories

- [Secret & Key Defaults](secret_and_key_defaults/) — Session secrets, signing keys, or crypto values left at development defaults or sample values, allowing attackers to forge tokens or decrypt data.

- [Host & Proxy Trust](host_and_proxy_trust/) — Proxy trust middleware (like `ProxyFix`) enabled globally or without IP allowlists, letting attackers inject forwarded headers without validation.

- [CORS & Scheme](cors_and_scheme/) — Incorrect `PREFERRED_URL_SCHEME`, permissive CORS origins, or wrong assumptions about TLS termination that enable CSRF or credential leakage.
