---
description: Bootstrap a new exercise - scaffold code, demos, and specs from previous exercise
model: opus
argument-hint: [version]
allowed-tools: Bash(*), Bash
---

# Bootstrap New Exercise: $ARGUMENTS

---

## ⛔⛔⛔ MANDATORY RULES ⛔⛔⛔

### 1. PLAN MODE CHECK

**IF Plan Mode is active → STOP IMMEDIATELY.**

```
ERROR: This command is incompatible with Plan Mode.
Please restart without Plan Mode enabled.
```

### 2. BUILT-IN AGENTS ARE BANNED

| Banned Agent | Why |
|--------------|-----|
| `Explore` | ❌ Bypasses our specialized agents |
| `Plan` | ❌ Interferes with command workflow |
| `general-purpose` | ❌ No domain skills |

### 3. MODEL ENFORCEMENT

**ALWAYS pass `model: opus` when spawning subagents.**

### 4. I NEVER WRITE .HTTP FILES

**DELEGATE ALL .http file creation to `demo-author` or `spec-author`.**

I will get the syntax wrong. The specialized agents have skills loaded for this.

### 5. DEMOS SHOULD FAIL - THIS IS CORRECT

**DO NOT chase green metrics.** TDD means demos assert what SHOULD exist but DOESN'T YET.

- ✅ Demos failing = correct (vulnerability not implemented yet)
- ✅ Specs passing = correct (inherited behavior unchanged)
- ❌ Silencing failures = FORBIDDEN
- ❌ Implementing functionality = NOT MY JOB

---

## My Mission

I scaffold a **new exercise** from the previous one:

1. **Copy exercise source code** (cp -r with adjustments)
2. **Wire into routing** (config.py, routes.py)
3. **Create demo directory** with draft .http files
4. **Update spec.yml** for inheritance

**Definition of Done:**
- ✅ Exercise code compiles/runs
- ✅ E2E specs pass (inherited, unchanged behavior)
- ✅ Demo files exist (but FAIL - TDD style)
- ❌ NO vulnerability implementation
- ❌ NO silencing of demo failures

---

## Phase 1: Parse Version Argument

**Input:** `$1` (e.g., `v403`, `v501`)

Extract:
- **Section number**: `{version[1]}` (e.g., `v403` → `4`, `v501` → `5`)
- **Exercise number**: `{version[2:]}` (e.g., `v403` → `03`, `v501` → `01`)
- **Section prefix**: `r0{section}` (e.g., `r04`, `r05`)
- **Exercise prefix**: `e{exercise}` (e.g., `e03`, `e01`)

**Determine source version:**
- Same section (e.g., `v403`): Source = previous in section (`v402`)
- New section first exercise (e.g., `v501`): Source = last exercise in previous section

---

## Phase 2: Locate Directories

### Project Structure

```
vulnerabilities/python/flask/confusion/webapp/
├── r01_authentication_confusion/
│   ├── e01_session_vs_basic/
│   ├── e02_.../
│   ├── http/
│   │   ├── common/
│   │   │   └── setup.http
│   │   ├── e01/
│   │   │   ├── e01_*.exploit.http
│   │   │   ├── e01_*.fixed.http
│   │   │   └── e01_*.intended.http
│   │   └── .httpyac.js          # ⚠️ CRITICAL - don't forget!
│   ├── routes.py                # Blueprint imports
│   └── README.md
├── r02_.../
├── r03_.../
└── r04_cardinality_confusion/
    ├── e01_coupon_stacking/
    ├── e02_zero_quantity/
    ├── e03_duplicate_coupons/
    ├── http/
    │   ├── common/
    │   │   └── setup.http
    │   ├── e01/
    │   ├── e02/
    │   ├── e03/
    │   └── .httpyac.js          # ⚠️ CRITICAL
    ├── routes.py
    └── README.md
```

### Key Files to Locate

