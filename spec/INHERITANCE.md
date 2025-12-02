# E2E Spec Inheritance Guide

This document captures lessons learned from migrating specs to v201 (base version) and troubleshooting inheritance issues across v201-v302.

## Core Principle: Port to Base, Exclude When Fixed

**Goal**: Maximize inheritance by placing tests in the earliest version where the functionality exists.

```
v201 (base)     ← PUT tests here when possible
  ↓ inherits
v202            ← exclude tests when behavior changes
  ↓ inherits
v203            ← inherits exclusions from v202
  ↓ inherits
...
```

**Benefits**:
- Fewer duplicate files to maintain
- Changes propagate automatically
- Clear documentation of when behavior changed

## Inheritance Chain: Authentication Confusion (r02)

| Version | Exercise | Intentional Vuln | Session Hijack Status |
|---------|----------|------------------|----------------------|
| v201 | e01_session_hijack | Session Hijack | VULNERABLE |
| v202 | e02_credit_top_ups | Credit Top-ups | ACCIDENTALLY FIXED |
| v203 | e03_fake_header_refund | Fake Header Refund | ACCIDENTALLY FIXED |
| v204 | e04_manager_mode | Manager Mode | INTENTIONALLY FIXED |
| v205 | e05_session_overwrite | Session Overwrite | FIXED (inherits v204) |
| v206 | e06_fixed_final_version | (all fixed) | FIXED |

### Why v202-v204 Accidentally Fixed Session Hijack

**e01 (VULNERABLE)** - `helpers.py`:
```python
# Both authenticators instantiated BEFORE any() iterates!
authenticators = [CustomerAuthenticator(), CredentialAuthenticator.from_basic_auth()]
return any(authenticator.authenticate() for authenticator in authenticators)
```
The `CredentialAuthenticator.from_basic_auth()` constructor sets `g.email` BEFORE `any()` even starts checking. If cookie auth succeeds, `g.email` is already poisoned.

**e02-e04 (FIXED)** - `helpers.py`:
```python
# Cookie auth checked FIRST, returns before Basic Auth instantiation
authenticator_from_cookie = CustomerAuthenticator()
if authenticator_from_cookie.authenticate():
    return True  # ← Returns BEFORE Basic Auth is instantiated

authenticator_from_basic_auth = CredentialAuthenticator.from_basic_auth()
```

**Lesson**: Subtle code refactoring can accidentally fix vulnerabilities. When tests fail, investigate whether the API behavior actually changed.

---

## spec.yml Exclusion Patterns

### When to Exclude Tests

1. **Vulnerability was fixed** (intentionally or accidentally)
2. **API signature changed** (e.g., new required parameter)
3. **Response format changed** (e.g., string vs number for tip)

### Exclusion Examples

```yaml
v202:
  inherits: v201
  tags: [r02, v202]
  exclude:
    # e02 accidentally fixed session hijack (auth flow refactored)
    - orders/list/get/vuln-session-hijack.http

v204:
  inherits: v203
  tags: [r02, v204]
  exclude:
    # e04 intentionally fixed session hijack (g.email set after password check)
    - orders/list/get/vuln-session-hijack.http

v301:
  inherits: v206
  tags: [r03, v301]
  exclude:
    # v301 requires restaurant_id parameter
    - cart/create/post/happy.http
    - cart/checkout/post/pollution.http
    # v301 returns tip as string "0.00" vs numeric 0
    - cart/checkout/post/validation.http
```

### Inheritance of Exclusions

Exclusions are **version-specific** and **don't cascade** automatically:
- v203 inherits from v202, so it gets v202's inherited files (minus v202's exclusions)
- If v203 needs the same exclusion, you can either:
  - Rely on v202's exclusion (v203 won't get the file because v202 excluded it)
  - Add explicit exclusion in v203 (clearer, but redundant)

---

## Common Failure Patterns When Porting

### 1. Import Path Breaks After Deletion

**Symptom**: `ref "X" not found` after deleting v205 duplicates

**Cause**: v205 files reference `happy.http` but file is now `~happy.http` (inherited)

**Fix**:
```http
# Before (broken)
# @import ./happy.http

# After (fixed)
# @import ./~happy.http
```

**Prevention**: After deleting files, run:
```bash
grep -r "@import.*happy\.http" spec/v205/  # Find non-~ imports
```

