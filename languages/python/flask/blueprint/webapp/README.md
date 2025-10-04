# Flask Unsafe Code Lab

Welcome to the Flask corner of the Unsafe Code Lab. This mini-app shows how everyday Flask patterns can create security pitfalls when developers make assumptions about requests, infrastructure, or framework helpers.

## How to navigate
- [Inconsistent Interpretation (ii)](ii/README.md) - Different parts of the code interpret the same input in incompatible ways.
- [Trust Boundary Errors](trust-boundary-errors/README.md) - We believe headers or hosts that should only be accepted from trusted proxies.
- [Cross-Component Semantics](cross-component-semantics/README.md) - Proxies, CDNs, and Flask disagree about what the request actually contains.
- [Policy Composition and Precedence](policy-composition-and-precedence/README.md) - Multiple guards combine so that the weakest one wins.
- [Unsafe Defaults and Misconfiguration](unsafe-defaults-and-misconfiguration/README.md) - Development settings and sample secrets that leak into production.
- [Type Coercion](type-coercion/README.md) - Implicit casting changes the meaning of security checks.
- [Temporal Inconsistency](temporal-inconsistency/README.md) - Time-of-check versus time-of-use, race conditions, and replay issues.

Many of these sections are still populated with outlines and guidance while we migrate examples from the legacy `confusion/` tree. As new Flask walkthroughs land, they will be annotated and generated into these folders automatically.
