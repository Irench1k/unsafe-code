# Path and Percent-Decode Drift
A CDN or WAF might normalize `%2F` or dot segments differently than Flask, letting attackers reach routes your app thought were protected.
## Overview

URL decoding, path traversal normalization, and collapse of duplicate slashes can happen at multiple layers. If the proxy rewrites `/admin%2Fsettings` to `/admin/settings` before applying ACLs but forwards the original string to Flask, the backend route matching may reach a resource that should have been blocked. Keeping the edge and the app in sync is essential for path-based security.

**Practice tips:** - Align normalization rules between your proxy and Flask; disable features you are not explicitly relying on. - Treat encoded path tests (`%2e%2e`, `%2F`, nested encodings) as regression coverage items. - Consider rejecting overly encoded paths at the edge to cut off exploitation options.
