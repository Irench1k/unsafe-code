# Temporal Inconsistency

Security decisions are made at a specific point in time. If an application checks a condition and acts on it later without protecting the time gap between them, concurrent requests or retries can invalidate the original assumption. This category covers time-of-check vs time-of-use races, missing idempotency protections, and other timing-related vulnerabilities.

## Running the Examples

All examples in this category share a single Docker Compose environment:

```bash
cd vulnerabilities/python/flask/temporal_inconsistency
docker compose up -d

# View logs
docker compose logs -f

# Stop and clean up
docker compose down
```

The application will be available at `http://localhost:8000/temporal-inconsistency/`.

## How to spot it
- Trace whether **data used by a guard can change** between validation and use. Check-then-act sequences with mutable shared state (balance, inventory, permissions) are especially vulnerable to race conditions.
- Add tests that **issue the same request twice in parallel** to see if side effects duplicate (double withdrawals, double credits, duplicate messages) or if the second request sees stale authorization decisions.
- Look for **non-atomic operations** where validation, calculation, and persistence happen in separate database queries or cache lookups without transactions or optimistic locking.
- Favor **atomic database operations** (UPDATE with WHERE constraints, UPSERT with conflict handling) or **idempotency keys** when mutations matter, especially for financial transactions or irreversible actions.
- Check whether **caches or memoized values** are invalidated correctly after state changes. Stale cached authorization decisions or user context can allow access long after permissions are revoked.

## Subcategories

- [TOCTOU Checks](webapp/toctou_checks/) — Separating validation from action with mutable state in between, allowing concurrent requests to invalidate the original check.
- [Races & Missing Synchronization](webapp/races_missing_sync/) — Parallel requests that clobber shared data without locks, transactions, or optimistic concurrency control.
- [Idempotency & Replay](webapp/idempotency_and_replay/) — Repeated delivery of the same intent produces duplicate side effects due to missing deduplication or replay protection.
- [Cache Coherence & Keying](webapp/cache_coherence_and_keying/) — Stale or shared caches that serve the wrong user's data after an update, or cache keys that don't capture all security-relevant context.
