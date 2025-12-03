# Prompt Templates

Copy-paste templates for complex scenarios that don't fit slash commands.

---

## Reviewing a Single .http Demo

```
Review this interactive demo for quality:
[path to .http file]

Check against Serena memory `http-demo-standards`:
- One assert per test?
- Character logic (attacker's own credentials)?
- Behavioral annotations (not jargon)?
- Business impact clear?
- Fun without cringe?

Also verify:
- Works with `httpyac [file] -a`
- Uses plain httpyac syntax (not utils.cjs helpers)
- @base only in example 3+
```

---

## Debugging a Specific Test Failure

```
This e2e spec is failing:
[paste error output]

Diagnose using this workflow:
1. Is it "ref not found"? Check import chain
2. Is it assertion mismatch? Check API response format
3. Is it 500 error? Check uclogs for server error

Key question: Is the test wrong, or did refactoring accidentally fix the vulnerability?

Check source code diff between versions before assuming test is broken.
```

---

## Investigating Accidental Vulnerability Fix

```
Inherited vulnerability test fails in [version]:
[paste test and error]

Investigate:
1. Diff source code: what changed between v[N-1] and v[N]?
2. Does the change intentionally or accidentally affect the vulnerability?
3. If accidentally fixed: add exclusion + document WHY
4. If intentionally fixed: ensure corresponding .fixed.http passes

See Serena memory `spec-inheritance-principles` for patterns.
```

---

## Adding a New Character to Narrative

```
I want to add [character] as an attacker/victim in [exercise].

Before proceeding, verify against `spongebob-characters` memory:
- Is this character appropriate for this attack type?
- Does the motivation match?
- Is SpongeBob NOT an attacker?

If new character needed in database:
1. Add to db population only when first used
2. Update credentials reference
3. Ensure character has logical reason to be in system
```

---

## Porting Tests to Base Version

```
Port these tests from v[XXX] to v201:
[list of tests]

Workflow:
1. Verify behavior exists in v201 (run against v201 server)
2. Check assertions are version-agnostic (use isError() not specific messages)
3. Copy tests to v201 directory
4. Run `uctest v201/[path]` to verify
5. Delete original from v[XXX]
6. Run `ucsync` to regenerate inherited files
7. Run `uctest v[XXX]/[path]` to verify inheritance
8. If vuln test fails in later version, add exclusion
```

---

## Creating New Exercise from Scratch

```
Create new exercise: [description]

1. Check curriculum gaps:
   `/project:brainstorm-exercise "[idea]"`

2. Design the vulnerability:
   Delegate to uc-vulnerability-designer with:
   - Root cause (single concept)
   - Natural evolution pattern
   - Attack chain outline
   - Character mapping

3. Implement:
   uc-code-crafter with designer's output

4. Create demos:
   uc-exploit-narrator with code + designer output

5. Add e2e specs:
   uc-spec-author for new endpoints

6. Generate docs:
   `uv run docs generate --target [path]`

7. Verify and commit:
   commit-agent
```

---

## Comparing Exercise Versions

```
Compare v[A] and v[B] to understand changes:

1. Diff source code:
   `diff -r vulnerabilities/.../e[A] vulnerabilities/.../e[B]`

2. Check README for documented changes

3. Run specs for both:
   `uctest v[A]/` and `uctest v[B]/`

4. Identify:
   - New endpoints
   - Changed behavior
   - Fixed vulnerabilities
   - New vulnerabilities

5. Verify specs match observed behavior
```

---

## Fixing Inheritance Chain

```
Inheritance is broken for v[XXX]:
[describe symptoms]

Debug workflow:
1. Check spec.yml for correct `inherits:` value
2. Run `ucsync -n` to preview changes
3. Look for warnings about missing files
4. Check import statements reference correct files (~ prefix after porting)
5. Run `ucsync` then `uctest v[XXX]/` to verify

Common causes:
- spec.yml typo
- Deleted source file not excluded
- Import references non-inherited file
- @forceRef chain broken
```

---

## Validating Full Section (r01/r02/r03)

```
Validate entire section r[NN]:
[section path]

Comprehensive review:
1. Read section README
2. Run all version specs: `uctest v[start]/ && uctest v[end]/`
3. Validate all demos: `httpyac [...]/http/**/*.http -a`
4. Check inheritance: `/project:check-inheritance v[each]`
5. Review character consistency across exercises
6. Verify progressive complexity
7. Check for stale impacts (same thing 4+ times)

Report:
- Versions reviewed
- Tests passed/failed
- Demos validated/issues
- Inheritance health
- Recommendations
```

---

## Quick Health Check

```
Quick health check for v[XXX]:

1. `uctest v[XXX]/` - all specs pass?
2. `ucsync -n` - inheritance in sync?
3. `uv run docs verify` - docs valid?
4. Check git status - uncommitted changes?

If any fail, investigate before making further changes.
```
