---
name: commit-workflow
description: Pre-commit verification workflow for Unsafe Code Lab. Auto-invoke when committing changes, finalizing work, or requesting "done" status. Covers verification steps by change category, commit message format, and quality gates that must pass.
---

# Commit Workflow

## When to Use This Skill

- About to commit changes
- User says "done" or "commit"
- Final verification needed
- Quality gates to check

## When NOT to Use This Skill

- Still implementing features
- Debugging failing tests
- Making iterative changes

## Pre-Commit Checklist by Category

### Category A: Tool Changes (tools/)

If you modified files in `tools/`:

```bash
# Run tests
uv run docs test -v

# Type checking
uv run mypy

# Linting
uv run ruff check tools/
```

**All must pass before committing.**

### Category B: Content Changes (vulnerabilities/, spec/)

If you modified vulnerable code, specs, or demos:

```bash
# Full docs verification (includes link checking)
uv run docs verify -v
```

This checks:
- All @unsafe annotations parseable
- README.md files up-to-date
- No broken links
- Annotation format compliance

### Category C: Mixed Changes

If both tools/ and content changed:

1. Run Category A checks first (ensures tools work)
2. Then run Category B checks (with updated tools)

### Category D: Documentation Only (.claude/, docs/)

If only configuration or documentation changed:

- No automated checks required
- Verify changes are intentional
- Check for broken relative links

## Git Status Check

Before committing, always verify:

```bash
git status
git diff --stat
```

**Never commit**:
- `.env` files
- Credentials or API keys
- Large generated files
- Unintended changes

## Commit Message Format

### Structure

```
<type>[scope]: <description>

[optional body]

[optional footer]
```

### Types

| Type | When to Use |
|------|-------------|
| feat | New feature or exercise |
| fix | Bug fix |
| docs | Documentation only |
| test | Adding or fixing tests |
| refactor | Code change that doesn't fix bug or add feature |
| chore | Maintenance tasks |

### Scope

| Scope | When to Use |
|-------|-------------|
| v301, v302, etc. | Changes to specific version |
| r01, r02, r03 | Changes to section |
| tools | Changes to tooling |
| spec | Changes to e2e specs |
| demo | Changes to interactive demos |

### Examples

```
feat[v303]: Add menu edit vulnerability

Introduces authorization confusion where restaurant staff can
edit menu items for other restaurants by manipulating the
restaurant_id in the request body.

- Added vulnerable endpoint in routes/menu.py
- Created exploit demo in http/e03/
- Added e2e specs in spec/v303/
```

```
fix[v302]: Restore cart swap vulnerability after refactor

Recent refactoring accidentally fixed the cart swap vuln.
Reverted the check order to maintain intentional vulnerability.
```

```
test[spec]: Add authorization boundary specs for cart endpoints

- Added happy path tests for cart ownership
- Added negative tests for cross-user access
- Configured inheritance from v201
```

## Quality Gates

### Required for All Commits

- [ ] `git status` shows only intended files
- [ ] No secrets or credentials staged
- [ ] Commit message follows format

### Required for Code Commits

- [ ] Relevant tests pass (uctest for specs, ucdemo for demos)
- [ ] No server errors in uclogs
- [ ] @unsafe annotations present if vulnerability added

### Required for Tool Commits

- [ ] `uv run docs test -v` passes
- [ ] `uv run mypy` passes
- [ ] `uv run ruff check tools/` passes

### Required for Content Commits

- [ ] `uv run docs verify -v` passes
- [ ] Links verified
- [ ] README accuracy verified

## Failure Handling

### If Quality Gates Fail

1. **Don't commit** - Fix the issue first
2. **Report back** - Explain what failed
3. **Small fix** - Apply auto-fixable lints only:
   ```bash
   uv run ruff check tools/ --fix
   ```
4. **Complex fix** - Delegate to appropriate agent

### If Unsure What to Commit

List changes and categorize:

```bash
git diff --name-only
```

Group by:
- Feature changes (commit together)
- Unrelated fixes (separate commits)
- Experimental/incomplete (don't commit yet)

## Atomic Commits

**Good**: One logical change per commit
- "Add v303 vulnerable endpoint"
- "Add v303 exploit demo"
- "Add v303 e2e specs"

**Bad**: Everything in one commit
- "Add v303 with endpoint, demos, specs, and also fixed unrelated bug in v301"

## After Committing

```bash
# Verify commit
git log -1

# Check nothing left unstaged accidentally
git status
```

## See Also

- [uclab-tools](../uclab-tools/SKILL.md) - CLI commands
- [http-spec-debugging](../http-spec-debugging/SKILL.md) - If tests fail during verification
