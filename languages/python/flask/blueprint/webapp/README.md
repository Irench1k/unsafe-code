# Flask Unsafe Code Lab

Welcome to the Flask corner of the Unsafe Code Lab. This mini-app shows how everyday Flask patterns can create security pitfalls when developers make assumptions about requests, infrastructure, or framework helpers.

## How to navigate
- [Inconsistent Interpretation (ii)](ii/README.md) - Different parts of the code interpret the same input in incompatible ways.
- [Trust Boundary Errors](trust_boundary_errors/README.md) - We believe headers or hosts that should only be accepted from trusted proxies.
- [Cross-Component Semantics](cross_component_semantics/README.md) - Proxies, CDNs, and Flask disagree about what the request actually contains.
- [Policy Composition and Precedence](policy_composition_and_precedence/README.md) - Multiple guards combine so that the weakest one wins.
- [Unsafe Defaults and Misconfiguration](unsafe_defaults_and_misconfiguration/README.md) - Development settings and sample secrets that leak into production.
- [Type Coercion](type_coercion/README.md) - Implicit casting changes the meaning of security checks.
- [Temporal Inconsistency](temporal_inconsistency/README.md) - Time-of-check versus time-of-use, race conditions, and replay issues.
