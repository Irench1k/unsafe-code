# Cross-Component Semantics

HTTP requests pass through multiple components (browsers, CDNs, WAFs, reverse proxies, Flask) that each parse and interpret the protocol. When these **legitimate, non-malicious components disagree on semantics** (e.g., how to count content length, which duplicate header wins, how to normalize paths) security checks can be bypassed. The vulnerability arises not from trusting attacker-controlled data, but from **components with different implementations of the same protocol** seeing different requests.

**Key distinction**: This is about protocol-level **semantic mismatches** between components all trying to handle HTTP correctly. For bugs about **trusting data you think came from infrastructure**, see [Trust Boundary Errors](../trust-boundary-errors/). For bugs about **misconfigured settings**, see [Unsafe Defaults and Misconfiguration](../unsafe-defaults-and-misconfiguration/).

## How to spot it
- Map every component in the request path and identify which ones parse or normalize the message.
- Compare proxy and server configurations to ensure they handle content length, encoding, and paths consistently.
- Review caching rules to ensure authentication and personalization are preserved through shared infrastructure.

## Subcategories
- [HTTP Desync](http-desync/) — Content-Length vs. Transfer-Encoding disagreements between proxy and backend let attackers smuggle their own requests through the mismatch.
- [Header Multiplicity & Ordering](header-multiplicity-and-ordering/) — When duplicate headers appear, proxy and Flask may pick different values (first vs. last, concatenated vs. singular).
- [Path & Percent-Decode Drift](path-percent-decode-drift/) — Path normalization, trailing slashes, and percent-encoding handled differently across components change which resource is accessed.
- [Cache-Key Canonicalization](cache-key-canonicalization/) — Cache and application disagree on which request parts (headers, cookies, query params) make responses unique, causing personalized data to be shared.
