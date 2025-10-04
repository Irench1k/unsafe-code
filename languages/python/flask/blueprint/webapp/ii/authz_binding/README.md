# Authorization Binding Drift in Flask
Binding bugs happen when we authenticate one identity but later trust user-controlled IDs for the actual work, letting attackers act on behalf of someone else.
## Overview

In multi-tenant or multi-user APIs, a common pattern is to authenticate once (session, token, Basic Auth) and then trust request data to determine which account, tenant, or resource to act on. If the handler uses attacker-controlled identifiers - `request.json["owner"]`, `request.args["user_id"]`, etc. - it separates the security decision from the action being taken.

We have not yet built Flask walkthroughs for this category. As new scenarios land (e.g., form submissions that rebind `owner_id` or background job APIs that mis-handle `account_id`), their annotations and examples will live here.
