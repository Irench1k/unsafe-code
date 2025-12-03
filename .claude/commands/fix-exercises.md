---
description: "Comprehensive exercise implementation using TDD workflow"
model: opus
argument-hint: [section] [exercise-range|all]
---

# Fix Exercises - Comprehensive Exercise Implementation

Think carefully and methodically about this TDD workflow. Each step must complete before moving to the next.

## Health Check
!`docker compose ps 2>/dev/null | head -5 || echo "Docker status unknown"`
!`uclogs --since 30m 2>/dev/null | grep -c -i error || echo "0 recent errors"`

## Required Context

Load these files before proceeding:
- [AGENTS.md](AGENTS.md) - Single source of truth for invariants
- [docs/ai/runbooks.md](docs/ai/runbooks.md) - Workflow checklists

**Purpose**: Fully implement and validate exercise(s) in a tutorial section, ensuring source code, interactive demos, and e2e specs all work correctly using TDD approach.

**Usage**: `/fix-exercises [section] [exercise-range]`

**Examples**:
- `/fix-exercises r03 e01-e03` - Fix exercises 1-3 in r03
- `/fix-exercises r03 e07` - Fix just exercise 7
- `/fix-exercises r03 all` - Fix all exercises in r03

---

## Definition of Done

For EACH exercise specified, ALL of the following must be complete:

### 1. Source Code ✅
- [ ] **Vulnerability implemented** - The intentional vuln from README actually works
- [ ] **Previous vuln fixed** - The previous exercise's vuln is properly patched
- [ ] **Code is production-quality** - No obvious hacks or shortcuts
- [ ] **@unsafe annotations present** - Mark vulnerable code sections

### 2. Interactive Demos (httpyac) ✅
- [ ] **`.exploit.http` exists and works** - Demonstrates CURRENT vuln
- [ ] **`.fixed.http` exists and works** - Demonstrates PREVIOUS vuln is fixed
- [ ] **Assertions are CORRECT** - ONE per request, actually execute (not interpreted as request body)
- [ ] **DB setup included** - Calls platform.seed() as needed
- [ ] **Student-facing language** - Behavioral descriptions, not implementation details
- [ ] **Character logic correct** - Attacker uses THEIR credentials
- [ ] **Run successfully** - `httpyac file.http -a --all` passes

### 3. E2E Specs (uctest) ✅
- [ ] **`vuln-*.http` exists** - Tests CURRENT vulnerability
- [ ] **`vXXX.http` exists** - Tests PREVIOUS vuln is now fixed (in next version)
- [ ] **Uses utils.cjs helpers** - platform.seed(), auth.*, $(response).*
- [ ] **Proper imports** - @import ../_imports.http
- [ ] **Correct tags** - @tag endpoint, r03, version
- [ ] **@forceRef chains** - Dependencies properly sequenced
- [ ] **Passes in own version** - `uctest vXXX/` succeeds
- [ ] **Inherits properly** - ucsync generates ~vXXX.http in later versions
- [ ] **Inherited specs pass** - `uctest vXXX+1/` includes and passes ~vXXX.http

### 4. Quality Checks ✅
- [ ] **No server errors** - `uclogs --since 30m` shows no errors
- [ ] **README accurate** - Vulnerability descriptions match actual behavior
- [ ] **No technical jargon** - All student-facing content uses behavioral language
- [ ] **Variety in impacts** - Each exploit has distinct business consequence

---

## TDD Workflow (MANDATORY)

**DO NOT** write tests that pass against broken code. **DO** write tests that fail, then fix code.

### Step 1: Understand Intent (10 min per exercise)
**Actions**:
1. Read `r03_authorization_confusion/README.md` for this exercise
2. Identify:
   - What vulnerability SHOULD exist?
   - What previous vulnerability SHOULD be fixed?
   - What's the natural SaaS evolution story?
   - What endpoints are involved?

**Output**: Clear understanding documented in plan

