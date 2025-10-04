# Header Authority in Flask Deployments
Code trusts `Host`, `X-Forwarded-*` headers assuming infrastructure set them, but without validation these are attacker-controlled values.
## Overview

This is a **code-level trust error**: your application reads `request.host`, `X-Forwarded-For`, `X-Forwarded-Proto`, or similar headers and treats them as authoritative for security decisions (password reset links, rate limiting, HTTPS enforcement). The code assumes infrastructure set these, but without explicit proxy trust configuration, they're attacker-controlled. The vulnerability is in **what the code reads and trusts**, not just in the config (though misconfiguration enables it).

**Contrast with [Unsafe Defaults > Host & Proxy Trust](../../unsafe-defaults-and-misconfiguration/host-and-proxy-trust/)**: That category covers the **configuration mistakes** (enabling `ProxyFix` globally, no IP allowlist) that make header injection possible. This category covers the **code pattern** of trusting headers without validation.

**Practice tips:** - Use `ProxyFix` or comparable middleware only with a whitelist of real proxy IP ranges. - Build absolute URLs from configuration, not dynamic host headers, unless you have a verified source. - Treat client IP and scheme detection as security-sensitive features worthy of tests.
