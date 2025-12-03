# Unsafe Code Lab: Orchestration Guide

> **Mission**: Educational security content with intentionally vulnerable code. Vulnerabilities are features, not bugs.

## Quick Start

Before ANY task, check relevant Serena memories:
- `pedagogical-design-philosophy` - ONE concept rule, progressive complexity, annotations
- `spongebob-characters` - Who attacks whom, credential rules
- `version-roadmap` - What each version introduces/fixes
- `http-demo-standards` - Interactive demo quality standards
- `spec-inheritance-principles` - E2E spec patterns

## Slash Commands

Use these for common workflows:
- `/project:review-exercises v301-v303` - Comprehensive exercise review
- `/project:run-specs v301/` - Smart spec execution
- `/project:validate-demos e01` - Interactive demo validation
- `/project:check-inheritance v302` - Inheritance health check
- `/project:brainstorm-exercise "idea"` - New vulnerability ideation
- `/project:quick-context` - Dump current state

## Orchestrator Role

**Plan, Delegate, Verify, Coordinate**—don't implement directly.

1. **Break tasks** into clear steps
2. **Delegate** to uc-* agents with precise instructions
3. **Verify** outputs against memories
4. **Pass context** between agents efficiently

## Specialized Agents

| Category | Agent | Purpose |
|----------|-------|---------|
| **Content** | uc-vulnerability-designer | Design WHAT/WHY/HOW |
| | uc-code-crafter | Implement vulnerable code |
| | uc-exploit-narrator | Create .http PoCs |
| **Docs** | uc-docs-editor | Edit READMEs |
| | uc-taxonomy-maintainer | Maintain classifications |
| | uc-curriculum-strategist | Gap analysis |
| **Infra** | uc-docs-generator-maintainer | Maintain `uv run docs` |
| | commit-agent | Verify + commit |
| **E2E Specs** | uc-spec-runner | Execute uctest (haiku) |
| | uc-spec-debugger | Diagnose failures (sonnet) |
| | uc-spec-author | Write/fix tests (sonnet) |
| | uc-spec-sync | Manage inheritance (haiku) |

## E2E Spec Decision Tree

```
Spec task
├── Run tests? → uc-spec-runner → pass/fail + next agent
├── "ref not found"? → uc-spec-debugger → uc-spec-author OR uc-spec-sync
├── Assertion mismatch? → uc-spec-debugger → uc-spec-author
├── Write new test? → uc-spec-author → uc-spec-runner
├── Fix test code? → uc-spec-author → uc-spec-runner
├── Update spec.yml? → uc-spec-sync → uc-spec-runner
└── Diagnose failure? → uc-spec-debugger → returns fix agent
```

## Quality Gates

### Before Delegating
- [ ] Read relevant memory first?
- [ ] ONE new concept only?
- [ ] Character logic sound? (attacker uses THEIR credentials)
- [ ] Variety in recent examples?

### Red Flags
- ❌ SpongeBob as attacker
- ❌ Victim's password in exploit
- ❌ Technical jargon in annotations
- ❌ `@base` in examples 1-2
- ❌ Same impact 4+ times
- ❌ Multiple new concepts

## Critical Distinctions

| Category | Style | Implications |
|----------|-------|--------------|
| **confusion/** | Sequential (r01→r02→r03) | Progressive complexity critical |
| **others** | Random-access | Each example standalone |

## Workflow Playbook

**Adding Vulnerability:**
1. uc-vulnerability-designer (design)
2. uc-code-crafter (implement)
3. uc-exploit-narrator (demos)
4. `uv run docs generate --target [path]`
5. commit-agent (verify + commit)

**Fixing Spec Failures:**
1. uc-spec-runner (run)
2. uc-spec-debugger (diagnose)
3. uc-spec-author OR uc-spec-sync (fix)
4. uc-spec-runner (verify)

## Key Insight

When inherited tests fail: **ALWAYS investigate source code first**. Refactoring can accidentally fix vulnerabilities!

## Success

Students learn to **spot subtle vulnerabilities in production-quality code** through intuition, not checklists.
