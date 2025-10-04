# Cache and Edge Trust
Application code assumes a cache or CDN enforced auth or applied correct keying, but it didn't—causing private data to leak due to misplaced trust.
## Overview

This is a **trust boundary error**: your code assumes infrastructure (cache, CDN, WAF) already validated something—auth, rate limiting, per-user keying—and proceeds without checking. The app treats cached responses or forwarded requests as if a trusted component filtered them, but that component either didn't have the rule configured, or the rule was bypassed. Unlike semantic mismatches where both components are "correct" per their logic, here the app is **trusting** the cache to have done work it didn't do.

**Contrast with [Cross-Component > Cache-Key Canonicalization](../../cross-component-semantics/cache-key-canonicalization/)**: That category covers **semantic disagreement** on what makes responses unique. This category covers **trusting** the cache to have enforced security policy.

**Practice tips:** - Add `Vary` headers or cache-busting tokens for any response that depends on cookies or auth headers. - Validate that edge rules match app rules during deployments and incident response drills. - Keep security-critical checks in application code; treat the edge as a bonus layer, not the final authority.
