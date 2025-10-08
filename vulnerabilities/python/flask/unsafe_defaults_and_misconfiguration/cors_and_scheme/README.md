# CORS and Scheme Misconfiguration

Configuration sets wrong `PREFERRED_URL_SCHEME`, permissive CORS allowlists, or missing proxy config, enabling credential leakage and CSRF.

## Overview

This is a **configuration mistake**: setting `PREFERRED_URL_SCHEME` incorrectly when TLS terminates upstream, copying dev `ALLOWED_ORIGINS` lists to production, or enabling `supports_credentials=True` with permissive CORS rules. These misconfigurations **enable** trust boundary errors by making the framework misunderstand the deployment topology (thinking HTTP when it's HTTPS) or allowing browsers to send credentials to attacker origins.

**Contrast with [Trust Boundary > Origin & Scheme Assertions](../../trust_boundary_errors/origin_scheme_assertions/)**: That category covers the **code pattern** of trusting scheme/origin values. This category covers the **config mistakes** that make those values incorrect or too permissive.

**Practice tips:**
- Tie CORS allowlists to deployment configs and review them alongside firewall changes.
- Require HTTPS verification before enabling secure cookies or redirect logic.
- Validate scheme and origin behavior with integration tests that simulate hostile origins.
