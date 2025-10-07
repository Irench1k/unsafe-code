# Boolean and Flag Coercion

Loose truthiness checks can incorrectly interpret strings like "yes" or "0", allowing attackers to enable feature flags or bypass guards without providing the expected value.

## Overview

Forms and JSON payloads arrive as strings, yet Flask code often treats them as booleans without explicit casting. Python considers any non-empty string truthy, so checks such as `if request.args.get("admin"):` succeed even when the user submits "false". Without strict validation, an attacker can enable privileged behavior simply by passing a creative value.

**Practice tips:**
- Use explicit comparisons (`value == "true"`) or strict types provided by Pydantic or Marshmallow.
- Audit feature gates and policy toggles for implicit truthiness.
- Log unexpected boolean inputs so you catch misuse before it becomes an incident.
