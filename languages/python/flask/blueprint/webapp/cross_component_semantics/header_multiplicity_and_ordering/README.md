# Header Multiplicity and Ordering Drift
Duplicate headers are legal in HTTP, but if the proxy keeps the first copy and Flask keeps the last, one of them will honor the attacker's value.
## Overview

Security logic often exists in both the proxy (rate limiting, authentication) and the application (session checks). When a client sends two `Authorization` headers or multiple cookies, the proxy might combine them one way while Flask handles them differently. Attackers exploit this disagreement to satisfy the proxy with a benign header while the backend consumes the malicious one.

**Practice tips:** - Normalize or reject duplicated security headers at the edge before forwarding. - Configure Flask (or Werkzeug) to treat header multiplicity the same way your proxy does. - Include duplicate-header cases in integration and fuzz tests for critical routes.
