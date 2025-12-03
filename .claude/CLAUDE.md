# Unsafe Code Lab: Orchestration Guide

> **Mission**: Educational security content with intentionally vulnerable code. Vulnerabilities are features, not bugs.

## Foundation (Load First)

Before ANY task, load these files:
- `AGENTS.md` - Single source of truth for all invariants
- `docs/ai/runbooks.md` - Workflow checklists

## Session Startup Sequence

At the START of every session involving specs or demos:

1. Load `AGENTS.md` (single source of truth)
2. Check `docs/ai/runbooks.md` for the workflow you need
3. Check server health with `uclogs` if touching tests
4. Read the relevant section `README.md` to confirm intent

### Quick Health Check
```bash
# Run at session start if working with tests
docker compose ps  # Are containers running?
uclogs --since 30m | grep -c error  # Any recent errors?
```

## Slash Commands

| Command | Use When |
|---------|----------|
| `/project:review-exercises v301-v303` | Full exercise review |
| `/project:run-specs v301/` | Run specs smartly |
| `/project:extend-exercise v304` | Add next exercise |
| `/project:fix-failing-specs v303/` | Debug test failures |
| `/project:fix-exercises r03 e01-e07` | Implement exercises with TDD |
| `/project:maximize-inheritance v201` | Backport specs |
| `/project:validate-demos e01` | Check demo quality |
| `/project:check-inheritance v302` | Inheritance health |
| `/project:brainstorm-exercise "idea"` | New vulnerability ideation |
| `/project:quick-context` | Dump current state |
| `/project:health-check v301` | Quick verification (specs, docs, git) |

### Common Command Sequences

Commands often chain naturally. Here are proven workflows:

| Workflow | Command Sequence |
|----------|------------------|
| **Fix then verify** | `/fix-failing-specs v301` → `/health-check v301` |
| **Add exercise** | `/brainstorm-exercise "idea"` → `/extend-exercise r03 v308` → `/health-check v308` |
| **Full review** | `/review-exercises r03 e01-e07` → `/health-check v301 v302 v303...` |
| **Debug inheritance** | `/check-inheritance v302` → `/run-specs v302/` → `/fix-failing-specs v302` |
| **Maximize reuse** | `/maximize-inheritance v201` → `/run-specs v201 v202 v203` |

**Pro tip:** After any fix command, run `/health-check` to verify everything is green.

## Agent Routing Table

| You say... | First Agent | Then... |
|------------|-------------|---------|
| "review v301-v303" | uc-maintainer | orchestrates all |
| "extend specs", "new version" | uc-spec-sync | → uc-spec-runner → uc-spec-author |
| "uctest failed", "spec failing" | uc-spec-runner | → uc-spec-debugger → fix agent |
| "new exercise", "add vuln" | uc-vulnerability-designer | → uc-code-crafter → specs → demos |
| "exploit demo", ".http demo" | uc-exploit-narrator | → uc-docs-editor |
| "inheritance broken", "ref not found" | uc-spec-sync | → uc-spec-runner |
| "commit", "done" | commit-agent | — |

## Orchestrator Role

**Plan, Delegate, Verify, Coordinate** — don't implement directly.

1. **Break tasks** into clear steps
2. **Delegate** to uc-* agents with precise instructions
3. **Verify** outputs against `AGENTS.md` invariants
4. **Pass context** between agents efficiently

Use `uc-maintainer` for complex tasks that require multi-agent orchestration.

## Specialized Agents

### Content
| Agent | Purpose |
|-------|---------|
| uc-vulnerability-designer | Design WHAT/WHY/HOW |
| uc-code-crafter | Implement vulnerable code |
| uc-exploit-narrator | Create .http PoCs |

### Docs
| Agent | Purpose |
|-------|---------|
| uc-docs-editor | Edit READMEs |
| uc-taxonomy-maintainer | Maintain @unsafe annotations |
| uc-curriculum-strategist | Gap analysis |

### E2E Specs
| Agent | Purpose |
|-------|---------|
| uc-spec-runner | Execute uctest (haiku) |
| uc-spec-debugger | Diagnose failures (sonnet) |
| uc-spec-author | Write/fix tests (sonnet) |
| uc-spec-sync | Manage inheritance (haiku) |

### Infrastructure
| Agent | Purpose |
|-------|---------|
| uc-maintainer | Top-level orchestrator |
| uc-docs-generator-maintainer | Maintain `uv run docs` |
| commit-agent | Verify + commit |

## E2E Spec Decision Tree

```
Spec task
├── Run tests? → uc-spec-runner → pass/fail + next agent
├── "ref not found"? → uc-spec-debugger → uc-spec-author OR uc-spec-sync
├── Assertion mismatch? → uc-spec-debugger → check code vs spec
├── Write new test? → uc-spec-author → uc-spec-runner
├── Fix test code? → uc-spec-author → uc-spec-runner
├── Update spec.yml? → uc-spec-sync → uc-spec-runner
└── Diagnose failure? → uc-spec-debugger → returns fix agent
```

## Decision: Fix Code or Fix Test?

**Default rule**: If inherited test fails → **CODE IS SUSPECT**

- Inherited test fails → Investigate source code first (refactoring may have accidentally fixed vuln)
- New test for new feature → Verify assertion logic
- Test expects old behavior → Check README for intentional change

See `docs/ai/decision-trees.md` for complete decision trees.

## Quality Gates

### Before Delegating
- [ ] Read relevant section README?
- [ ] ONE new concept only?
- [ ] Character logic sound? (attacker uses THEIR credentials)
- [ ] Variety in recent examples?

### Red Flags (Stop & Think)
- ❌ SpongeBob as attacker
- ❌ Victim's password in exploit
- ❌ Technical jargon in annotations
- ❌ `@base` in examples 1-2
- ❌ Same impact 4+ times
- ❌ Multiple new concepts
- ❌ About to edit a `~` prefixed file (run ucsync instead)
- ❌ About to exclude inherited test (investigate code first)

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

See `docs/ai/runbooks.md` for complete workflows.

## Key Insight

When inherited tests fail: **ALWAYS investigate source code first**. Refactoring can accidentally fix vulnerabilities!

## Success Criteria

Students learn to **spot subtle vulnerabilities in production-quality code** through intuition, not checklists.
