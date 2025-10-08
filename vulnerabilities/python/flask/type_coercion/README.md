# Type Coercion

Python and JavaScript perform automatic type conversions, and these conversions can cause vulnerabilities in Flask applications through form parsing, JSON decoding, and ORMs. This category focuses on bugs where implicit type casting or conversion changes the meaning of a security check.

## Running the Examples

All examples in this category share a single Docker Compose environment:

```bash
cd vulnerabilities/python/flask/type_coercion
docker compose up -d

# View logs
docker compose logs -f

# Stop and clean up
docker compose down
```

The application will be available at `http://localhost:8000/type-coercion/`.

## How to spot it
- Identify whether a field was validated as the **exact type** the guard expects, or if it was auto-coerced from a different representation (string to bool, integer to string, etc.).
- Watch for helpers or parsers that **accept both scalars and lists** depending on multiplicity (e.g., `?id=1` vs. `?id=1&id=2`), which can bypass single-value validation logic.
- Look for **truthiness checks** (`if value:`) on fields that might be empty strings, zero, or `None`, where the intended logic was checking for explicit presence or a specific value.
- Use **strict validators** (Pydantic strict types, Marshmallow `validate`, or explicit type checks) for anything that drives authorization decisions, feature flags, or privilege escalation.
- Trace how **null, empty, and missing** values are distinguished: does the code treat `""`, `0`, `None`, and "not provided" as the same thing when they should be semantically different?

## Subcategories

- [Booleans & Flags](webapp/booleans_and_flags/) — Truthiness surprises and coercion-based bypasses that enable privileged code paths or flip intended security checks.
- [Loose Equality](webapp/loose_equality/) — String and number comparisons that succeed only because of automatic type casting, allowing unauthorized access or data manipulation.
- [Array vs Scalar](webapp/array_vs_scalar/) — Branches that behave differently when the same parameter arrives once or many times, enabling multi-value attacks or validation bypasses.
- [Null, Empty, Missing](webapp/null_empty_missing/) — Treating `""`, `0`, `None`, and "not provided" as equivalent when they represent distinct states, leading to authentication bypasses or unintended defaults.
- [Deserialization](webapp/deserialization/) — Hydrating attacker-controlled objects or polymorphic payloads that smuggle unexpected types or behaviors into the application logic.
