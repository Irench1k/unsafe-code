# Null, Empty, and Missing Values

Empty strings, zero, `None`, and entirely missing fields all behave differently; collapsing them together lets attackers bypass presence checks or disable safeguards.

## Overview

Web forms frequently submit empty strings, while JSON often omits fields altogether. If a guard simply tests `if not request.json.get("quota"):` it treats `0`, `"0"`, `None`, and "not provided" the same way. This can reset a quota, disable a feature flag, or bypass validation that expected a real value.

**Practice tips:**
- Distinguish "not provided" from provided-but-empty in your schema layer.
- Use sentinel values or explicit `is None` checks for nullable fields.
- Add logging for unexpected empty values in security-sensitive fields.
