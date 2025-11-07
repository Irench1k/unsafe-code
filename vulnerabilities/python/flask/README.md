# Flask Applications

[Flask](https://flask.palletsprojects.com/) is a lightweight WSGI web application framework in Python. It's designed to be simple and easy to use, making it a popular choice for building web applications and APIs.

This collection demonstrates how security vulnerabilities emerge in Flask applications through realistic development patterns: framework-specific behaviors, common architectural decisions, and subtle interactions between components.

## Confusion & Inconsistent Interpretation

Inconsistent interpretation happens when code that should be working with **one logical input value** ends up consulting **different representations or different sources** of that value. Sometimes this means security checks and business logic read from entirely different places (path vs. query vs. body vs. a merged helper). Other times, both read the same source but one normalizes, casts, or handles multiple values differently than the other. Either way, the result is the same: two effective values for what should be a single input, opening the door to authorization bypasses, identity confusion, and data integrity violations.

1.  [Source Precedence](confusion/webapp/r01_source_precedence/README.md) — Different components pull the "same" logical parameter from different places (path vs. query vs. body vs. headers vs. cookies), leading to precedence conflicts.
2.  [Cross-Component Parse](confusion/webapp/r02_cross_component_parse/README.md) — Middleware, decorators, or framework helpers parse or reshape inputs in ways that differ from what the view sees.
3.  [Authorization Binding](confusion/webapp/r03_authz_binding/README.md) — Authorization checks identity or value X, but the handler acts on identity or value Y.
4.  [HTTP Semantics](confusion/webapp/r04_http_semantics/README.md) — Wrong assumptions about HTTP methods or content types cause components to read different sources.
5.  [Multi-Value Semantics](confusion/webapp/r05_multi_value_semantics/README.md) — One component treats a parameter as a list while another grabs only the first value.
6.  [Normalization & Canonicalization](confusion/webapp/r06_normalization_canonicalization/README.md) — Case folding, whitespace stripping, or URL decoding makes "equal" values diverge when checked versus used.

### Running the examples

First, navigate to the [`confusion`](confusion/README.md) directory, and then use Docker Compose:

```bash
cd vulnerabilities/python/flask/confusion
docker compose up -d

# View logs
docker compose logs -f

# Stop and clean up
docker compose down
```
The application will be available at `http://localhost:8000`.

### How to spot it
- Pick a logical input (like `user_id` or `resource_name`) and trace its **full lifecycle**: where it enters the system, how it's merged or combined with other sources, what normalizations or casts happen, and where it's ultimately accessed.
- Compare what the **security check** reads versus what the **business logic** uses, not just the variable name, but the actual source (path? query? body? merged dict? default value?).
- Look for "smart" helpers like `request.values` or custom accessors that merge multiple sources, and check whether all consumers agree on precedence.
- Watch for **multi-value** and **type** handling differences: does one place use `.get()` (first value) while another uses `.getlist()` (all values)? Are there implicit casts or normalization steps (case folding, URL decoding, whitespace stripping)?
- Verify **ordering**: do guards run before or after inputs are finalized, merged, or normalized? Are defaults or fallbacks introduced after the security check?

## Additional Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Flask Security Considerations](https://flask.palletsprojects.com/en/latest/security/)
- [Flask Extension Registry](https://flask.palletsprojects.com/en/latest/extensions/)