### 2. Error Message Mismatches

**Symptom**: `$(response).field("error") == Unauthorized` fails

**Cause**: Different versions return different error messages:
- e01-e04: "Unauthorized"
- e05+: "Authentication required"

**Fix**: Use generic assertions:
```http
# Before (fragile)
?? js $(response).field("error") == Unauthorized

# After (resilient)
?? js $(response).isError() == true
```

### 3. Vulnerability Test Fails in Later Version

**Symptom**: `vuln-*.http` test expects vulnerability but passes/fails unexpectedly

**Cause**: The vulnerability was fixed in this version

**Fix**: Add exclusion in spec.yml for this version

### 4. Obsolete Version-Specific Config Files

**Symptom**: `ucsync` fails with confusing errors

**Cause**: Old `spec/vXXX/spec.yml` files conflict with central `spec/spec.yml`

**Fix**: Delete version-specific spec.yml files:
```bash
rm spec/v205/spec.yml  # If exists
```

---

## Best Practices for .http File Design

### Design for Inheritance

**DO**:
- Use generic error assertions (`isError()`) not specific messages
- Reference helpers (`auth.basic()`) not hardcoded values
- Use `@forceRef` for state-changing dependencies
- Keep tests focused on one behavior

**DON'T**:
- Assert specific error message text
- Hardcode version-specific behaviors
- Mix concerns (happy path + auth + validation in one file)

### File Organization for Maximum Reuse

```
spec/v201/                    ← Base version
  cart/checkout/post/
    happy.http               ← Core success path
    authn.http               ← Auth boundary tests
    authz.http               ← Authorization tests
    validation.http          ← Input validation

spec/v205/                    ← Only version-specific tests
  cart/checkout/post/
    ~happy.http              ← Inherited (generated)
    ~authn.http              ← Inherited (generated)
    pollution.http           ← v205-specific test
```

### When to Create Version-Specific Override

Create a local file (not `~` prefixed) when:
1. The API signature changed
2. The expected response format changed
3. The test logic itself needs to differ

---

## Porting Checklist

When porting tests from vXXX to v201:

1. **Check if behavior exists in v201**
   - Does the endpoint exist?
   - Does it behave the same way?

2. **Copy and adjust the test**
   - Change tags from `vXXX` to `v201`
   - Verify imports work in v201 context

3. **Run tests against v201**
   ```bash
   uctest v201/path/to/test.http
   ```

4. **Delete the original from vXXX**
   - The file will be recreated as `~test.http` by ucsync

5. **Update spec.yml exclusions if needed**
   - If behavior differs in intermediate versions, add exclusions

6. **Run ucsync**
   ```bash
   uv run ucsync
   ```

7. **Verify inheritance chain**
   ```bash
   uctest v201 && uctest v202 && uctest v203 && uctest v204 && uctest v205
   ```

---

## Debugging Inheritance Issues

### Quick Diagnosis

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `ref X not found` | Import references deleted file | Change `X.http` to `~X.http` |
| Test passes in v201, fails in v202 | Behavior changed | Add exclusion in spec.yml |
| Vuln test fails | Vulnerability was fixed | Add exclusion |
| Wrong number of tests | Exclusions missing or wrong | Check spec.yml inheritance |
| ucsync fails | Old spec.yml in version dir | Delete version-specific spec.yml |

### Verification Commands

```bash
# Check what files exist in a version
ls spec/v205/cart/checkout/post/

# Check what's inherited (~ prefix) vs local
ls spec/v205/cart/checkout/post/*.http | grep -E "^[^~]"  # Local only

# Count tests per version
uctest v201 2>&1 | tail -1
uctest v202 2>&1 | tail -1

# Find all exclusions in spec.yml
grep -A5 "exclude:" spec/spec.yml
```

---

## Future Development Notes

### Extending to v303+, v4xx, v5xx

1. **New version series should inherit from the last "clean" version**
   - v301 inherits from v206 (last of r02 series)
   - v401 could inherit from v302 (last of r03 series)

2. **Document what each version fixes/changes in spec.yml comments**

3. **Keep vulnerability tests in base version, exclude in fixed versions**

4. **Run full test suite after adding new versions**
   ```bash
   uctest v201 v202 v203 v204 v205 v206 v301 v302
   ```
