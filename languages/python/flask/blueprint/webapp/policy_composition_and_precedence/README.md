# Policy Composition and Precedence

Modern applications use multiple layers of security controls: blueprints, decorators, feature flags, and middleware. Vulnerabilities occur when two policies overlap and the weaker one executes last, bypassing the stronger protection that should have been enforced.

## How to spot it
- Review the complete decorator chain and middleware order, not just recently added guards.
- Search for code paths that default to "allow" when an explicit deny would be safer.
- Check whether nested resources inherit stricter policies from their parents or bypass them.

## Subcategories
- [Merge Order & Short-Circuit](merge-order-and-short-circuit/) - Combining permissive or caching layers with stronger guards in the wrong order.
- [Default-Allow Gaps](default-allow-gaps/) - New routes or feature toggles that are deployed without security protection.
- [Scope Mismatch](scope-mismatch/) - Policies applied at one routing layer but not at the handler that modifies data.
