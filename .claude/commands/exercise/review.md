---
description: "Review and fix exercises: validate specs, demos, code using TDD"
model: opus
argument-hint: [section] [exercise-range|all]
---

# Review Exercises: $ARGUMENTS

---

## ⛔⛔⛔ CRITICAL RESTRICTIONS - READ FIRST ⛔⛔⛔

### 1. PLAN MODE CHECK

**IF Plan Mode is active → STOP IMMEDIATELY.**

```
ERROR: This command is incompatible with Plan Mode.
Please restart without Plan Mode enabled.
```

### 2. BUILT-IN AGENTS ARE BANNED

**I MUST NEVER spawn these built-in subagent types:**

| Banned Agent | Why |
|--------------|-----|
| `Explore` | ❌ Bypasses our specialized agents |
| `Plan` | ❌ Interferes with command workflow |
| `general-purpose` | ❌ No domain skills |

### 3. ALLOWED AGENTS ONLY

| Task | Agent |
|------|-------|
| Run specs | `spec-runner` |
| Debug failures | `spec-debugger` |
| Fix specs | `spec-author` |
| Review demos | `demo-debugger` |
| Fix demos | `demo-author` |
| Fix source code | `code-author` |
| Edit docs | `docs-author` |

---

## My Mission

I am a **comprehensive review orchestrator**. For each exercise I review:

1. **Source Code** - Does implementation match intent?
2. **Documentation** - Does README match implementation?
3. **E2E Specs** - Do specs test the vulnerability correctly?
4. **Demos** - Do demos clearly show the attack?
5. **Alignment** - Are all pieces consistent?

---

## Parse Arguments

- **Section**: First word (e.g., `r02`, `r03`)
- **Exercise Range**: Second word can be:
  - Single exercise: `e07` → review only v307
  - Range: `e01-e07` → review v301 through v307
  - All: `all` → review entire section
  - Version: `v307` → review specific version
- **Path**: `vulnerabilities/python/flask/confusion/webapp/{section}_*/`

---

## Health Check

!`(cd vulnerabilities/python/flask/confusion/ && uclogs --since 30m 2>/dev/null | grep -c -i error || echo "0")`
recent errors

---

## Phase 1: Understand Intent

**I WILL read these files myself (not delegate):**

1. **Section README** - `vulnerabilities/.../r0X_.../README.md`
   - What vulnerability is documented for each version?
   - What is the expected exploit flow?
   - What is the narrative/story?

2. **Exercise Source Code** - `vulnerabilities/.../e0X_.../`
   - How is the vulnerability actually implemented?
   - How does it differ from previous version?
   - What does `@unsafe` annotation say?

**Key Question:** Does the implementation match the README description?

---

## Phase 2: Check Alignment

After reading README and source code:

### If README ≠ Implementation:

1. **Document the discrepancy** clearly
2. **Present findings** to the user
3. **Ask which to fix:**
   - Update README to match implementation? (usually correct)
   - Update implementation to match README? (rare)

**Do NOT auto-fix docs without user approval.**

### Common Discrepancies:

| Issue | Example | Resolution |
|-------|---------|------------|
| Wrong mechanism | README says "middleware mutates X" but code does "handler reads Y" | Update README |
| Wrong exploit flow | README steps don't match actual attack | Update README |
| Missing fix description | README doesn't explain how v(N+1) fixes it | Add to README |
| Outdated narrative | Story changed during implementation | Update README |

---

## Phase 3: Validate E2E Specs

**Delegate to `spec-runner`:**

```
Run E2E specs for v{XXX}.
Report: pass/fail counts, any failures with error messages, inheritance health.
```

### If Failures:

1. **Delegate to `spec-debugger`** to analyze
2. Determine if issue is in:
   - **Spec** → delegate to `spec-author`
   - **Source code** → delegate to `code-author`
   - **Both** → fix source first, then spec

### Inheritance Check:

- Count `~*.http` files (inherited) vs native files
- If inherited test fails → investigate source code first (may have accidentally fixed vuln)

---

## Phase 4: Validate Demos

**Delegate to `demo-debugger`:**

```
Validate demos for e{XX} in section r{YY}.
Check: execution, character logic, narrative quality, assertions, state management.
```

### Demo Quality Checklist:

- [ ] Attacker uses OWN credentials (not victim's password)
- [ ] Business impact is clear to students
- [ ] No technical jargon
- [ ] Strategic console.info (2-3 max)
- [ ] Setup code in request-level `{{ }}` (after `###`), NOT file-level

### If Issues Found:

1. **Present findings** to user
2. **Ask which issues to fix:**
   - Critical (broken execution) → always fix
   - Quality (narrative, clarity) → ask scope
   - Minor (formatting) → ask if desired

**Delegate fixes to `demo-author`** with specific instructions.

---

## Phase 5: Cross-Reference Completeness

### For Each Exercise (vXXX):

| Artifact | Location | Purpose |
|----------|----------|---------|
| Vuln Code | `eXX_.../` | Implements vulnerability |
| Fix Code | `e(XX+1)_.../` | Fixes vulnerability |
| Exploit Demo | `http/eXX/*.exploit.http` | Shows attack succeeds |
| Fixed Demo | `http/eXX/*.fixed.http` | Shows fix blocks attack |
| Vuln Spec | `spec/vXXX/*/vuln-*.http` | Tests vuln exists |
| Fix Spec | `spec/v(XXX+1)/*/` | Tests fix works |

### Check Demo-Spec Alignment:

**Demos should have corresponding E2E specs!**

If demo tests something that spec doesn't cover:
1. Note the gap
2. Ask user if spec should be added
3. If yes → delegate to `spec-author`

---

## Phase 6: Generate Report

### Summary Format:

```markdown
## Exercise Review: {section} {range}

### Versions Reviewed: v{start} - v{end}

### Alignment Status:
- [ ] README matches implementation: {YES/NO - details}
- [ ] Specs test documented vuln: {YES/NO}
- [ ] Demos show documented attack: {YES/NO}

### E2E Specs:
- Total: {N} | Passed: {P} | Failed: {F}
- Inheritance: {healthy/broken}
- Issues: {list}

### Demos:
- Files: {list}
- Execution: {pass/fail}
- Quality Issues: {list}
- Missing specs for demo scenarios: {list}

### Discrepancies Found:
1. {discrepancy} → {recommended action}
2. ...

### Recommendations:
1. {action item}
2. ...
```

---

## Phase 7: Execute Fixes (With Approval)

After presenting report:

1. **Ask user** which issues to address
2. **Execute fixes** via appropriate agents
3. **Re-run validation** to confirm fixes
4. **Update report** with final status

---

## Red Flags (Stop & Investigate)

- **Inherited spec fails** → source code may have accidentally fixed vuln
- **Victim's password in demo** → character logic error (attacker uses OWN creds)
- **File-level `{{ }}` with state ops** → will break multi-request demos
- **README says X, code does Y** → alignment issue, ask user
- **Demo works but no spec** → coverage gap, suggest adding spec
- **Technical jargon in demo** → should be behavioral/narrative

---

## Definition of Done

- [ ] README accurately describes implementation
- [ ] Source code implements vuln correctly
- [ ] Source code (next version) fixes vuln
- [ ] `.exploit.http` demonstrates vuln
- [ ] `.fixed.http` demonstrates fix
- [ ] `vuln-*.http` spec tests vuln exists
- [ ] Next version specs test fix
- [ ] All demos pass (`ucdemo`)
- [ ] All specs pass (`uctest`)
- [ ] Inheritance healthy (`ucsync`)
- [ ] No server errors in logs
- [ ] Demo scenarios have spec coverage
