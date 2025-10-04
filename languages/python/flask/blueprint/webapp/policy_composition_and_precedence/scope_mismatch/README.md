# Scope Mismatch Between Guards and Handlers
Applying a guard to a blueprint but not to the individual handler, or vice versa, leaves gaps that attackers can exploit.
## Overview

Authorization often happens at different layers: blueprint-level decorators, per-route checks, and even object-level policies. If those scopes overlap imperfectly, a sub-route or alternate HTTP method may skip the intended guard. This is especially common during refactors when routes move or inherit from new base classes.

**Practice tips:** - Review middleware and decorator coverage after reorganizing routes. - Write tests for every HTTP method and nested path, not just the primary one. - Centralize guard application where possible so scope is obvious.
