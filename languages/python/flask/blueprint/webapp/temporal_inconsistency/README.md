# Temporal Inconsistency

Security decisions are made at a specific point in time. If an application checks a condition and acts on it later without protecting the time gap between them, concurrent requests or retries can invalidate the original assumption. This category covers time-of-check vs time-of-use races, missing idempotency protections, and other timing-related vulnerabilities.

## How to spot it
- Trace whether data used by a guard can change before the action completes.
- Add tests that issue the same request twice in parallel to see if side effects duplicate.
- Favor atomic database operations or idempotency keys when mutations matter.

## Subcategories
- [TOCTOU Checks](toctou-checks/) - Separating validation from action with mutable state in between.
- [Races & Missing Synchronization](races-missing-sync/) - Parallel requests that clobber shared data without locks.
- [Idempotency & Replay](idempotency-and-replay/) - Repeated delivery of the same intent produces duplicate side effects.
- [Cache Coherence & Keying](cache-coherence-and-keying/) - Stale or shared caches that serve the wrong user's data after an update.
