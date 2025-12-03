# Task Runbooks

> Compact workflow checklists for common Unsafe Code Lab tasks.
> See `AGENTS.md` for full context and decision trees.

---

## 1. Extend E2E Specs to Next Exercise

**Goal**: vN → vN+1 with maximum inheritance

```
1. READ section README (authoritative plan)
2. RUN uctest vN/ (ensure baseline is green)
3. UPDATE spec.yml:
   - Add vN+1 entry with `inherits: vN`
   - Add version-specific tags
4. RUN ucsync (generate inherited files)
5. RUN uctest vN+1/
6. FOR EACH failure:
   - Is behavior change documented in README?
     YES → uc-spec-author adjusts spec
     NO  → uc-code-crafter fixes code
   - Is it "ref not found"?
     → Check imports, run ucsync again
7. VERIFY all green
8. commit-agent
```

**Agents**: uc-spec-sync → uc-spec-runner → uc-spec-debugger → uc-spec-author OR uc-code-crafter

---

## 2. Add New Vulnerability Exercise

**Goal**: Create complete new exercise with code, specs, and demos

```
1. uc-vulnerability-designer:
   - Read section README
   - Design: What vuln? What fix? What new feature?
   - Output: Design spec document

2. uc-code-crafter:
   - Clone previous exercise directory
   - Implement design spec
   - Add @unsafe annotations
   - Ensure backward compatible (usually)

3. uc-spec-author + uc-spec-sync:
   - Update spec.yml for new version
   - Create specs for new endpoints/behavior
   - Run ucsync

4. uc-spec-runner:
   - Run uctest until green
   - Debug failures as needed

5. uc-exploit-narrator:
   - Create .exploit.http (demonstrates vuln)
   - Create .fixed.http (shows fix works)
   - Follow character rules, one assert per test

6. uc-docs-editor:
   - Polish any README changes
   - Ensure behavioral language, not jargon

7. uv run docs generate --target [path]

8. commit-agent:
   - Run full verification
   - Commit with clear message
```

**Agents**: uc-vulnerability-designer → uc-code-crafter → uc-spec-author → uc-spec-sync → uc-spec-runner → uc-exploit-narrator → uc-docs-editor → commit-agent

---

## 3. Fix Failing E2E Specs (Enhanced)

**Goal**: Diagnose and fix spec failures correctly

### Diagnostic Flow
```
uctest fails
    │
    ├─ 1. CHECK SERVER LOGS FIRST
    │     uclogs --since 5m
    │     Look for: 500 errors, exceptions, stack traces
    │
    ├─ 2. CHECK README INTENT
    │     Read section README.md
    │     What behavior is SUPPOSED to exist?
    │
    └─ 3. DECIDE: Code or Spec?
          ├─ README says X, code does X, spec expects Y → Fix spec
          ├─ README says X, code does Y, spec expects X → Fix code
          └─ README unclear → Check with uc-vulnerability-designer
```

### Example: 500 Error Investigation
```bash
# Step 1: Run failing test
uctest v301/cart/checkout/post/happy.http
# Output: 500 Internal Server Error

# Step 2: Check server logs
uclogs --since 5m | grep -i error
# Found: TypeError in auth/decorators.py line 42

# Step 3: Read README to understand intent
cat vulnerabilities/.../r03_authorization_confusion/README.md
# Intent: "v301 should have body_override vulnerability"

# Step 4: Decide
# Code has bug unrelated to vulnerability → Fix code
```

---

## 4. Maximize Inheritance (Backport Specs)

**Goal**: Move tests to earliest valid version for max DRYness

### Detailed Workflow

#### Step 1: Find Backport Candidates
```bash
# Compare test coverage between versions
diff <(ls spec/v302/cart/checkout/post/) <(ls spec/v301/cart/checkout/post/)

# Find tests that exist in v302 but not v301
comm -23 <(ls spec/v302/cart/checkout/post/*.http | xargs -n1 basename) \
         <(ls spec/v301/cart/checkout/post/*.http | xargs -n1 basename)
```

#### Step 2: Verify Behavior Exists in Earlier Version
```bash
# Start the earlier version's server
cd vulnerabilities/.../e01_*/  && docker compose up -d

# Run the test against it manually
uctest --target-version v301 spec/v302/cart/checkout/post/happy.http
```

#### Step 3: Port Test File
```bash
# Copy to earlier version
cp spec/v302/cart/checkout/post/new-feature.http \
   spec/v301/cart/checkout/post/new-feature.http

# Update any version-specific refs in the file
sed -i 's/v302/v301/g' spec/v301/cart/checkout/post/new-feature.http
```

#### Step 4: Delete Original and Regenerate
```bash
# Remove from later version (will become inherited)
rm spec/v302/cart/checkout/post/new-feature.http

# Regenerate inheritance
ucsync

# Verify both versions pass
uctest v301/cart/checkout/post/ && uctest v302/cart/checkout/post/
```

### Example: Split Monolithic Test File
If v302 has `cart-tests.http` with 10 tests but only 3 apply to v301:

```bash
# 1. Extract common tests to v301
grep -A20 "### Test 1\\|### Test 2\\|### Test 3" spec/v302/cart-tests.http \
  > spec/v301/cart-common.http

# 2. Keep v302-specific tests
# Edit v302/cart-tests.http to only have v302-specific tests

# 3. Add import in v302
echo "# @import ./~cart-common.http" >> spec/v302/cart-tests.http

# 4. Run ucsync
ucsync
```

**Agents**: uc-spec-author (port files) → uc-spec-sync (update inheritance) → uc-spec-runner (verify)

---

## 5. Review Exercise Quality

