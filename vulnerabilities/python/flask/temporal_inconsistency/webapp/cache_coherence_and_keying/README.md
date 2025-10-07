# Cache Coherence and Keying

Caches that ignore user identity or forget to expire stale entries can undo security fixes moments after you apply them.

## Overview

Flask apps often rely on Redis or CDN caches to speed up personalized pages. If the cache key omits the user or role, the first responder populates the entry and everyone else sees the same data. Likewise, failing to invalidate cached authorization decisions leaves outdated privileges in place long after a user is revoked.

**Practice tips:**
- Include user identifiers and relevant claims in cache keys or use `Vary` headers for HTTP caches.
- Invalidate caches as part of permission changes, not just data updates.
- Add monitoring for cache hit anomalies immediately after sensitive updates.
