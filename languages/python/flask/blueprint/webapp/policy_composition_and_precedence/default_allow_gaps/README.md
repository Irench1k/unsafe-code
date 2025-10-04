# Default-Allow Gaps
New routes and features sometimes ship without explicit authorization checks, leaving sensitive actions exposed.
## Overview

Many frameworks default to "allow" unless you add a guard. When teams move fast, they add UI checks or rely on route naming conventions, assuming the backend will catch up later. Attackers probe for these unsecured endpoints, especially admin helpers and beta features hidden in the frontend.

**Practice tips:** - Start with deny-by-default blueprints or middleware that requires an explicit allowlist. - Add automated checks that flag routes lacking authentication decorators. - Keep documentation of feature flags and ensure the API enforces them server side.
