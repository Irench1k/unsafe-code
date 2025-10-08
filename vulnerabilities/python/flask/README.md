# Flask Applications

[Flask](https://flask.palletsprojects.com/) is a lightweight WSGI web application framework in Python. It's designed to be simple and easy to use, making it a popular choice for building web applications and APIs.

This collection demonstrates how security vulnerabilities emerge in Flask applications through realistic development patterns: framework-specific behaviors, common architectural decisions, and subtle interactions between components.

## How to Navigate

Each vulnerability category contains runnable Flask applications that demonstrate specific security issues:

- [Confusion & Inconsistent Interpretation](confusion/README.md) - Different parts of the code interpret the same input in incompatible ways.
- [Policy Composition and Precedence](policy_composition_and_precedence/README.md) - Multiple guards combine so that the weakest one wins.
- [Trust Boundary Errors](trust_boundary_errors/README.md) - We believe headers or hosts that should only be accepted from trusted proxies.
- [Cross-Component Semantics](cross_component_semantics/README.md) - Proxies, CDNs, and Flask disagree about what the request actually contains.
- [Unsafe Defaults and Misconfiguration](unsafe_defaults_and_misconfiguration/README.md) - Development settings and sample secrets that leak into production.
- [Type Coercion](type_coercion/README.md) - Implicit casting changes the meaning of security checks.
- [Temporal Inconsistency](temporal_inconsistency/README.md) - Time-of-check versus time-of-use, race conditions, and replay issues.

## Additional Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Flask Security Considerations](https://flask.palletsprojects.com/en/latest/security/)
- [Flask Extension Registry](https://flask.palletsprojects.com/en/latest/extensions/)