**Goal**: Comprehensive quality check on exercise set

```
1. READ section README
   - Understand planned evolution
   - Note which vulns/fixes per version

2. RUN uctest for each version
   - All should be green
   - Note inheritance health

3. VALIDATE interactive demos:
   - httpyac [file].http -a for each
   - Check character logic (attacker uses own creds)
   - Check one assert per test
   - Check narrative quality

4. CROSS-REFERENCE:
   - Diff source code between versions
   - Compare actual changes to README plan
   - Flag any accidental fixes

5. CHECK variety:
   - Different attackers across examples?
   - Different impacts?
   - No repetition of same pattern 4+ times?

6. REPORT:
   - Versions reviewed
   - Specs passed/failed
   - Demo quality issues
   - Recommendations
```

**Agents**: uc-spec-runner → uc-exploit-narrator (review) → uc-docs-editor (polish)

---

## 6. Fix Vulnerability Chain

**Goal**: Ensure vuln appears/disappears correctly across versions

```
1. IDENTIFY the vulnerability and its lifecycle:
   - Which version introduces it?
   - Which version fixes it?
   - Is fix intentional or accidental?

2. FOR EACH version in chain:
   a. Check source code
      → Is vuln present where it should be?
      → Is vuln absent where it should be?

   b. If wrong:
      → uc-code-crafter adjusts implementation

   c. Check specs
      → vuln-*.http should pass where vuln exists
      → vuln-*.http should be excluded where fixed

3. UPDATE spec.yml exclusions with documentation

4. RUN full chain: uctest v301 v302 v303 ...

5. UPDATE interactive demos if needed
```

---

## 7. Refresh Interactive Demos (Enhanced)

**Goal**: Improve student-facing exploit demonstrations

### Workflow

```
1. READ section README + exercise code

2. FOR EACH demo pair (.exploit.http + .fixed.http):

   a. VERIFY technical correctness:
      → httpyac [file].http -a
      → Does exploit actually work?
      → Does fix actually work?

   b. CHECK character logic:
      → Attacker uses OWN credentials
      → Right character for attack type
      → SpongeBob NEVER attacks

   c. CHECK narrative quality:
      → Behavioral annotations (not jargon)
      → Business impact clear
      → Fun without cringe
      → One assert per test

   d. CHECK variety:
      → Not same impact as last 3 examples
      → Rotate attackers/victims/impacts

3. uc-exploit-narrator rewrites as needed

4. uc-docs-editor polishes language

5. RE-RUN demos to verify
```

### Storytelling Templates

#### Template A: Coworker Grudge (Squidward → SpongeBob)
```http
### SpongeBob logs in to check his messages
POST {{host}}/auth/login
Content-Type: application/json
{"email": "spongebob@krusty-krab.sea", "password": "bikinibottom"}
?? status == 200

### SpongeBob reads his private messages (normal use)
GET {{host}}/messages
Authorization: {{spongebob_auth}}
?? status == 200

### --- ATTACK BEGINS ---

### Squidward logs in with his own credentials
POST {{host}}/auth/login
Content-Type: application/json
{"email": "squidward@krusty-krab.sea", "password": "clarinet123"}
?? status == 200

### EXPLOIT: Squidward reads SpongeBob's messages
GET {{host}}/messages?user=spongebob
Authorization: {{squidward_auth}}
?? status == 200

# IMPACT: Squidward can see SpongeBob's private recipe notes!
```

#### Template B: Business Rival (Plankton → Krabs/Patrick)
```http
### Mr. Krabs reviews today's sales (normal use)
GET {{host}}/restaurant/1/sales
X-API-Key: {{krabs_api_key}}
?? status == 200

### --- ATTACK BEGINS ---

### EXPLOIT: Plankton uses Chum Bucket key on Krusty Krab endpoint
GET {{host}}/restaurant/1/sales
X-API-Key: {{chum_bucket_api_key}}
?? status == 200

# IMPACT: Plankton just stole Krusty Krab's sales data!
```

#### Template C: VIP Target (Any → Patrick)
```http
### Patrick checks his VIP credit balance
GET {{host}}/account/credits
Authorization: {{patrick_auth}}
?? status == 200

### --- ATTACK BEGINS ---

### EXPLOIT: Plankton transfers Patrick's credits to himself
POST {{host}}/credits/transfer
Authorization: {{plankton_auth}}
Content-Type: application/json
{"from_user": "patrick", "to_user": "plankton", "amount": 100}
?? status == 200

# IMPACT: Plankton stole $100 from Patrick's account!
```

### Variety Rotation Checklist
By example 4-5, rotate at least 2 of these:

| Aspect | Options |
|--------|---------|
| Attacker | Squidward, Plankton, (Sandy for advanced) |
| Victim | SpongeBob, Mr. Krabs, Patrick |
| Impact | Read data, Modify data, Delete data, Transfer money |
| Resource | Messages, Orders, Menu, Credits, Sales |

---

## Quick Commands Reference

```bash
# E2E Specs
uctest vNNN/                    # Run all tests for version
uctest @tag vNNN/               # Run tests with tag
uctest -k vNNN/                 # Keep going after failures
uctest -v vNNN/path/            # Verbose output
uctest --show-plan vNNN/        # Show execution plan

# Inheritance
ucsync                          # Regenerate inherited files
ucsync -n                       # Preview changes (dry run)
ucsync clean                    # Remove generated files

# Interactive Demos
httpyac file.http -a            # Run demo

# Debugging
uclogs                          # Docker logs
grep -r "@name X" spec/vNNN/    # Find named request
grep -r "@import" spec/vNNN/    # Check import chains
```
