---
description: "Backport specs to earlier versions to maximize inheritance"
---

# Maximize Inheritance: $ARGUMENTS

Move tests to the earliest valid version to maximize inheritance coverage.

## Goal

Tests should live in the **earliest version where the behavior exists**. Later versions inherit automatically, reducing duplication and maintenance burden.

```
v201 (base)     ← Tests go HERE when possible
  ↓ inherits
v202            ← Only version-specific overrides
  ↓ inherits
v203            ← Only version-specific overrides
```

## Before Starting

1. Load `AGENTS.md` for invariants
2. Load `spec/INHERITANCE.md` for patterns
3. Review `spec/spec.yml` for current inheritance structure

## Workflow

### Step 1: Identify Candidates
Look for tests that:
- Were introduced in vN+k but test behavior that exists in vN
- Are duplicated across multiple versions
- Test core functionality, not version-specific features

```bash
# Compare what's in later version vs base
ls spec/v302/cart/  # What's here that could be in v201?
ls spec/v201/cart/  # What's already in base?
```

### Step 2: Verify Portability
For each candidate:

1. **Check if behavior exists in target version**
   ```bash
   # Run test against earlier server
   VERSION=v201 uctest path/to/test.http
   ```

2. **Check if assertions are version-agnostic**
   - Use `isError()` not specific error messages
   - Use helpers not hardcoded values

### Step 3: Port Tests
Delegate to **uc-spec-author**:

1. Copy file to earlier version
2. Update any version-specific references
3. Ensure imports work in new context

### Step 4: Clean Up Later Version
1. Delete the original file from later version
2. It will be recreated as `~file.http` by ucsync

### Step 5: Regenerate Inheritance
Delegate to **uc-spec-sync**:
```bash
ucsync
```

### Step 6: Add Exclusions Where Needed
If behavior differs in some versions:

```yaml
# spec.yml
v203:
  exclude:
    # v203 changes error format
    - path/to/test.http
```

**Always document WHY** in a comment.

### Step 7: Verify Full Chain
Delegate to **uc-spec-runner**:
```bash
uctest v201 v202 v203 v204 v205 v206
```

All should pass.

## Common Patterns

### Core Functionality
These almost always belong in base:
- Authentication boundary tests (authn.http)
- Happy path tests (happy.http)
- Basic input validation

### Version-Specific
These stay in their introducing version:
- Tests for new endpoints
- Tests for changed API signatures
- Vulnerability tests (vuln-*.http) — but exclude in fixed versions

### Partial Portability
Sometimes only part of a file is portable:
1. Split file into portable + version-specific
2. Port the portable part
3. Keep version-specific part local

## Verification Checklist

Before completing:
- [ ] All ported tests pass in target version?
- [ ] Original files deleted from later versions?
- [ ] ucsync ran successfully?
- [ ] Inherited files (`~` prefix) regenerated?
- [ ] Full inheritance chain green?
- [ ] Exclusions documented with WHY?

## Anti-Patterns

- ❌ Porting tests that fail in target version
- ❌ Forgetting to run ucsync after changes
- ❌ Leaving duplicate files in both versions
- ❌ Porting without testing against target server
- ❌ Undocumented exclusions
