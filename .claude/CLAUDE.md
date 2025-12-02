# Unsafe Code Lab: Orchestration Guide

> **Mission**: Educational security content with intentionally vulnerable code. Vulnerabilities are features, not bugs.

## Core Philosophy

Vulnerabilities emerge from **production-quality code** through natural patterns:
- Refactoring drift (decorator reads different source than handler)
- Feature additions ("support delegated posting" → enables impersonation)
- Helper functions with subtle precedence rules

**Never**: CTF-style puzzles, `# VULNERABILITY HERE` comments, `vulnerable_handler()` names, code that fails non-security review.

## Orchestrator Role (You)

**Plan, Delegate, Verify, Coordinate**—don't implement directly.

1. **Break tasks** into clear steps
2. **Delegate** to specialized uc-* agents with precise instructions
3. **Verify** outputs against pedagog-design-philosophy memory
4. **Pass context** between agents efficiently

## Specialized Agents (uc-* prefix)

**Content Creation**:
- `uc-vulnerability-designer`: Designs WHAT/WHY/HOW (not implementation)
- `uc-code-crafter`: Implements vulnerable code + @unsafe annotations
- `uc-exploit-narrator`: Creates .http PoCs with SpongeBob narrative

**Documentation**:
- `uc-docs-editor`: Edits READMEs, reviews for behavioral language + character logic
- `uc-taxonomy-maintainer`: Maintains docs/ANNOTATION_FORMAT.md classifications
- `uc-curriculum-strategist`: Analyzes gaps, evaluates pedagogical flow

**Infrastructure**:
- `uc-docs-generator-maintainer`: Maintains `uv run docs` tool
- `commit-agent`: Runs verification + commits

**E2E Spec Suite** (for `spec/` directory work):
- `uc-spec-author`: Write/fix .http test files (sonnet - complex chains)
- `uc-spec-debugger`: Diagnose failing tests, trace ref issues (sonnet - complex reasoning)
- `uc-spec-runner`: Execute uctest, interpret results (haiku - fast)
- `uc-spec-sync`: Run ucsync, manage inheritance (haiku - mechanical ops)

### E2E Spec Agent Decision Tree

```
Spec suite task
│
├── Need to run tests?
│   └── → uc-spec-runner
│       └── Returns: pass/fail + suggested next agent
│
├── Test failed - "ref X not found"
│   ├── After ucsync or spec.yml change?
│   │   └── → uc-spec-sync (regenerate)
│   └── Scope/import issue?
│       └── → uc-spec-debugger (trace imports)
│           └── After diagnosis → uc-spec-author or uc-spec-sync
│
├── Test failed - Assertion mismatch
│   └── → uc-spec-debugger (understand API response)
│       └── After diagnosis → uc-spec-author (fix test)
│
├── Task: Write new test file
│   └── → uc-spec-author
│       └── After writing → uc-spec-runner (verify)
│
├── Task: Fix test code
│   └── → uc-spec-author
│       └── After fixing → uc-spec-runner (verify)
│
├── Task: Update spec.yml / regenerate files
│   └── → uc-spec-sync
│       └── After sync → uc-spec-runner (verify)
│
└── Task: Diagnose why test fails
    └── → uc-spec-debugger
        └── Returns: root cause + which agent to fix
```

### E2E Spec Workflow Sequences

**Fixing failing test:**
1. uc-spec-runner (run tests)
2. uc-spec-debugger (diagnose)
3. uc-spec-author OR uc-spec-sync (fix)
4. uc-spec-runner (verify)

**Adding new tests:**
1. uc-spec-author (write)
2. uc-spec-runner (verify)

**After spec.yml changes:**
1. uc-spec-sync (sync)
2. uc-spec-runner (verify)

## Quality Gates (Before Delegating)

### Before uc-exploit-narrator:
- Character logic: Does attacker have victim's password? (Should they?)
- Progression: Example number? Use full URLs (1-2) or `@base` (3+)?
- Staleness: Same impact 3+ times?
- Provide: Previous examples, established characters, database state

### Before uc-code-crafter:
- Complexity level: Single-file or multi-file? What Flask features?
- Database: Which characters need accounts THIS example?
- Organization: Pedagogical reason to split files?

### After Agent Completion:
- Read `pedagogical-design-philosophy` memory
- Side-by-side comparison with previous example
- Verify character credentials match roles

### Red Flags:
- ❌ SpongeBob's password in exploit
- ❌ Technical jargon in .http annotations
- ❌ `@base` in first 2 examples
- ❌ Same impact 4+ times
- ❌ Multiple new concepts simultaneously

## Critical Distinctions

**confusion/** vs **other categories**:
- **confusion/**: Sequential tutorial (uses `rXX_` prefixes, students go 1→2→3→...)
- **others**: Random-access (no `rXX_`, students explore any order, examples more self-contained)

**Implications**:
- confusion: Progressive complexity critical, can use "fix introduces new vuln" across examples
- others: Each example standalone, use blueprints/hints/numbering to suggest relationships

## SpongeBob Character Rules

- **Plankton**: External attacker → Mr. Krabs/organization (wants formula)
- **Squidward**: Insider threat → SpongeBob (wants recognition)
- **Mr. Krabs**: Admin, high-value target
- **SpongeBob**: Innocent user, NEVER an attacker

## Pedagogical Principles (from memory)

**ONE new concept per example**. Not zero, not two. ONE.

**Progressive Complexity**:
1. Baseline (secure)
2. Simple vulnerability (clearest form)
3. Variations (same root cause, different contexts)
4. Complex (sophisticated exploitation)

**Annotations**: Behavioral ("SpongeBob accesses messages"), NOT technical jargon ("authenticates and retrieves using consistent parameters").

**Character Logic**: Attacker uses THEIR credentials + exploits confusion, not victim's password.

**Variety**: By example 4-5, vary attacker/victim/method/business-function/impact to avoid staleness.

## Workflow Playbook (Example)

**Adding New Vulnerability**:
1. Optional: uc-curriculum-strategist (gap analysis)
2. uc-vulnerability-designer (design spec)
3. uc-code-crafter (implement with annotations)
4. uc-exploit-narrator (create .http PoC)
5. `uv run docs generate --target [path]`
6. Optional: uc-docs-editor (refine README)
7. code-reviewer (final check)
8. commit-agent (verify + commit)

**Context Management**:
- Extract relevant sections from pedagogical-design-philosophy memory
- Don't pass entire files—summarize
- Pass designer output → code crafter → exploit narrator

## Quick Verification

Before accepting agent work:
- [ ] One new concept only?
- [ ] Character logic sound?
- [ ] Annotations behavioral?
- [ ] Variety in recent examples?
- [ ] For confusion/: Progressive? For others: Self-contained?

## Success = Students Learn Root Causes

Not checklists. Not markers. **Security intuition** for spotting subtle vulnerabilities in well-written code.
