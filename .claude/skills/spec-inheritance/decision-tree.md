# Inheritance Decision Trees

Visual decision guides for spec inheritance scenarios.

## Test Failure Triage

```
TEST FAILS
    │
    ├─ Is it an inherited (~) file?
    │      │
    │      ├─ YES ──────────────────────────────────────┐
    │      │                                            │
    │      │   ┌────────────────────────────────────────▼─────────────────┐
    │      │   │ INHERITED TEST FAILS                                     │
    │      │   │                                                          │
    │      │   │ Check source code FIRST!                                 │
    │      │   │ git diff HEAD~5 -- vulnerabilities/.../                  │
    │      │   │                                                          │
    │      │   │ ├─ Code changed recently?                                │
    │      │   │ │    │                                                   │
    │      │   │ │    ├─ YES → Did change fix the vuln accidentally?     │
    │      │   │ │    │         │                                         │
    │      │   │ │    │         ├─ YES → Restore vulnerable code         │
    │      │   │ │    │         └─ NO  → Create local test override      │
    │      │   │ │    │                                                   │
    │      │   │ │    └─ NO  → Is test version-specific?                  │
    │      │   │ │              │                                         │
    │      │   │ │              ├─ YES → Exclude with reason             │
    │      │   │ │              └─ NO  → Debug assertion/API             │
    │      │   │ └                                                        │
    │      │   └──────────────────────────────────────────────────────────┘
    │      │
    │      └─ NO (local file)
    │             │
    │             └─► Standard debugging:
    │                 - Check assertion syntax
    │                 - Verify API response
    │                 - Check auth/setup
    │
    └─ Error type?
           │
           ├─ "ref not found" ────────► Check imports & exclusions
           ├─ Assertion mismatch ─────► Compare expected vs actual
           ├─ 500 error ──────────────► Check assertion syntax (missing operator?)
           └─ 401/403 ────────────────► Check auth helper usage
```

## Exclusion Decision

```
SHOULD I EXCLUDE THIS TEST?
    │
    ├─ Is the vulnerability SUPPOSED to exist in this version?
    │      │
    │      ├─ YES ─────► DON'T EXCLUDE
    │      │             Fix source code to restore vulnerability
    │      │
    │      └─ NO ──────► Continue...
    │
    ├─ Is this a version-specific behavior?
    │      │
    │      ├─ YES ─────► EXCLUDE with comment
    │      │             Example: "v302 uses new auth, test assumes old"
    │      │
    │      └─ NO ──────► Continue...
    │
    ├─ Did the API contract change intentionally?
    │      │
    │      ├─ YES ─────► Create LOCAL OVERRIDE
    │      │             Copy ~file, modify for new API
    │      │
    │      └─ NO ──────► Continue...
    │
    └─ Is this just a flaky/broken test?
           │
           ├─ YES ─────► FIX THE TEST
           │             Don't exclude to hide problems
           │
           └─ NO ──────► Investigate deeper before deciding
```

## Override vs Exclude

```
INHERITED TEST DOESN'T WORK FOR MY VERSION
    │
    ├─ Same endpoint, same behavior, different syntax?
    │      │
    │      └─► CREATE LOCAL OVERRIDE
    │          - Copy ~file.http → file.http
    │          - Modify syntax/assertions
    │          - Run ucsync to clean up
    │
    ├─ Endpoint doesn't exist in this version?
    │      │
    │      └─► EXCLUDE ENTIRE FILE
    │          exclude:
    │            - "path/to/file.http"
    │
    ├─ Endpoint exists but specific test doesn't apply?
    │      │
    │      └─► EXCLUDE SPECIFIC TEST
    │          exclude:
    │            - "path/to/file.http::Test Title"
    │
    └─ Endpoint behavior intentionally different?
           │
           └─► CREATE LOCAL OVERRIDE with new tests
               Don't exclude - replace with version-appropriate tests
```

## Ref Not Found Resolution

```
ERROR: Reference 'some_name' not found
    │
    ├─ Is the referenced test in an excluded file?
    │      │
    │      ├─ YES ─────► Either:
    │      │             a) Remove exclusion, OR
    │      │             b) Create local _fixtures.http with @name
    │      │
    │      └─ NO ──────► Continue...
    │
    ├─ Is the import chain correct?
    │      │
    │      ├─ NO ──────► Fix @import statements
    │      │             Check for ~file.http vs file.http
    │      │
    │      └─ YES ─────► Continue...
    │
    ├─ Does the @name exist in inheritance chain?
    │      │
    │      ├─ NO ──────► Create the fixture:
    │      │             - In _fixtures.http for reuse
    │      │             - In same file if one-time use
    │      │
    │      └─ YES ─────► Run ucsync to regenerate
    │
    └─ Still failing?
           │
           └─► Check for circular dependencies
               A refs B refs C refs A = broken
```

## Quick Reference Table

| Scenario | Action | Command/File |
|----------|--------|--------------|
| Inherited test fails | Check source code | `git diff` |
| Need to customize | Create local override | Copy `~file` → `file` |
| Test doesn't apply | Exclude in spec.yml | `exclude:` section |
| Ref not found | Check imports/exclude | `ucsync --check` |
| Stale ~ files | Regenerate | `ucsync v302 --force` |
| New version setup | Inherit from parent | Add to spec.yml |

## Anti-Patterns

❌ **Exclude to make tests pass**
→ Exclusions hide problems, don't solve them

❌ **Edit ~ prefixed files**
→ Changes lost on next ucsync

❌ **Exclude without investigating code**
→ May be hiding accidental fixes

❌ **Create override for minor syntax difference**
→ Fix the underlying issue instead

✅ **Investigate source code when inherited test fails**
→ The test worked before - what changed?

✅ **Document exclusion reasons**
→ Future maintainers need context

✅ **Run ucsync after spec.yml changes**
→ Regenerates inheritance correctly
