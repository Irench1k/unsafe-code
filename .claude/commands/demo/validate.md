---
description: "Validate interactive .http demos for quality, character logic, and engagement"
model: opus
argument-hint: [exercise-id|path]
---

# Validate Demos: $ARGUMENTS

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
| `code-reviewer` | ❌ Use project agents instead |

### 3. I AM A DUMB ROUTER

**My ONLY job is to delegate to project agents.** I do NOT:

- ❌ Read `.http` files directly
- ❌ Read skill files (`.claude/skills/`)
- ❌ Read reference files (`.claude/references/`)
- ❌ Analyze code or syntax myself
- ❌ Run httpyac directly
- ❌ Make validation judgments myself

### 4. ALLOWED AGENTS (ONLY THESE)

| Task | Agent | How to Spawn |
|------|-------|--------------|
| Run & analyze demos | `demo-debugger` | `Task(subagent_type="demo-debugger")` |
| Fix issues found | `demo-author` | `Task(subagent_type="demo-author")` |

**Validation = Spawn demo-debugger, report its findings to user.**

---

Consider carefully the student experience. Is the demo engaging? Is character logic sound?

Validate student-facing interactive exploit demonstrations.

## Location Pattern

```
vulnerabilities/python/flask/confusion/webapp/r{NN}_{category}/http/e{XX}/
├── e{XX}_{name}.exploit.http    # Demonstrates the vulnerability
└── e{XX}_{name}.fixed.http      # Shows the fix works
```

## Before Validating

Review these references first:

- `spongebob-characters` - Character rules and logic
- `demo-conventions` - Demo quality standards
- `http-syntax` + `http-gotchas` - Minimal syntax/pitfall refresher
- `vulnerability-design-methodology` - ONE concept rule

## Validation Checklist

### Technical Correctness

- [ ] Exploit actually exploits the vulnerability
- [ ] Fixed version actually blocks the exploit
- [ ] Assertions verify expected behavior
- [ ] No hardcoded values that break on reseed
- [ ] Works with `ucdemo {file}`

### Character Logic

- [ ] Attacker uses THEIR credentials (not victim's)
- [ ] Plankton attacks Mr. Krabs/organization
- [ ] Squidward attacks SpongeBob (petty revenge)
- [ ] SpongeBob is NEVER an attacker
- [ ] Credentials match character roles

### Engagement Quality

- [ ] Business impact immediately clear
- [ ] Not boring or formulaic
- [ ] Fun in underhanded way (via examples, not explanations)
- [ ] Minimal annotations (show, don't tell)
- [ ] No overexplaining what's visible in the code

### Format Standards

- [ ] One assert per test (unlike e2e specs)
- [ ] Variables defined for reusable values
- [ ] Console.info at key moments (sparingly)
- [ ] No complex .http syntax
- [ ] Plain demo patterns (no utils.cjs helpers)

## Red Flags

- Using `$(response).field()` - that's e2e spec syntax, not demo syntax
- Using `auth.basic()` - demos use raw Authorization headers
- Multiple paragraphs of explanation
- Same business impact as previous demo
- Technical jargon ("authenticates", "instantiates")

## Running Demos

```bash
# Run single demo
ucdemo path/to/e01_demo.exploit.http

# Run all demos in exercise
ucdemo r02/e01

# If balance issues occur
# Use seedBalance() helper in the demo setup
```

## Demo vs E2E Spec Comparison

| Aspect          | Interactive Demo            | E2E Spec              |
| --------------- | --------------------------- | --------------------- |
| Response access | `response.parsedBody.field` | `$(response).field()` |
| Auth            | Raw `Authorization:` header | `{{auth.basic()}}`    |
| Asserts         | 1 per test                  | Multiple OK           |
| Helpers         | None (plain patterns)       | Full utils.cjs        |
| Purpose         | Student learning            | Automated testing     |