### Step 2: Write Failing Tests (30-45 min per exercise)
**Actions**:
1. Write `.exploit.http` that DEMONSTRATES the vuln (will fail if vuln not implemented)
2. Write `.fixed.http` that VERIFIES previous vuln is fixed (will fail if not fixed)
3. Write `vuln-*.http` e2e spec for CURRENT vuln
4. Write `vXXX.http` e2e spec verifying PREVIOUS vuln is fixed
5. **RUN TESTS** - expect failures!
   ```bash
   httpyac e01/e01_dual_auth_refund.exploit.http -a --all
   httpyac e01/e01_dual_auth_refund.fixed.http -a --all
   uctest v301/orders/refund-status/patch/vuln-dual-auth-refund.http
   uctest v302/orders/refund-status/patch/v302.http
   ```

**Critical**: If tests pass immediately, they're testing the WRONG thing!

### Step 3: Identify Source Files (15 min per exercise)
**Actions**:
1. Find route handlers for affected endpoints
2. Find authorization decorators/middleware
3. Find data models if needed
4. Document file paths in plan

**Pattern**: Routes usually in `vulnerabilities/.../routes/`, decorators in `decorators.py` or `auth.py`

### Step 4: Implement Vulnerability (45-60 min per exercise)
**Actions**:
1. Modify source code to introduce the intentional vulnerability
2. Add `@unsafe` annotations marking vulnerable code
3. **RUN `.exploit.http`** - should now PASS
4. **RUN `vuln-*.http`** - should now PASS
5. Check uclogs for errors

**Critical**: Don't move to next step until exploit tests pass!

### Step 5: Fix Previous Vulnerability (45-60 min per exercise)
**Actions**:
1. Modify source code to fix the PREVIOUS exercise's vulnerability
2. **RUN `.fixed.http`** - should now PASS
3. **RUN `vXXX.http`** - should now PASS
4. **RUN previous `vuln-*.http`** in current version - should now FAIL (vuln is fixed)
5. Check uclogs for errors

**Critical**: Verify fix actually works, don't just make assertions pass!

### Step 6: Test Inheritance (15 min per exercise)
**Actions**:
1. Run `ucsync` to generate inherited specs
2. Verify `~vXXX.http` appears in later versions
3. Run `uctest vXXX+1/` to verify inherited spec passes
4. If failures, debug before proceeding

### Step 7: Final Validation (15 min per exercise)
**Actions**:
1. Run full demo suite for this exercise
2. Run full e2e spec suite for this version
3. Check server logs for any errors
4. Verify README descriptions match actual behavior
5. Commit changes (small, atomic commit per exercise)

**Commands**:
```bash
# Interactive demos
httpyac http/e01/*.http -a --all

# E2E specs
uctest v301/

# Server health
uclogs --since 30m | grep -i error
```

---

## Agent Delegation

Use specialized agents for different tasks:

| Task | Agent | Why |
|------|-------|-----|
| Write/fix .exploit.http | uc-exploit-narrator | Knows SpongeBob narrative, behavioral language |
| Write/fix .fixed.http | uc-exploit-narrator or uc-docs-editor | Same narrative skills |
| Write e2e specs | uc-spec-author | Knows uctest conventions, utils.cjs helpers |
| Run e2e specs | uc-spec-runner | Quick execution with smart failure interpretation |
| Debug spec failures | uc-spec-debugger | Diagnoses root cause (code vs spec issue) |
| Implement vuln code | uc-code-crafter | Writes production-quality vulnerable code |
| Review code quality | code-reviewer | Catches issues before finalizing |
| Commit changes | commit-agent | Runs verification gates before committing |

**Orchestration**: Use `uc-maintainer` for complex multi-exercise tasks.

---

## Common Pitfalls

### ❌ Don't Do This:
- Write assertions that always pass (not actually testing anything)
- Fudge tests to match broken code
- Skip TDD and implement code first
- Use technical jargon in student-facing demos
- Have attacker use victim's credentials
- Forget to add DB setup to demos
- Create specs that don't actually fail when vuln exists
- Skip inheritance testing
- Commit without running full test suite

### ✅ Do This Instead:
- Write assertions that fail until code is fixed
- Fix code to make tests pass
- Always TDD: test → fail → fix → pass
- Use behavioral, SpongeBob-universe language
- Attacker always uses THEIR OWN credentials
- Add `platform.seed()` calls to demos that need DB state
- Verify specs actually test the vulnerability
- Run ucsync and test ~vXXX.http after each exercise
- Full validation before committing

