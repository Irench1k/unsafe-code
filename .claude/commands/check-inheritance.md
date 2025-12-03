---
description: "Check e2e spec inheritance health and identify broken chains"
model: opus
argument-hint: [version-spec]
---

# Check Inheritance: $ARGUMENTS

Analyze deeply the inheritance chain. Consider whether failures indicate code issues, not test issues.

Validate spec inheritance is working correctly for specified version(s).

## Current Inheritance State

!`cat spec/spec.yml 2>/dev/null | head -50 || echo "spec.yml not found"`

## Philosophy

**Specs should maximize inheritance.** Place tests in the earliest version where behavior exists. Later versions inherit automatically.

Inheritance breaks when:

1. API behavior changes intentionally (vulnerability fixed)
2. API behavior changes accidentally (refactoring side-effect)
3. Response format changes (schema difference)
4. New endpoints don't exist in base version

## Workflow

### Step 1: Check spec.yml

```bash
cat spec/spec.yml | grep -A20 "{version}:"
```

Look for:

- `inherits: {parent}` - inheritance chain
- `exclude:` - tests blocked from inheritance
- `tags:` - version-specific tags

### Step 2: Run ucsync

```bash
ucsync {version}
ucsync -n  # dry run to preview
```

Watch for:

- Files created with `~` prefix (inherited)
- Warnings about local overrides
- Missing source files

### Step 3: Run Tests

```bash
uctest {version}/
```

### Step 4: Analyze Failures

**If inherited test fails:**

1. Is this an intentionally fixed vulnerability? → Add to `exclude:`
2. Is this accidental behavior change? → Fix source code
3. Is this schema difference? → Consider standardization or exclude

**Key insight:** Code refactoring can ACCIDENTALLY fix vulnerabilities. Always investigate source code before assuming test is broken.

## Inheritance Health Indicators

**Healthy:**

- Most tests pass (inherited + local)
- Few exclusions, each documented with WHY
- `~` files match source versions

**Unhealthy:**

- Many exclusions without clear reasons
- Tests overridden locally that should inherit
- Failing inherited tests not in exclusion list

## Common Patterns

### Accidental Fix Pattern

```
v201: Vulnerability exists (test passes)
v202: Refactoring accidentally fixes it (test fails)
v203: Same code (test still fails)
```

**Solution:** Add exclusion at v202 with comment explaining accidental fix

### Intentional Fix Pattern

```
v301: Vulnerability introduced (exploit test passes)
v302: Fix applied (exploit test should fail)
```

**Solution:** Add exclusion at v302, ensure fixed.http passes

### Schema Difference Pattern

```
v201: Returns { "tip": "1.50" }  (string)
v301: Returns { "tip": 1.50 }   (number)
```

**Solution:** Standardize in source OR use resilient assertions

## Quick Commands

```bash
# Sync all versions
ucsync

# Sync specific version
ucsync v302

# Preview changes
ucsync -n

# Clean generated files
ucsync clean
```
