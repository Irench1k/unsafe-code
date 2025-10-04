# Inconsistent Interpretation

Inconsistent interpretation happens when code that should be working with **one logical input value** ends up consulting **different representations or different sources** of that value. Sometimes this means security checks and business logic read from entirely different places (path vs. query vs. body vs. a merged helper). Other times, both read the same source but one normalizes, casts, or handles multiple values differently than the other. Either way, the result is the same: two effective values for what should be a single input, opening the door to authorization bypasses, identity confusion, and data integrity violations.

## How to spot it
- Pick a logical input (like `user_id` or `resource_name`) and trace its **full lifecycle**: where it enters the system, how it's merged or combined with other sources, what normalizations or casts happen, and where it's ultimately accessed.
- Compare what the **security check** reads versus what the **business logic** uses,not just the variable name, but the actual source (path? query? body? merged dict? default value?).
- Look for "smart" helpers like `request.values` or custom accessors that merge multiple sources, and check whether all consumers agree on precedence.
- Watch for **multi-value** and **type** handling differences: does one place use `.get()` (first value) while another uses `.getlist()` (all values)? Are there implicit casts or normalization steps (case folding, URL decoding, whitespace stripping)?
- Verify **ordering**: do guards run before or after inputs are finalized, merged, or normalized? Are defaults or fallbacks introduced after the security check?

## Subcategories
- [Source Precedence](source_precedence/) — Different components pull the "same" logical parameter from different places (path vs. query vs. body vs. headers vs. cookies), leading to precedence conflicts, merging issues, or source pollution.
- [Normalization & Canonicalization](normalization_canonicalization/) — Case folding, whitespace stripping, URL decoding, or path normalization makes "equal" values diverge when checked versus used.
- [Multi-Value Semantics](multi_value_semantics/) — One component treats a parameter as a list while another grabs only the first value, or `.get()` vs `.getlist()` disagreements create different effective values.
- [Cross-Component Parse](cross_component_parse/) — Middleware, decorators, or framework helpers parse or reshape inputs in ways that differ from what the view sees.
- [Behavior Order](behavior_order/) — Guards run before inputs are fully merged, normalized, or before critical context (like `g.user`) is established.
- [HTTP Semantics](http_semantics/) — Wrong assumptions about HTTP methods or content types (e.g., GET with body, form vs. JSON) cause components to read different sources.
- [Authorization Binding](authz_binding/) — Authorization checks identity or value X, but the handler acts on identity or value Y.