---

## httpyac Assertion Gotchas

**Critical**: httpyac assertions have specific syntax that's easy to get wrong.

### ✅ CORRECT (one assertion per request):
```http
GET /orders
X-API-Key: {{chum_bucket_api_key}}

?? status == 200
```

### ❌ WRONG (multiple assertions treated as request body):
```http
GET /orders
X-API-Key: {{chum_bucket_api_key}}

?? status == 200
?? js response.parsedBody.length > 0
```

### ✅ CORRECT (use js assertion for multiple checks):
```http
GET /orders
X-API-Key: {{chum_bucket_api_key}}

?? js response.status === 200 && response.parsedBody.length > 0
```

**Debugging**: Run with `httpyac file.http -a --all --verbose` to see which assertions execute.

**Pattern**: ONE assertion per HTTP request block. Combine checks using `&&` in js assertions.

---

## File Structure Reference

```
r03_authorization_confusion/
├── README.md                              [READ: Vulnerability descriptions]
├── vXXX/                                  [Source code for each version]
│   ├── routes/                            [Endpoint handlers]
│   ├── decorators.py or auth.py           [Authorization logic]
│   └── models.py                          [Data models]
├── http/                                  [Interactive demos]
│   ├── common/setup.http                  [Shared setup]
│   ├── e01/
│   │   ├── e01_*.exploit.http             [Demonstrates vuln]
│   │   └── e01_*.fixed.http               [Demonstrates fix]
│   └── ...
└── spec/                                  [E2E specs]
    ├── v301/
    │   └── orders/refund-status/patch/
    │       ├── vuln-dual-auth-refund.http [Tests v301 vuln]
    │       └── ...
    ├── v302/
    │   └── orders/refund-status/patch/
    │       ├── ~vuln-dual-auth-refund.http [Inherited (excluded)]
    │       ├── v302.http                   [Tests v301 fix]
    │       └── ...
    └── ...
```

---

## Required Reading

Before starting, read these files:

1. **AGENTS.md** - Single source of truth for invariants
2. **docs/ai/runbooks.md** - Workflow checklists
3. **r03_authorization_confusion/README.md** - Vulnerability descriptions
4. **spec/utils.cjs** - Helper functions for e2e specs
5. **.claude/skills/http-e2e-specs.md** - E2E spec conventions
6. **.claude/skills/http-interactive-demos.md** - Demo conventions
7. **.claude/skills/spongebob-characters.md** - Character rules

---

## Success Criteria

**Per Exercise**:
- [ ] `.exploit.http` passes (demonstrates vuln)
- [ ] `.fixed.http` passes (demonstrates previous fix)
- [ ] `vuln-*.http` passes in vulnerable version
- [ ] `vXXX.http` passes in fixed version
- [ ] Source code implements vuln correctly
- [ ] Source code fixes previous vuln correctly
- [ ] No server errors in uclogs
- [ ] Inheritance works (ucsync + uctest)

**Per Section**:
- [ ] All exercises meet per-exercise criteria
- [ ] Full interactive demo suite passes
- [ ] Full e2e spec suite passes for all versions
- [ ] README matches actual implementation
- [ ] Commits are atomic and well-documented

---

## Time Estimates

Per exercise (assuming moderate complexity):
- Understand intent: 10 min
- Write failing tests: 30-45 min
- Identify source files: 15 min
- Implement vulnerability: 45-60 min
- Fix previous vulnerability: 45-60 min
- Test inheritance: 15 min
- Final validation: 15 min
- **Total: 2.5-3.5 hours per exercise**

For r03 (7 exercises): **17-25 hours total**

**Parallelization**: Some exercises can be worked on in parallel if they don't depend on each other's fixes.

---

## Next Steps

When this command is invoked:

1. **Parse arguments** to identify section and exercise range
2. **Load context** (AGENTS.md, runbooks.md, section README)
3. **For each exercise**, follow TDD workflow above
4. **Delegate to specialized agents** as needed
5. **Report progress** clearly to user
6. **Final validation** before marking complete

**Autonomous Operation**: This command should run with minimal user interaction. Ask questions only when genuinely ambiguous - don't ask for confirmation at every step.