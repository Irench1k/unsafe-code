---
name: http-editing-policy
description: Safety policy for `.http` files. Auto-load for any agent near `.http` content.
---

# HTTP Editing Policy

## Who may edit `.http` files?
- **Manual edits allowed:** `spec-author`, `spec-debugger`, `demo-author`, `demo-debugger`.
- **Automated regeneration:** `spec-runner` may run `ucsync` to refresh inherited specs, but should not hand-edit `.http`.
- **Everyone else:** Do **not** touch `.http` files—delegate instead.

## Role boundaries
- **spec-author:** Creates/updates `spec/**/*.http` (E2E tests). Runs uctest only via spec-runner; manages content, not inheritance policies.
- **spec-debugger:** Diagnoses failing uctest runs. *Reads* `.http`, but normally does **not edit**—hands fixes to spec-author or code-author.
- **demo-author:** Creates/updates demo `.http` files (`*.exploit.http`, `*.fixed.http`) under `vulnerabilities/.../http/`.
- **demo-debugger:** Diagnoses failing demos. Reads `.http`; if a small syntax fix is obvious, may patch, otherwise delegate to demo-author.

## Rules of engagement
- If you are not in the allowed list → stop and delegate immediately.
- Do not mix spec and demo edits in one change; keep domains clean.
- Preserve **one concept per demo** and **one assert per request** in demos.
- For specs, do not hand-edit inherited `# @tag` lines—run `ucsync` via spec-runner when needed.
- Always open `http-syntax` + `http-gotchas` while editing.

## Delegation quicklinks
- Spec content change → `spec-author`
- Spec failure triage → `spec-debugger` → next agent
- Demo content change → `demo-author`
- Demo failure triage → `demo-debugger` → next agent
