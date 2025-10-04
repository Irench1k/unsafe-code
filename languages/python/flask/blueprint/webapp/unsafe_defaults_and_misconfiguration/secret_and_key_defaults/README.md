# Secret and Key Defaults

Leaving `SECRET_KEY`, signing keys, or crypto salts at their sample values lets attackers forge sessions and tokens as if they were the server.

## Overview

Flask apps rely on `SECRET_KEY` for session cookies, CSRF tokens, and more. Tutorials ship with obvious values like `"change-me"`, and real projects sometimes keep them all the way to production. With the key in hand, attackers can mint their own authenticated sessions or tamper with signed payloads.

**Practice tips:**
- Generate high-entropy keys per environment and manage them as secrets, not config constants.
- Add startup checks that refuse to run when default values are detected.
- Rotate secrets as part of your incident response plan.
