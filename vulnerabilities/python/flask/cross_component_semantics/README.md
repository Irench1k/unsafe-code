# Cross-Component Semantics

HTTP requests pass through multiple components (browsers, CDNs, WAFs, reverse proxies, Flask) that each parse and interpret the protocol. When these **legitimate, non-malicious components disagree on semantics**—how to count content length, which duplicate header wins, how to normalize paths—security checks can be bypassed. The vulnerability arises not from trusting attacker-controlled data, but from **components with different implementations of the same protocol** seeing different requests.

**Key distinction**: This is about protocol-level **semantic mismatches** between components all trying to handle HTTP correctly. For bugs about **trusting data you think came from infrastructure**, see [Trust Boundary Errors](../trust_boundary_errors/). For bugs about **misconfigured settings**, see [Unsafe Defaults and Misconfiguration](../unsafe_defaults_and_misconfiguration/).

## Running the Examples

**Important**: Unlike other vulnerability categories, each subcategory in Cross-Component Semantics has its own Docker Compose environment because they require different infrastructure components:

- **HTTP Desync** requires reverse proxy configurations (nginx, HAProxy)
- **Header Multiplicity** needs load balancers with header manipulation
- **Path & Percent-Decode Drift** uses CDNs and path-rewriting proxies
- **Cache-Key Canonicalization** depends on caching layers (Varnish, nginx cache)

Navigate to the specific subcategory directory and start its environment:

```bash
# Example: Running HTTP Desync examples
cd vulnerabilities/python/flask/cross_component_semantics/http_desync
docker compose up -d

# View logs
docker compose logs -f

# Stop and clean up
docker compose down
```

Each subcategory's README provides specific instructions for its infrastructure setup and available endpoints.

## How to spot it

- **Map the component chain**: Identify every component in the request path (browser → CDN → WAF → reverse proxy → load balancer → Flask) and determine which ones parse, normalize, or transform the HTTP message.
- **Compare parsing implementations**: Review how each component handles edge cases like duplicate headers, conflicting content-length values, trailing slashes, percent-encoding, and case sensitivity.
- **Test boundary conditions**: Send requests with ambiguous or contradictory HTTP features (e.g., both `Content-Length` and `Transfer-Encoding`, duplicate `Host` headers, mixed encoding) and observe how each component interprets them.
- **Verify cache and proxy configurations**: Ensure caching rules preserve authentication state, personalization headers, and sensitive query parameters—check that cache keys include all security-relevant request parts.
- **Audit normalization points**: Identify where paths, headers, or parameters are normalized and confirm that authorization checks happen after (or use the same normalization as) the final interpretation.

## Subcategories

- [HTTP Desync](http_desync/) — Content-Length vs. Transfer-Encoding disagreements between proxy and backend let attackers smuggle their own requests through the mismatch, causing request routing confusion and cache poisoning.

- [Header Multiplicity & Ordering](header_multiplicity_and_ordering/) — When duplicate headers appear, proxy and Flask may pick different values (first vs. last, concatenated vs. singular), causing authorization checks to see different data than business logic.

- [Path & Percent-Decode Drift](path_percent_decode_drift/) — Path normalization, trailing slashes, and percent-encoding handled differently across components change which resource is accessed, bypassing URL-based authorization or routing rules.

- [Cache-Key Canonicalization](cache_key_canonicalization/) — Cache and application disagree on which request parts (headers, cookies, query params) make responses unique, causing personalized or authenticated data to be served to wrong users.
