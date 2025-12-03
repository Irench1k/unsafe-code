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

```
┌─────────────────────────────────────────────────────────────────┐
│                      uc-maintainer                              │
│              (Top-level orchestrator, sonnet)                   │
└───────────┬────────────────────────────────────────┬────────────┘
            │                                        │
    ┌───────┴───────┐                       ┌───────┴───────┐
    │   CONTENT     │                       │   E2E SPECS   │
    └───────────────┘                       └───────────────┘
    │                                       │
    ├─ uc-vulnerability-designer (sonnet)   ├─ uc-spec-runner (haiku)
    │  └─ Design WHAT/WHY vulnerabilities   │  └─ Execute uctest
    │                                       │
    ├─ uc-code-crafter (sonnet)             ├─ uc-spec-debugger (sonnet)
    │  └─ Implement vulnerable code         │  └─ Diagnose failures
    │                                       │
    └─ uc-exploit-narrator (sonnet)         ├─ uc-spec-author (sonnet)
       └─ Create .http PoC demos            │  └─ Write/fix tests
                                            │
                                            └─ uc-spec-sync (haiku)
    ┌───────────────┐                          └─ Manage inheritance
    │   DOCS        │
    └───────────────┘                       ┌───────────────┐
    │                                       │   DEBUG       │
    ├─ uc-docs-editor (haiku)               └───────────────┘
    │  └─ Edit READMEs                      │
    │                                       └─ uc-demo-debugger (haiku)
    ├─ uc-taxonomy-maintainer (haiku)          └─ Debug httpyac demos
    │  └─ Maintain @unsafe annotations
    │
    └─ uc-curriculum-strategist (sonnet)    ┌───────────────┐
       └─ Gap analysis                      │   INFRA       │
                                            └───────────────┘
                                            │
                                            └─ commit-agent (haiku)
                                               └─ Verify + commit
```

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
   └─ uc-vulnerability-designer creates spec

2. /extend-exercise r03 v308         → Full pipeline
   └─ uc-code-crafter implements code
   └─ uc-spec-author creates specs
   └─ uc-exploit-narrator creates demos

3. /run-specs v308/                  → Verify
   └─ uc-spec-runner executes

4. commit-agent                      → Finalize
```

### Fixing Failing Tests

```
1. /run-specs v303/                  → Identify failures
   └─ Returns pass/fail summary

2. /fix-failing-specs v303/          → Diagnose + fix
   └─ uc-spec-debugger classifies failures
   └─ Routes to: uc-spec-author OR uc-spec-sync OR uc-code-crafter

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
| `spec/vNNN/` files | `http-e2e-specs` | `$(response)`, `auth.basic()`, `@ref` |
| `http/eNN/` demos | `http-interactive-demos` | `.exploit.http`, `IMPACT:` |
| Assertion errors | `http-assertion-gotchas` | "Expected X but got Y", 500 errors |
| `~` files, ucsync | `spec-inheritance` | "ref not found", version bumps |
| Demo narratives | `spongebob-characters` | SpongeBob, Squidward, Plankton |
| CLI tools | `uclab-tools` | uctest, httpyac, uclogs |
| Vuln design | `vulnerability-design-methodology` | ONE concept rule, complexity |
| @unsafe code | `vulnerable-code-patterns` | Annotations, Flask patterns |
| Failure diagnosis | `spec-debugging` | Fix code vs fix test decisions |
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
| **Debugger** | `uc-spec-debugger` | `uc-demo-debugger` |

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
