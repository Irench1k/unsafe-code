# Unsafe Code Lab: AI-Assisted Development Guide

Guide for human contributors on using Claude Code effectively in this project.

## Quick Reference: Which Command to Use

| I want to... | Command | Arguments |
|--------------|---------|-----------|
| Start new exercise | `/extend-exercise` | `[section] [version]` |
| Review exercise range | `/review-exercises` | `[section] [exercise-range\|all]` |
| Fix failing tests | `/fix-failing-specs` | `[version-or-path]` |
| Run tests quickly | `/run-specs` | `[version-path] [options]` |
| Check inheritance | `/check-inheritance` | `[version-spec]` |
| Validate demo quality | `/validate-demos` | `[exercise-id\|path]` |
| Brainstorm new vuln | `/brainstorm-exercise` | `[vulnerability-idea]` |
| Get project context | `/quick-context` | (none) |
| Maximize inheritance | `/maximize-inheritance` | `[base-version] [target-versions]` |
| Implement using TDD | `/fix-exercises` | `[section] [exercise-range\|all]` |

## Agent Architecture

- **uc-maintainer** (opus): top-level orchestrator (name unchanged)
- **Content & Docs**: `content-planner` (design/taxonomy), `code-author` (implement), `docs-author` (docs)
- **Specs**: `spec-runner` (uctest + ucsync), `spec-debugger` (diagnose), `spec-author` (write/fix specs)
- **Demos**: `demo-author` (create/maintain demos), `demo-debugger` (diagnose demos)
- **Infra**: `infra-maintainer` (tooling, docs generator), `commit-agent` (verify + commit)

### Model Selection Rationale

| Model | Used For | Why |
|-------|----------|-----|
| **opus** | Multi-agent orchestration commands | Complex coordination, extended thinking |
| **sonnet** | Reasoning-heavy agents | Design, debugging, authoring |
| **haiku** | Execution-focused agents | Fast, mechanical verification |

## Common Workflows

### Adding New Exercise

```
1. /brainstorm-exercise "your idea"  → Design
   └─ content-planner creates design brief

2. /extend-exercise r03 v308         → Full pipeline
   └─ code-author implements code
   └─ spec-author creates specs (spec-runner runs ucsync/uctest)
   └─ demo-author creates demos

3. /run-specs v308/                  → Verify
   └─ spec-runner executes

4. commit-agent                      → Finalize
```

### Fixing Failing Tests

```
1. /run-specs v303/                  → Identify failures
   └─ Returns pass/fail summary

2. /fix-failing-specs v303/          → Diagnose + fix
   └─ spec-debugger classifies failures
   └─ Routes to: spec-author or spec-runner (inheritance) or code-author

3. Repeat until green
```

### Reviewing Exercises

```
1. /review-exercises r03 e01-e07     → Full quality review
   └─ Runs specs across all versions
   └─ Validates demo quality
   └─ Checks character logic
   └─ Reports issues
```

## Skills Auto-Loading

Skills load automatically based on context:

| Working With | Auto-Loaded Skill | Key Triggers |
|--------------|-------------------|--------------|
| `spec/**/*.http` | `http-spec-conventions` + `http-syntax` + `http-gotchas` | `$(response)`, `auth.basic()`, `@ref` |
| `vulnerabilities/.../http/**/*.http` | `http-demo-conventions` + `http-syntax` + `http-gotchas` | `.exploit.http`, `.fixed.http` |
| Any `.http` edit | `http-editing-policy` | enforce delegation |
| Assertion errors | `http-gotchas` | "Expected X but got Y", 500 errors |
| Inheritance/ucsync | `http-spec-inheritance` | `~` files, version bumps |
| Spec debugging | `http-spec-debugging` | `uctest` failure triage |
| Demo narratives | `spongebob-characters` | SpongeBob, Squidward, Plankton |
| CLI tools | `uclab-tools` | uctest, httpyac, uclogs |
| Vuln design | `vulnerability-design-methodology` | ONE concept rule, complexity |
| @unsafe code | `vulnerable-code-patterns` | Annotations, Flask patterns |
| README editing | `documentation-style` | Behavioral language, jargon |
| Committing | `commit-workflow` | Quality gates, message format |

## Critical Distinctions

### E2E Specs vs Interactive Demos

| Aspect | E2E Specs (`spec/`) | Interactive Demos (`http/`) |
|--------|---------------------|----------------------------|
| **Runner** | `uctest` | `httpyac` |
| **Response** | `$(response).field()` | `response.parsedBody` |
| **Auth** | `{{auth.basic()}}` | Manual `Authorization:` |
| **Imports** | Heavy use | Only `setup.http` |
| **Asserts** | Multiple OK | ONE per test |
| **Debugger** | `spec-debugger` | `demo-debugger` |

### Fix Code vs Fix Test?

**Default rule**: Inherited test fails → **SUSPECT CODE FIRST**

```
Inherited test fails
├── Check source code for changes
├── Did refactoring accidentally fix vuln?
│   └── YES → Restore vulnerable code (code issue)
└── Should test be excluded?
    └── Only after confirming vuln shouldn't exist (spec issue)
```

## CLI Tool Reference

| Tool | Purpose | Example |
|------|---------|---------|
| `uctest` | Run E2E specs | `uctest v301/cart/` |
| `httpyac` | Run demos | `httpyac file.http -a` |
| `ucsync` | Manage inheritance | `ucsync v302` |
| `uclogs` | View logs | `uclogs --since 10m` |
| `uv run docs` | Generate READMEs | `uv run docs generate` |

## Character Rules

> **CRITICAL**: Attacker uses THEIR OWN credentials. Exploit = confusion, not theft!

| Character | Role | Attacks | Never |
|-----------|------|---------|-------|
| SpongeBob | Victim | — | Never attacker |
| Squidward | Insider threat | SpongeBob, Mr. Krabs | — |
| Plankton | External attacker | Mr. Krabs, Patrick | SpongeBob directly |
| Patrick | VIP victim | — | — |
| Mr. Krabs | High-value target | — | — |

## Assertion Quick Reference

```http
# CORRECT - operator required, no quotes on RHS
?? js $(response).field("status") == approved
?? js parseFloat($(response).balance()) > 100

# WRONG - missing operator (becomes request body!)
?? js $(response).field("active")

# WRONG - quotes become part of literal
?? js $(response).field("status") == "approved"

# CORRECT - capture pre-state BEFORE request
{{
  exports.before = await user("plankton").balance();
}}
POST /refund
?? js await user("plankton").balance() == {{before + 10}}
```

## Quality Checklist

Before committing:

- [ ] E2E specs pass (`uctest vNNN/`)
- [ ] Interactive demos run (`httpyac ... -a`)
- [ ] Character logic correct (attacker uses own creds)
- [ ] ONE new concept per example
- [ ] No technical jargon in demo annotations
- [ ] READMEs regenerated if annotations changed

## Red Flags

Stop and reconsider if you see:

- ❌ SpongeBob as attacker
- ❌ Victim's password in exploit request
- ❌ Technical jargon in demo annotations
- ❌ About to edit a `~` prefixed file (run ucsync instead)
- ❌ About to exclude inherited test without checking code
- ❌ Multiple new concepts in one example

## Getting Help

| Resource | Purpose |
|----------|---------|
| Skills | Auto-load based on context |
| Slash commands | `/project:*` for workflows |
| `AGENTS.md` | Full agent documentation |
| `docs/ai/runbooks.md` | Step-by-step workflows |
| `docs/ai/decision-trees.md` | Diagnosis flowcharts |
| `docs/ai/gotchas.md` | Common mistakes |
