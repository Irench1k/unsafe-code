---
description: "Comprehensive review of Unsafe Code Lab exercises - validates code, specs, and demos"
---

# Review Exercises: $ARGUMENTS

Thoroughly review, validate, and improve the specified exercise versions.

## Before Starting

1. Read Serena memory `pedagogical-design-philosophy` for core principles
2. Read Serena memory `spongebob-characters` for character rules
3. Read Serena memory `version-roadmap` to understand what each version introduces

## Workflow

### Step 1: Understand Context
- Read the section README (e.g., `vulnerabilities/.../r03_authorization_confusion/README.md`)
- Identify which vulnerabilities and fixes are expected in each version
- Note the natural SaaS evolution narrative

### Step 2: Validate E2E Specs
- Run `uctest {version}/` for each version specified
- If tests fail, delegate to `uc-spec-debugger` for diagnosis
- Check inheritance health: most specs should inherit from previous version
- If inheritance is broken, investigate source code first (refactoring may have accidentally fixed vulns)

### Step 3: Validate Interactive Demos
- Check `vulnerabilities/.../http/eXX/` directories
- Each exercise has `.exploit.http` (demonstrates vuln) and `.fixed.http` (shows fix works)
- Run demos with `httpyac {file}.http -a`
- Verify: Character logic sound? Business impact clear? Fun without being cringe?

### Step 4: Cross-Reference
- Compare source code changes between versions (`diff -r eXX eXX+1`)
- Ensure documented vulnerabilities match actual code
- Verify fixes actually fix the vulnerability
- Check that new features follow natural evolution

### Step 5: Report
Provide structured summary:
- Versions reviewed
- Specs passed/failed
- Demos validated/issues found
- Inheritance health
- Recommendations

## Agent Delegation

| Task | Delegate To |
|------|-------------|
| Run e2e specs | uc-spec-runner |
| Diagnose spec failures | uc-spec-debugger |
| Fix spec test code | uc-spec-author |
| Manage inheritance | uc-spec-sync |
| Review demo quality | uc-docs-editor |

## Red Flags to Watch For

- Specs that need to be excluded (usually means source code bug)
- Interactive demos using victim's password (character logic error)
- Same business impact repeated 3+ times (needs variety)
- Technical jargon in demo annotations (should be behavioral)
- Multiple new concepts in single example (violates ONE concept rule)
