# AI Knowledgebase Index

Authoritative map for AI agents working in Unsafe Code Lab. Use this as the entry point; each linked file has a single, clear scope.

| File | Scope | Use When |
|------|-------|----------|
| `unsafe-lab-playbook.md` | One-page orientation + starter checklists | Start of every session; remind yourself of invariants and tool belt |
| `invariants.md` | Non-negotiable rules (TDD, HTTP syntax invariants, characters, inheritance, code subtlety) | Any decision that could break rules or semantics |
| `http-syntax.md` | Complete `.http` syntax for both demos and specs | Before editing any `.http` file |
| `http-demos.md` | Conventions for student-facing demos (ucdemo) | Writing or debugging `vulnerabilities/.../http/*.http` |
| `http-specs.md` | Conventions for E2E specs (uctest) and helpers | Writing or debugging `spec/**/*.http` or `spec/spec.yml` |
| `spec-vs-demo.md` | Side-by-side differences in purpose, syntax, and style | Choosing patterns or troubleshooting context mixups |
| `tools.md` | CLI references for ucdemo/uctest/ucsync, docker helpers, linting, docs generation | Running tools or recalling flags/paths |
| `curriculum.md` | Section/version map, directory layout, blueprint wiring, `@unsafe` requirements | Adding/understanding exercises or routing |
| `characters.md` | Canonical character rules, attack relationships, narrative patterns | Selecting attackers/victims or writing impact text |
| `runbooks.md` | Step-by-step workflows for common tasks (failing demo/spec, new exercise, refresh demos, pre-commit, etc.) | Executing a task and need ordered steps |
| `decision-trees.md` | Diagnostic trees for failures, inheritance issues, assertion placement | When stuck deciding code vs test vs exclusion |

Quick commands (see `tools.md` for details):
- `ucdemo r03` — run demos in section 03
- `uctest v301/` — run specs for v301
- `ucsync` — regenerate inherited specs
- `uclogs -f` — tail Docker logs

Task routing (start here):
- Fix failing demo → `runbooks.md` §1
- Fix failing spec → `runbooks.md` §2 + `decision-trees.md` §§1–2
- Add new exercise → `runbooks.md` §4 + `curriculum.md`
- Maximize inheritance/backport → `runbooks.md` §5 + `decision-trees.md` §§6–9
- Refresh demos or storytelling → `runbooks.md` §8 + `characters.md`

If anything in this index becomes outdated, fix the target doc and update the table so new sessions land on the right source.
