# Inconsistent Interpretation

Inconsistent interpretation happens when code that should be working with **one logical input value** ends up consulting **different representations or different sources** of that value. Sometimes this means security checks and business logic read from entirely different places (path vs. query vs. body vs. a merged helper). Other times, both read the same source but one normalizes, casts, or handles multiple values differently than the other. Either way, the result is the same: two effective values for what should be a single input, opening the door to authorization bypasses, identity confusion, and data integrity violations.

## Running the Examples

All examples in this category share a single Docker Compose environment:

```bash
cd vulnerabilities/python/flask/confusion
docker compose up -d

# View logs
docker compose logs -f

# Stop and clean up
docker compose down
```

The application will be available at `http://localhost:8000`.

## How to spot it
- Pick a logical input (like `user_id` or `resource_name`) and trace its **full lifecycle**: where it enters the system, how it's merged or combined with other sources, what normalizations or casts happen, and where it's ultimately accessed.
- Compare what the **security check** reads versus what the **business logic** uses, not just the variable name, but the actual source (path? query? body? merged dict? default value?).
- Look for "smart" helpers like `request.values` or custom accessors that merge multiple sources, and check whether all consumers agree on precedence.
- Watch for **multi-value** and **type** handling differences: does one place use `.get()` (first value) while another uses `.getlist()` (all values)? Are there implicit casts or normalization steps (case folding, URL decoding, whitespace stripping)?
- Verify **ordering**: do guards run before or after inputs are finalized, merged, or normalized? Are defaults or fallbacks introduced after the security check?

## Subcategories

The subcategories below are organized with progressive complexity (indicated by the `rXX_` prefix). Each builds on concepts from earlier examples. Some subcategories contain multiple example implementations (indicated by the `e0X_` prefix, such as `e01_baseline`, `e02_decorator_drift`) that demonstrate different variations or progressive refinements of the same vulnerability pattern:

1. [Source Precedence](webapp/r01_source_precedence/README.md) — Different components pull the "same" logical parameter from different places (path vs. query vs. body vs. headers vs. cookies), leading to precedence conflicts, merging issues, or source pollution.
2. [Cross-Component Parse](webapp/r02_cross_component_parse/README.md) — Middleware, decorators, or framework helpers parse or reshape inputs in ways that differ from what the view sees.
3. [Authorization Binding](webapp/r03_authz_binding/README.md) — Authorization checks identity or value X, but the handler acts on identity or value Y.
4. [HTTP Semantics](webapp/r04_http_semantics/README.md) — Wrong assumptions about HTTP methods or content types (e.g., GET with body, form vs. JSON) cause components to read different sources.
5. [Multi-Value Semantics](webapp/r05_multi_value_semantics/README.md) — One component treats a parameter as a list while another grabs only the first value, or `.get()` vs `.getlist()` disagreements create different effective values.
6. [Normalization & Canonicalization](webapp/r06_normalization_canonicalization/README.md) — Case folding, whitespace stripping, URL decoding, or path normalization makes "equal" values diverge when checked versus used.
