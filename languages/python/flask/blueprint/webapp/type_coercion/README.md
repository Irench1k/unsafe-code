# Type Coercion

Python and JavaScript perform automatic type conversions, and these conversions can cause vulnerabilities in Flask applications through form parsing, JSON decoding, and ORMs. This category focuses on bugs where implicit type casting or conversion changes the meaning of a security check.

## How to spot it
- Ask whether a field was validated as the exact type the guard expects or if it was auto-coerced.
- Watch for helpers that accept both scalars and lists depending on multiplicity.
- Use strict validators (Pydantic strict types, Marshmallow `validate`) for anything that drives authorization or feature flags.

## Subcategories
- [Booleans & Flags](booleans-and-flags/) - Truthiness surprises that enable privileged code paths.
- [Loose Equality](loose-equality/) - String and number comparisons that succeed only because of auto-casting.
- [Array vs Scalar](array-vs-scalar/) - Branches that behave differently when the same parameter arrives once or many times.
- [Null, Empty, Missing](null-empty-missing/) - Treating `""`, `0`, `None`, and "not provided" as the same thing.
- [Deserialization](deserialization/) - Hydrating attacker-controlled objects or polymorphic payloads that smuggle behavior.
