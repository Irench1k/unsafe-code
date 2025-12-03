---
description: "Smart spec execution with failure interpretation and next-step suggestions"
model: sonnet
argument-hint: [version-path] [options]
---

# Run Specs: $ARGUMENTS

Execute e2e specs intelligently and interpret results.

## Execution Modes

**Path-based** (fast, limited scope):

```bash
uctest v301/cart/checkout
```

**Tag-based** (slower, full dependency resolution):

```bash
uctest @happy v301/
uctest @authn @orders v301/
```

**With options**:

- `-k` - Keep going after failures
- `-v` - Verbose output
- `-r` - Resume from last failure
- `--show-plan` - Show execution order without running

## Workflow

1. Determine best execution mode based on target
2. Run specs via `uc-spec-runner` agent
3. Interpret results
4. Suggest next steps based on failure patterns

## Failure Interpretation

| Pattern                   | Likely Cause                   | Next Agent                        |
| ------------------------- | ------------------------------ | --------------------------------- |
| "ref X not found"         | Import chain broken            | uc-spec-debugger                  |
| Assertion mismatch        | Test logic or API change       | uc-spec-debugger → uc-spec-author |
| 500 server error          | Source code bug or bad request | Check uclogs                      |
| Timeout                   | Slow test or infinite loop     | Check test for missing seed       |
| Multiple similar failures | Common root cause              | Fix one, others may resolve       |

## Post-Run Actions

**If all pass**: Report success, suggest next validation step

**If failures**:

1. Group failures by pattern
2. Identify root cause vs symptoms
3. Delegate to appropriate agent
4. Re-run after fixes

## Quick Commands

```bash
# Run all specs for a version
uctest v301/

# Run specific endpoint
uctest v301/cart/checkout/post/

# Run by tag
uctest @vulnerable v301/

# Check execution plan
uctest --show-plan v301/orders/
```

## Notes

- Always run `ucsync` first if you've modified spec.yml
- Use `uclogs` to inspect server-side errors
- Inherited tests (~ prefix) should not be edited directly
