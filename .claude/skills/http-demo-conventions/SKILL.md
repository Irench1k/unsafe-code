---
name: http-demo-conventions
description: Conventions for student-facing interactive demos (`*.exploit.http`, `*.fixed.http`) under `vulnerabilities/.../http/`. Use with `http-syntax`.
---

# Demo Conventions

**Audience:** Students. Purpose: show impact, not test coverage.

- **One request, one assert** per demo file; keep it short and readable.
- **Auth:** Use attacker’s own credentials (per SpongeBob rules). No stolen passwords.
- **Narrative:** Describe business impact in comments; avoid jargon. Mention attacker/victim roles.
- **Helpers:** Plain httpyac – no `$(response)` helpers. Access data via `response.status`, `response.parsedBody`, `response.headers`.
- **Headers:** Include explicit `Authorization` and `Content-Type` when needed. No hidden utils imports.
- **Setup:** Inline any seeding/login steps in `{{ }}` blocks; keep self-contained.
- **Fixed demos:** Mirror exploit but show corrected behavior; assert success/denial accordingly.
- **Characters:** Follow character mappings; attacker uses their own account; rotate victims/impacts to avoid repetition.
- **Paths:** Use absolute URLs in the first two examples of a series, then `@base` later if already introduced.
- **Clarity:** Comment top lines with the scenario and expected outcome.
