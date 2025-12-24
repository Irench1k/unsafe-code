# Inconsistent Interpretation

Inconsistent interpretation happens when code that should be working with **one logical input value** ends up consulting **different representations or different sources** of that value. Sometimes this means security checks and business logic read from entirely different places (path vs. query vs. body vs. a merged helper). Other times, both read the same source but one normalizes, casts, or handles multiple values differently than the other. Either way, the result is the same: two effective values for what should be a single input, opening the door to authorization bypasses, identity confusion, and data integrity violations.

## How to spot it
- Pick a logical input (like `user_id` or `resource_name`) and trace its **full lifecycle**: where it enters the system, how it's merged or combined with other sources, what normalizations or casts happen, and where it's ultimately accessed.
- Compare what the **security check** reads versus what the **business logic** uses,not just the variable name, but the actual source (path? query? body? merged dict? default value?).
- Look for "smart" helpers like `request.values` or custom accessors that merge multiple sources, and check whether all consumers agree on precedence.
- Watch for **multi-value** and **type** handling differences: does one place use `.get()` (first value) while another uses `.getlist()` (all values)? Are there implicit casts or normalization steps (case folding, URL decoding, whitespace stripping)?
- Verify **ordering**: do guards run before or after inputs are finalized, merged, or normalized? Are defaults or fallbacks introduced after the security check?

## Subcategories
1. [Input Source](./r01_input_source_confusion/README.md) — Source precedence bugs occur when different code paths read the "same" logical input from different locations (path vs. query vs. body vs. headers vs. cookies).
2. [Authentication](./r02_authentication_confusion/README.md) — Authentication confusion occurs when the code that **verifies identity** examines a different value than the code that **acts on identity**.
3. [Authorization](./r03_authorization_confusion/README.md) — Authorization confusion happens when the code that **checks permissions** examines a different resource or identity than the code that **performs the action**.
4. [Cardinality](./r04_cardinality_confusion/README.md) — Cardinality confusion occurs when one part of the code treats a parameter as a **single value** while another treats it as a **list**. The parser, validator, and business logic disagree on whether you sent one item or many.
5. [Normalization](./r05_normalization_issues/README.md) — Character normalization confusion happens when two code paths apply **different string transformations** to the same logical input.
