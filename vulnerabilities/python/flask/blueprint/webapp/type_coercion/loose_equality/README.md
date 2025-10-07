# Loose Equality Comparisons

Comparing user input with `==` invites type juggling; crafted strings that coerce to the same value can pass checks they should fail.

## Overview

In loosely typed comparisons, the runtime automatically converts both sides to a shared representation. This is convenient but dangerous in security checks: values such as `"0e12345"` and `0` both evaluate to zero, and whitespace-padded tokens may compare equal after trimming. Any guard that uses `if request.json["role"] == "admin":` should ensure that the incoming value cannot change through coercion.

**Practice tips:**
- Use strict comparisons backed by schema validation or explicit casting before the guard.
- Reject unexpected types early so they never reach critical equality checks.
- Normalize values once in a dedicated layer, then stick to exact string comparisons downstream.
