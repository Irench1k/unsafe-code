---
description: "Quick health check for a version: tests, inheritance, docs, and git status"
model: haiku
argument-hint: [version]
---

# Health Check: $ARGUMENTS

Run quick verification that everything is working for a version.

## Automated Checks

### E2E Specs

!`uctest $ARGUMENTS/ 2>&1 | tail -10 || echo "uctest failed or not found"`

### Inheritance Sync

!`ucsync --check 2>&1 | head -10 || echo "ucsync check unavailable"`

### Docs Verification

!`uv run docs verify 2>&1 | tail -5 || echo "docs verify unavailable"`

### Git Status

!`git status --short 2>&1 | head -15`

### Server Health

!`(cd vulnerabilities/python/flask/confusion/ && uclogs --since 5m 2>&1 | grep -Ei "error|exception" | head -5 || echo "No recent errors")`

## Interpretation

| Check       | Green                    | Yellow          | Red       |
| ----------- | ------------------------ | --------------- | --------- |
| E2E Specs   | All pass                 | Some warnings   | Failures  |
| Inheritance | "already in sync"        | Pending changes | Errors    |
| Docs        | "All targets up-to-date" | Warnings        | Errors    |
| Git         | Clean or staged          | Uncommitted     | Conflicts |
| Server      | No errors                | Warnings        | Errors    |

## Next Steps

**If all green**: Ready to commit or continue development

**If failures found**:

- E2E failures → `/project:fix-failing-specs $ARGUMENTS`
- Inheritance issues → `ucsync $ARGUMENTS`
- Doc issues → `uv run docs generate --target [path]`
- Server errors → Check `uclogs -f` for details