| File | Purpose | Action |
|------|---------|--------|
| `r{NN}_*/e{MM}_*/` | Exercise source code | cp -r from previous |
| `r{NN}_*/e{MM}_*/config.py` | Version string | Update version |
| `r{NN}_*/routes.py` | Blueprint wiring | Add import + registration |
| `r{NN}_*/http/e{MM}/` | Demo directory | Create + scaffold |
| `r{NN}_*/http/.httpyac.js` | httpyac config | Verify exists (don't touch) |
| `r{NN}_*/http/common/setup.http` | Shared setup | Verify exists (don't touch) |
| `spec/spec.yml` | E2E inheritance | Add new version entry |

---

## Phase 3: Execute Bootstrap

### 3.1 Copy Exercise Source Code

```bash
# Determine source and target directories
SOURCE_EXERCISE="vulnerabilities/python/flask/confusion/webapp/r0{N}_*/e{PREV}_*/"
TARGET_EXERCISE="vulnerabilities/python/flask/confusion/webapp/r0{N}_*/e{NEW}_*/"

# Copy with new name (exercise name from README)
cp -r "$SOURCE_EXERCISE" "$TARGET_EXERCISE"
```

**After copy, update:**
- `config.py`: Change version string (e.g., `"v402"` → `"v403"`)
- `config.py`: Change name string to match README description

### 3.2 Wire Into Section Routes

**Read `r{NN}_*/routes.py`** to understand pattern.

Typical pattern:
```python
from .e01_name import bp as e01_bp
from .e02_name import bp as e02_bp
# Add:
from .e{NEW}_name import bp as e{NEW}_bp

def register_blueprints(app):
    app.register_blueprint(e01_bp, url_prefix="/v101")
    app.register_blueprint(e02_bp, url_prefix="/v102")
    # Add:
    app.register_blueprint(e{NEW}_bp, url_prefix="/v{NNN}")
```

### 3.3 Create Demo Directory

```bash
mkdir -p "vulnerabilities/python/flask/confusion/webapp/r0{N}_*/http/e{NEW}/"
```

**Verify these exist (don't modify):**
- `http/.httpyac.js` - httpyac configuration
- `http/common/setup.http` - shared setup code

### 3.4 Create Draft Demo Files

**⚠️ DELEGATE TO `demo-author` ⚠️**

I do NOT write .http files myself. Delegate with:

```
Context: Bootstrapping new exercise {version}.

Task: Create draft demo files for e{NEW} based on:
1. README description for this version's vulnerability
2. Pattern from previous exercise demos (e{PREV}/)

Create these files in http/e{NEW}/:
- e{NEW}_{slug}.exploit.http - Shows vulnerability exploitation
- e{NEW}_{slug}.fixed.http - Shows previous vuln is fixed
- e{NEW}_{slug}.intended.http - Shows new intended behavior (if applicable)

Requirements:
- Import common/setup.http
- Set @host = {{base_host}}/v{NNN}
- Add assertions that WILL FAIL (TDD - vuln not implemented yet)
- Follow character rules (attacker uses OWN credentials)
- Use seedBalance() for state setup

These demos SHOULD FAIL - that's correct TDD. Do not implement any fixes.
```

### 3.5 Update spec.yml

**Read `spec/spec.yml`** to understand inheritance pattern.

Add new version entry:
```yaml
  v{NNN}:
    inherits: v{NNN-1}
    tags:
      - v{NNN}
      - r0{N}
    exclude:
      # Previous version's vulnerability is fixed
      - "vuln-{previous-vuln-name}.http"
```

**Then run:**
```bash
ucsync
```

---

## Phase 4: Verification

### 4.1 Check Exercise Compiles

```bash
# Start services and check for import errors
ucup -d
uclogs --tail=20 | grep -i error
```

### 4.2 Run Inherited Specs

```bash
uctest v{NNN}/ -k
```

**Expected:** All specs PASS (behavior unchanged from previous version)

### 4.3 Run Demos (Expect Failures)

```bash
ucdemo r0{N}/e{NEW}
```

**Expected:** Demos FAIL (TDD - vulnerability not implemented)

**THIS IS CORRECT. DO NOT FIX.**

---

## Phase 5: Report Results

```markdown
## Bootstrap Complete: {version}

### 📁 Exercise Created
- Source: `e{PREV}_{name}/` → Target: `e{NEW}_{name}/`
- Config updated: version = "{version}"
- Routes wired: ✅

### 🎬 Demos Created
- `e{NEW}_{slug}.exploit.http` - ⚠️ Failing (expected - TDD)
- `e{NEW}_{slug}.fixed.http` - ⚠️ Failing (expected - TDD)
- `e{NEW}_{slug}.intended.http` - (if created)

### 🧪 Specs
- Added to spec.yml: ✅
- Inherits from: v{NNN-1}
- Excludes: vuln-{previous}.http
- ucsync: ✅
- uctest: {PASS/FAIL count}

### Next Steps
1. Use `/exercise/partner {version}` to discuss implementation
2. Implement vulnerability in exercise code
3. Verify demos pass
4. Add additional spec coverage as needed
```

---

## Special Case: New Section (e.g., v501)

When bootstrapping first exercise of a NEW section:

### Additional Steps Required

1. **Create section directory**: `r0{N}_{section_name}/`
2. **Create section routes.py**: With first blueprint import
3. **Create section README.md**: From curriculum plan
4. **Create http/ directory structure**:
   - `http/.httpyac.js` (copy from previous section)
   - `http/common/setup.http` (copy and adjust)
   - `http/e01/`
5. **Wire section into main app**: Update top-level routing

### Source Exercise

For `v501`, source = last exercise of section 4 (e.g., `v405` or whatever exists)

```bash
# Find last exercise in previous section
ls -d vulnerabilities/python/flask/confusion/webapp/r04_*/e*_*/ | tail -1
```

---

## Agent Delegation Reference

| Task | Agent | Required |
|------|-------|----------|
| Write .http demos | `demo-author` | **MANDATORY** |
| Debug demo issues | `demo-debugger` | If demos have syntax errors |
| Write .http specs | `spec-author` | If manual spec creation needed |
| Run specs | `spec-runner` | For complex spec verification |

**I handle directly:**
- cp -r for exercise code
- Editing config.py, routes.py (Python files)
- Creating directories
- Editing spec.yml
- Running ucsync, uctest, ucdemo

---

## Invariants I Enforce

1. **TDD**: Demos MUST fail initially (vulnerability not implemented)
2. **No vanity metrics**: Never silence failures to make things green
3. **One exercise**: I only bootstrap, I don't implement
4. **Delegate .http**: Only demo-author/spec-author write .http files
5. **Inheritance first**: New specs inherit from previous version

---

## Quick Reference: Version Mapping

| Version | Section | Exercise | Source |
|---------|---------|----------|--------|
| v101 | r01 | e01 | (first - special) |
| v102 | r01 | e02 | v101 |
| v201 | r02 | e01 | v1XX (last of r01) |
| v301 | r03 | e01 | v2XX (last of r02) |
| v403 | r04 | e03 | v402 |
| v501 | r05 | e01 | v4XX (last of r04) |

---

## Error Handling

| Error | Action |
|-------|--------|
| Source exercise not found | Stop, ask user to verify |
| Section doesn't exist (new section) | Trigger new section workflow |
| spec.yml syntax error | Fix YAML, re-run ucsync |
| Demo syntax errors | Delegate to demo-debugger |
| Import errors after wiring | Check routes.py blueprint names |

---

## Definition of Done Checklist

Before reporting complete:

- [ ] Exercise directory exists with updated config.py
- [ ] Blueprint wired in routes.py
- [ ] Demo directory exists with .http files (via demo-author)
- [ ] Demo files import common/setup.http correctly
- [ ] Demo files set correct @host
- [ ] spec.yml updated with inheritance + exclusion
- [ ] ucsync completed successfully
- [ ] uctest passes (inherited specs work)
- [ ] ucdemo runs (failures expected and ACCEPTABLE)
- [ ] NO vulnerability implementation done
- [ ] NO demo/spec failures silenced
