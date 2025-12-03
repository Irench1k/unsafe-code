# Decision Trees

> When something goes wrong, use these trees to determine the correct fix.

---

## 1. Inherited Test Fails

```
Inherited test from vN fails in vN+1
│
├─→ Was behavior change documented in README?
│   │
│   ├─ YES → uc-spec-author: Create version-specific override
│   │         (Add new file, not ~prefixed)
│   │
│   └─ NO → Continue to next question...
│
├─→ Did refactoring accidentally fix the vulnerability?
│   │
│   │  How to check:
│   │  1. Diff source code: diff -r eNN eNN+1
│   │  2. Look for auth flow changes, early returns
│   │  3. Compare to vuln pattern in spec
│   │
│   ├─ YES → Add exclusion to spec.yml
│   │         Document WHY in comment
│   │         This is expected, not a bug
│   │
│   └─ NO → Continue to next question...
│
└─→ Is there a bug in the exercise code?
    │
    │  The test worked before. The code should match
    │  the intended behavior from the README.
    │
    └─ YES → uc-code-crafter: Fix source code
             Don't change the test!
```

---

## 2. "ref X not found" Error

```
Error: ref "X" not found in scope Y.http
│
├─→ Try tag-based execution first
│   │
│   │  uctest @orders v301/  (instead of uctest v301/orders/)
│   │
│   ├─ Works now → Path scope was too narrow
│   │              Cross-directory deps need full scan
│   │
│   └─ Still fails → Continue...
│
├─→ Does the @name X exist?
│   │
│   │  grep -r "@name X" spec/v301/
│   │
│   ├─ NOT FOUND → uc-spec-author: Create the named request
│   │              It simply doesn't exist
│   │
│   └─ FOUND → Check import chain...
│
├─→ Is the file defining X imported?
│   │
│   │  Check Y.http for @import statements
│   │  Trace chain: Y → _imports → parent → ...
│   │
│   ├─ Missing import → uc-spec-author: Add import statement
│   │
│   └─ Import exists → Check ~ prefix issue...
│
└─→ Is inherited file referencing wrong sibling?
    │
    │  In ~multi-tenant.http:
    │  # @import ./happy.http    ← WRONG
    │  # @import ./~happy.http   ← CORRECT
    │
    └─ YES → uc-spec-sync: Run ucsync to regenerate
```

---

## 3. Assertion Mismatch

```
Expected X but got Y
│
├─→ Is there a quotes issue?
│   │
│   │  ?? js $(response).field("status") == "delivered"  ← WRONG
│   │  ?? js $(response).field("status") == delivered    ← CORRECT
│   │
│   │  Right side is a literal, not JavaScript string
│   │
│   └─ YES → uc-spec-author: Remove quotes from RHS
│
├─→ Is it a type mismatch?
│   │
│   │  API returns "200" (string) vs 200 (number)
│   │  API returns "12.34" vs 12.34
│   │
│   ├─ YES → Decide: Standardize source or adjust spec?
│   │         If API inconsistency → Fix source code
│   │         If spec too strict → Adjust assertion
│   │
│   └─ NO → Continue...
│
├─→ Is it an assertion timing issue?
│   │
│   │  Both assertions run AFTER the request:
│   │  POST /refund
│   │  ?? js balance == 100  ← Runs after!
│   │  ?? js balance == 110  ← Also runs after!
│   │
│   │  Need to capture pre-state:
│   │  {{ exports.before = await user("x").balance(); }}
│   │  POST /refund
│   │  ?? js await user("x").balance() == {{before + 10}}
│   │
│   └─ YES → uc-spec-author: Add pre-state capture
│
└─→ Did the API actually change behavior?
    │
    ├─ Change is intentional (documented) → uc-spec-author: Update spec
    │
    └─ Change is accidental (bug) → uc-code-crafter: Fix source
```

---

## 4. Vulnerability Test Passes Unexpectedly

```
vuln-*.http test PASSES in version where vuln should be FIXED
│
├─→ Is the vulnerability actually fixed?
│   │
│   │  Run exploit manually against API
│   │  Check if attack still works
│   │
│   ├─ Vuln still exists → The test assertion is wrong
│   │                      uc-spec-author: Fix test logic
│   │
│   └─ Vuln is fixed → Why is test passing?
│
└─→ Test assertion is too weak
    │
    │  Test may check for 200 OK but not verify
    │  that unauthorized data was NOT returned
    │
    └─ uc-spec-author: Strengthen assertion
       Add check for what SHOULDN'T happen
```

---

## 5. Vulnerability Test Fails Unexpectedly

```
vuln-*.http test FAILS in version where vuln SHOULD EXIST
│
├─→ Was the vulnerability accidentally fixed?
│   │
│   │  Diff source code between versions
│   │  Look for:
│   │  - Auth flow changes
│   │  - Early returns
│   │  - Parameter handling changes
│   │
│   ├─ YES → Add exclusion to spec.yml
│   │         Document the accidental fix
│   │         This is common with refactoring
│   │
│   └─ NO → Continue...
│
├─→ Is the test environment incorrect?
│   │
│   │  - Database not seeded?
│   │  - Wrong server version running?
│   │  - Balance depleted from previous test?
│   │
│   └─ YES → Fix environment, re-run
│
└─→ Is the test itself broken?
    │
    │  - Wrong credentials?
    │  - Wrong endpoint?
    │  - Import chain broken?
    │
    └─ uc-spec-debugger: Trace the issue
```

---

## 6. When to Create Version-Specific Override

```
Need different behavior in vN+1
│
├─→ Is it a NEW endpoint?
│   │
│   └─ YES → Create new file in vN+1
│            Will be inherited forward
│
├─→ Is it a CHANGED API signature?
│   │
│   │  e.g., new required parameter
│   │  e.g., different response format
│   │
│   └─ YES → Create override in vN+1
│            (Same filename, no ~ prefix)
│            Original stays in vN for earlier versions
│
├─→ Is it a FIXED vulnerability?
│   │
│   └─ YES → Don't override - add exclusion
│            The vuln-*.http stays in base
│            Later versions exclude it
│
└─→ Is it just different test data?
    │
    └─ NO override needed
       Extract shared logic to _fixtures.http
       Use @ref to share state
```

---

## 7. Fix Code or Fix Test?

```
Something doesn't work
│
├─→ Is this an INHERITED test?
│   │
│   │  File has ~ prefix or comes from parent in spec.yml
│   │
│   ├─ YES → DEFAULT: Fix the CODE
│   │         The test worked in earlier version
│   │         Code should maintain backward compatibility
│   │         EXCEPTION: README documents intentional change
│   │
│   └─ NO → Continue...
│
├─→ Is this a NEW test for NEW feature?
│   │
│   └─ YES → Check test assertion logic
│            May need adjustment
│
├─→ Does README describe intended behavior?
│   │
│   ├─ Test matches README → Fix CODE
│   │
│   └─ Test doesn't match README → Fix TEST
│
└─→ When in doubt:
    │
    └─ Ask: "What was working before?"
       If test passed before → Fix code
       If test is new → Verify assertion
```

---

## Quick Reference: Agent Selection

| Situation | Agent |
|-----------|-------|
| Run tests | uc-spec-runner |
| Diagnose failures | uc-spec-debugger |
| Write/fix tests | uc-spec-author |
| Manage inheritance | uc-spec-sync |
| Fix source code | uc-code-crafter |
| Create demos | uc-exploit-narrator |
| Polish docs | uc-docs-editor |
| Commit changes | commit-agent |
