# Idempotency and Replay Weaknesses

Without idempotency keys or replay protection, retried requests and webhook replays can repeat privileged actions.

## Overview

Network hiccups, client retries, and webhook redeliveries are normal. If a Flask handler performs a side effect each time it sees a request, duplicates will multiply the action. That can mean double-charging payments, granting the same privilege twice, or reusing a one-time token that should have expired.

**Practice tips:**
- Require idempotency keys for mutating operations and store the result tied to that key.
- Track webhook event IDs and ignore previously seen messages.
- Treat replay resistance as part of authentication for stateless APIs.
