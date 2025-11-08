# Confusion & Inconsistent Interpretation

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

## Subcategories

1. [Source Precedence](webapp/r01_source_precedence/README.md) — Different components pull the "same" logical parameter from different places (path vs. query vs. body vs. headers vs. cookies), leading to precedence conflicts, merging issues, or source pollution.
2. [Cross-Component Parse](webapp/r02_cross_component_parse/README.md) — Middleware, decorators, or framework helpers parse or reshape inputs in ways that differ from what the view sees.
3. [Authorization Binding](webapp/r03_authz_binding/README.md) — Authorization checks identity or value X, but the handler acts on identity or value Y.
4. [HTTP Semantics](webapp/r04_http_semantics/README.md) — Wrong assumptions about HTTP methods or content types (e.g., GET with body, form vs. JSON) cause components to read different sources.
5. [Multi-Value Semantics](webapp/r05_multi_value_semantics/README.md) — One component treats a parameter as a list while another grabs only the first value, or `.get()` vs `.getlist()` disagreements create different effective values.
6. [Normalization & Canonicalization](webapp/r06_normalization_canonicalization/README.md) — Case folding, whitespace stripping, URL decoding, or path normalization makes "equal" values diverge when checked versus used.
