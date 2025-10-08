# Policy Composition and Precedence

Modern applications use multiple layers of security controls: blueprints, decorators, feature flags, and middleware. Vulnerabilities occur when two policies overlap and the weaker one executes last, bypassing the stronger protection that should have been enforced.

## Running the Examples

All examples in this category share a single Docker Compose environment:

```bash
cd vulnerabilities/python/flask/policy_composition_and_precedence
docker compose up -d

# View logs
docker compose logs -f

# Stop and clean up
docker compose down
```

The application will be available at `http://localhost:8000/policy-composition-and-precedence/`.

## How to spot it
- Review the **complete decorator chain and middleware order**, not just recently added guards. Execution order determines which policy "wins" when multiple overlap.
- Search for code paths that **default to "allow"** when an explicit deny would be safer. New routes, feature flags, or conditional branches may bypass existing protections.
- Check whether **nested resources inherit stricter policies** from their parents or bypass them through direct access paths.
- Trace the **full request lifecycle**: which policies execute at blueprint registration, before_request, decorator evaluation, and handler execution? Are any skipped conditionally?
- Look for **caching or memoization** of authorization decisions that may be invalidated by subsequent checks or context changes.

## Subcategories

- [Merge Order & Short-Circuit](webapp/merge_order_and_short_circuit/) — Combining permissive or caching layers with stronger guards in the wrong order allows the weaker policy to take precedence or short-circuit stricter enforcement.
- [Default-Allow Gaps](webapp/default_allow_gaps/) — New routes, feature toggles, or conditional branches that are deployed without security protection, leaving unguarded paths to protected resources.
- [Scope Mismatch](webapp/scope_mismatch/) — Policies applied at one routing layer (blueprint, middleware) but not at the handler level that modifies data, or vice versa, creating enforcement gaps.
