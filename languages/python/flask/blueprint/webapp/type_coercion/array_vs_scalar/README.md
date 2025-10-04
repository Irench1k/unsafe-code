# Array vs Scalar Confusion

The same parameter can arrive once as a string or many times as a list, and treating those cases interchangeably leads to missing or excess authorization.

## Overview

Flask surfaces repeated parameters through helpers like `.getlist()` while `.get()` returns only the first value. APIs that accept both single and multi-select input often forget to normalize, so a guard may see a string while the business logic receives a list. Attackers exploit this discrepancy to include forbidden roles in the extra values or to bypass checks that expect a single entry.

**Practice tips:**
- Normalize request data in one place, returning a predictable type to the rest of the code.
- Cover the multi-value case in tests, not just the happy path where a single value is sent.
- Avoid converting lists to scalars silently; make the caller choose the shape.
