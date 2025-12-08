# Task Runbooks

Compact, authoritative workflow checklists for common Unsafe Code Lab tasks. Use alongside `docs/ai/decision-trees.md` when diagnosing.

---

## 1. Review & Fix Failing Demo
**Goal**: Make a student-facing demo pass for the right reasons.
```
1) Run with detail: ucdemo <target> --bail -v
2) Classify failure:
   - 500 error → usually missing operator or malformed body
   - Assertion mismatch → quotes on RHS or real behavior bug
   - Undefined var/import → missing capture or @import
   - Connection refused → docker not running
3) Check logs: uclogs --tail=50
4) Decide root cause:
   - Syntax issue → fix demo file (see http-syntax + http-demos)
   - Behavior issue → fix app code
5) Re-run ucdemo target (expect pass)
```

---

## 2. Fix Failing E2E Specs (Enhanced)
**Goal**: Diagnose and correct spec failures without weakening coverage.
```
1) Run failing file verbose: uctest <path> -v
2) Check inheritance: ucsync <version> -n (is it ~ file?)
3) Read README intent (section + curriculum)
4) Decide: code vs spec vs exclusion
   - Inherited test → default fix code unless README says behavior changed
   - New test → verify assertion logic
5) If "ref not found": trace @name + imports; regenerate ucsync
6) Apply fix; rerun ucsync (if needed) + uctest
```
Use decision trees for deeper branching.

---

## 3. Extend E2E Specs to Next Exercise
**Goal**: vN → vN+1 with maximum inheritance.
```
1) Read section README (authoritative plan)
2) uctest vN/ (baseline green)
3) Update spec.yml: add vN+1 with inherits: vN + tags
4) ucsync
5) uctest vN+1/
6) For each failure: README alignment? code vs spec?
7) Verify all green
8) commit-agent
```

---

## 4. Add New Vulnerability Exercise
**Goal**: Complete new exercise (code + specs + demos) via TDD.
```
1) content-planner: read README; design vuln/fix/new feature
2) code-author: clone previous exercise; add @unsafe; keep backward compatibility
3) spec-author/spec-runner: update spec.yml, create specs, run ucsync
4) spec-runner: run uctest until green
5) demo-author: write .exploit.http + .fixed.http (one assert each)
6) docs-author: polish README language (behavioral)
7) uv run docs generate --target [path]
8) commit-agent: full verification
```

---

## 5. Maximize Inheritance (Backport Specs)
**Goal**: Move tests to earliest valid version to reduce overrides.
```
1) Find duplicate overrides:
   find spec/v3* -name "*.http" ! -name "~*" ! -name "_*"
2) Analyze lifecycle (which versions need behavior)
3) Move canonical test to earliest valid version
4) Add exclusions where behavior genuinely diverges
5) Split files by lifecycle if assertions change midstream
6) ucsync; uctest across versions
```

---

## 6. Review Exercise Quality
**Goal**: Holistic quality check for a version set.
```
1) Read section README (planned evolution)
2) ucdiff r03 (overview of all changes in section)
3) Run uctest for each version (inheritance health)
4) Validate demos:
   - ucdemo r03 -k
   - Attacker uses own creds; one assert; narrative quality
5) ucdiff r03 -e routes.py (track file evolution for drift)
6) Cross-reference code diffs vs README; flag accidental fixes
7) Check variety (attackers, impacts, targets)
8) Report: versions reviewed, spec status, demo issues, recommendations
```

---

## 7. Fix Vulnerability Chain
**Goal**: Ensure vuln appears/disappears in correct versions.
```
1) Identify vuln lifecycle (introduced vs fixed)
2) ucdiff r03 -e [vuln-file].py (see how file evolved)
3) For each version:
   a) Check source: vuln present/absent as intended?
   b) Fix code if wrong
   c) Check specs: vuln-*.http present where vuln exists; excluded where fixed
4) Update spec.yml exclusions with rationale
5) Run chain: uctest v301 v302 v303 ...
6) Update demos if lifecycle changed
```

---

## 8. Refresh Interactive Demos
**Goal**: Improve student-facing exploit demonstrations.
```
1) Read section README + exercise code
2) For each exploit/fix pair:
   - Verify technically (`ucdemo`)
   - Check character logic (attacker owns creds)
   - Check narrative (behavioral impact, no jargon)
   - Ensure variety and one assert per request
3) Rewrite as needed; re-run demos
```
Storytelling templates (keep handy):
- Coworker grudge (Squidward → SpongeBob)
```
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
- Business rival (Plankton → Krabs/Patrick)
```
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
- VIP target (Plankton → Patrick)
```
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
See `docs/ai/characters.md` for cast rules.

---

## 9. Debug State Issues in Demos
**Goal**: Resolve flakiness when demos pass alone but fail in sequence.
```
1) Reset explicitly:
   {{ await seedBalance("v305", "plankton@chum-bucket.sea", 100); }}
2) Verify cookie isolation (httpyac.config.js: cookieJarEnabled=false)
3) Check request order for hidden dependencies
4) Isolate by running single file: `ucdemo path/to/demo.http -v`
5) Add temporary diagnostics: console.log(JSON.stringify(response.parsedBody))
```
Remove diagnostics once stable.

---

## 10. Pre-Commit Verification
**Goal**: Ensure changes are validated before committing.
```
Demos changed:
  ucdemo <scope>  # affected demos
  ucdemo <section> -k  # if common files changed
Specs changed:
  ucsync
  uctest <version>/
  uclint <version>
Code changed:
  ucup (if needed)
  uctest <version>/ -k
  ucdemo <section> -k
  uclogs --tail=100
Docs changed:
  uv run docs verify -v
```

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
ucdemo r03                      # Run all demos in section
ucdemo r03/e07                  # Run specific exercise demos

# Exercise Diff
ucdiff v307                     # Compare with previous (v306)
ucdiff v306..v307               # Compare two versions
ucdiff r03                      # Overview of section changes
ucdiff r03 -e routes.py         # Track file evolution
ucdiff v307 --check-specs       # Warn if specs missing
ucdiff v306..v307 --json        # Machine-readable output

# Debugging
uclogs                          # Docker logs
grep -r "@name X" spec/vNNN/    # Find named request
grep -r "@import" spec/vNNN/    # Check import chains
```
