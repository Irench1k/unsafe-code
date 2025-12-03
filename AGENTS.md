# Unsafe Code Lab – Agent Guide

> **Single Source of Truth** for all AI agents (Claude, Cursor, Codex, Gemini, Copilot).
> Load this file before starting any task.

## 1. Mental Model (CRITICAL)

### Project Structure
- **Progressive SaaS versions**: v101 → v201 → v301...
- **Each version cycle**: Intentional vulnerability introduced, previous vulnerability fixed
- **Section README is authoritative**: e.g., `r03_authorization_confusion/README.md` defines what each exercise should do

### Directory Layout
```
vulnerabilities/python/flask/confusion/webapp/
├── r01_input_source_confusion/     # Section 1
├── r02_authentication_confusion/   # Section 2
├── r03_authorization_confusion/    # Section 3
│   ├── README.md                   # AUTHORITATIVE: SaaS evolution plan
│   ├── e01_dual_auth_refund/       # Exercise code
│   ├── e02_cart_swap_checkout/
│   └── http/                       # Interactive demos
│       ├── e01/
│       │   ├── e01_dual_auth_refund.exploit.http
│       │   └── e01_dual_auth_refund.fixed.http
│       └── ...

spec/
├── spec.yml           # Inheritance configuration
├── v201/, v202/...    # E2E specs per version
└── utils.cjs          # Test helpers
```

---

## 2. Priority of Truth

When sources conflict, follow this order:

1. **Section README** (`vulnerabilities/.../rXX_*/README.md`)
   - Planned SaaS evolution, teaching goals, intended vulnerabilities

2. **Exercise source code** (`vulnerabilities/.../eXX_*/`)
   - Actual implementation (may have bugs vs README intent)

3. **E2E specs** (`spec/vNNN/`)
   - Behavioral contracts, run via `uctest`

4. **Interactive demos** (`vulnerabilities/.../http/`)
   - Student-facing exploit demonstrations

---

## 3. Hard Invariants

### Inheritance Rules
- **Inheritance is DEFAULT**. Breaking it = alarm bells.
- If inherited test fails → investigate **SOURCE CODE first**
- Refactoring can accidentally fix vulnerabilities
- Prefer **adding** new .http specs over modifying/removing inherited ones

### Demo Rules
- Interactive demos: **behavior + impact only**, no root-cause explanation
- **ONE assert per test** in demos (unlike e2e specs which can have many)
- **ONE new concept per exercise**

### Evolution Rules
- Next version extends previous (new endpoints, new features)
- Rarely breaks backward compatibility
- APIs accrue functionality, they don't remove it

---

## 4. Tool Commands

| Command | Purpose |
|---------|---------|
| `uctest vNNN/` | Run e2e specs for version |
| `uctest @tag vNNN/` | Run specs with specific tag |
| `ucsync` | Regenerate inherited files from spec.yml |
| `ucsync -n` | Preview inheritance changes |
| `httpyac file.http -a` | Run interactive demo |
| `uclogs` | Docker compose logs (debugging) |
| `uv run docs generate --target [path]` | Generate README.md |
| `uv run docs verify` | Verify annotations |

### Common Debugging
```bash
# Reset database (when balance tests fail)
uctest @setup vNNN/

# See execution plan without running
uctest --show-plan vNNN/path

# Continue after failures
uctest -k vNNN/
```

---

## 5. Character Rules (SpongeBob Universe)

### Cast & Credentials

| Character | Role | Credentials | Email |
|-----------|------|-------------|-------|
| SpongeBob | Innocent victim | `spongebob` / `bikinibottom` | `spongebob@krusty-krab.sea` |
| Squidward | Insider threat | `squidward` / `clarinet123` | `squidward@krusty-krab.sea` |
| Plankton | External attacker | `plankton` / `i_love_my_wife` | `plankton@chum-bucket.sea` |
| Mr. Krabs | Admin/owner | — | `krabs@krusty-krab.sea` |
| Patrick | VIP customer | `patrick` / `pineapple` | `patrick@bikini-bottom.sea` |

### Attack Relationships
```
Squidward ──[insider grudge]──► SpongeBob
Plankton ──[business rival]──► Mr. Krabs
```

### Golden Rule
**Attacker uses THEIR OWN credentials.**

The exploit comes from **confusion**, not password theft.

```http
# WRONG - using victim's password
Authorization: Basic {{btoa("spongebob:bikinibottom")}}

# CORRECT - attacker's own credentials
Authorization: Basic {{btoa("squidward:clarinet123")}}
GET /messages?user=spongebob  # confusion happens here
```

### Section Character Mapping

| Section | Typical Attacker | Typical Victim |
|---------|------------------|----------------|
| r01 (Input Source) | Squidward | SpongeBob |
| r02 (Authentication) | Squidward | SpongeBob |
| r03 (Authorization) | Plankton | Mr. Krabs |

### Variety by Example 4-5
Avoid staleness by rotating:
- Attacker (Squidward → Plankton)
- Victim (SpongeBob → Mr. Krabs)
- Impact (read → delete → modify)
- Function (messages → orders → menu)

---

## 6. Red Flags (Stop & Think)

- ❌ **SpongeBob as attacker** - NEVER
- ❌ **Victim's password in exploit** - Use attacker's own credentials
- ❌ **Technical jargon in annotations** - "SpongeBob checks his messages" not "User authenticates and retrieves messages"
- ❌ **Same impact 4+ times** - Rotate characters, methods, consequences
- ❌ **@base in examples 1-2** - Students need full URLs first
- ❌ **Multiple new concepts in one example** - ONE concept per exercise
- ❌ **Editing ~ prefixed files** - Run `ucsync` instead
- ❌ **Excluding inherited test without investigation** - Check source code first

---

## 7. E2E Specs vs Interactive Demos

| Aspect | E2E Specs (`spec/`) | Interactive Demos (`http/`) |
|--------|---------------------|----------------------------|
| **Purpose** | Behavioral contracts | Student teaching |
| **Asserts** | Multiple OK | ONE per test |
| **Syntax** | Full utils.cjs helpers | Plain httpyac |
| **DRY** | Heavy imports, canonical happy.http | Self-contained |
| **Style** | Technical, comprehensive | Narrative, engaging |
| **Focus** | Cover all cases | Show business impact |
| **Auth** | `{{auth.basic("plankton")}}` | `Authorization: Basic ...` |
| **Response** | `$(response).field("x")` | `response.parsedBody.x` |

---

## 8. Agent Roster

### Content & Docs
| Agent | Purpose |
|-------|---------|
| `content-planner` | Design exercises, taxonomy, and curriculum progression |
| `code-author` | Implement vulnerable code to match the design |
| `docs-author` | Polish READMEs, annotations, learner docs |

### Spec (E2E) Agents
| Agent | Purpose |
|-------|---------|
| `spec-runner` | Run `uctest` and `ucsync`; summarize failures |
| `spec-debugger` | Diagnose spec failures; decide who fixes |
| `spec-author` | Write/fix `spec/**/*.http` tests |

### Demo Agents
| Agent | Purpose |
|-------|---------|
| `demo-author` | Create/maintain interactive demos (`*.exploit.http`, `*.fixed.http`) |
| `demo-debugger` | Diagnose demo/httpyac failures |

### Infrastructure
| Agent | Purpose |
|-------|---------|
| `infra-maintainer` | Maintain tools, docs generator, Docker, scripts |
| `commit-agent` | Verify + commit changes |
| `uc-maintainer` | Top-level orchestrator (name unchanged) |

**Spec vs Demo editing lock:** Only `spec-author`, `spec-debugger`, `demo-author`, and `demo-debugger` may edit `.http` files. Others must delegate.

---

## 9. Decision Trees

### When Inherited Test Fails

```
Inherited test fails in vN+1
├── Was behavior supposed to change? (Check README)
│   ├── YES → spec-author: adjust spec for new behavior
│   └── NO → Continue...
├── Did refactoring accidentally fix the vulnerability?
│   ├── YES → spec-runner: add exclusion to spec.yml, run ucsync
│   └── NO → Continue...
└── Is there a bug in the exercise code?
    └── YES → code-author: fix to match intended behavior
```

### When to Fix Code vs Spec

```
Test fails
├── Inherited from earlier version? → SUSPECT CODE
├── New test for new feature? → Verify assertion logic
├── "ref not found"? → Run ucsync, check imports
└── Assertion mismatch?
    ├── API changed intentionally → Fix spec (spec-author)
    └── API changed accidentally → Fix code (code-author)
```

---

## 10. Workflow Quick Reference

### Extend E2E to Next Exercise
1. Read section README
2. `uctest vN/` (baseline green?)
3. Update spec.yml if needed
4. `ucsync && uctest vN+1/` via spec-runner
5. Debug failures → code-author or spec-author
6. Verify all green

### Add New Vulnerability Exercise
1. `content-planner` → design
2. `code-author` → implement
3. `spec-author` + `spec-runner` → specs + inheritance
4. `demo-author` → demos
5. `docs-author` → polish
6. `commit-agent` → finalize

### Fix Failing Specs
1. `spec-runner` → run, capture failures
2. `spec-debugger` → classify each failure
3. Appropriate fix agent (spec-author / code-author / spec-runner) → fix
4. `spec-runner` → verify

See `docs/ai/runbooks.md` for complete workflows.

---

## 11. Claude Code Skills

Skills auto-load based on context.

### Available Skills

| Skill | Auto-Triggers When | Location |
|-------|-------------------|----------|
| `http-editing-policy` | Any `.http` proximity (enforces delegation) | `.claude/skills/http-editing-policy/` |
| `http-syntax` | Editing any `.http` | `.claude/skills/http-syntax/` |
| `http-gotchas` | Editing/reviewing `.http` | `.claude/skills/http-gotchas/` |
| `http-demo-conventions` | Working in `vulnerabilities/.../http/` | `.claude/skills/http-demo-conventions/` |
| `http-spec-conventions` | Working in `spec/vNNN/` | `.claude/skills/http-spec-conventions/` |
| `http-spec-debugging` | Investigating failing `uctest` runs | `.claude/skills/http-spec-debugging/` |
| `http-spec-inheritance` | Editing `spec.yml` / running `ucsync` | `.claude/skills/http-spec-inheritance/` |
| `spongebob-characters` | Choosing attacker/victim for demos | `.claude/skills/spongebob-characters/` |
| `vulnerability-design-methodology` | Planning new exercises | `.claude/skills/vulnerability-design-methodology/` |
| `vulnerable-code-patterns` | Implementing vulnerable code | `.claude/skills/vulnerable-code-patterns/` |
| `documentation-style` | Polishing docs | `.claude/skills/documentation-style/` |
| `uclab-tools` | Running uctest/ucsync/httpyac | `.claude/skills/uclab-tools/` |
| `commit-workflow` | Preparing commits | `.claude/skills/commit-workflow/` |

### E2E vs Demo Distinction

| Working In | Agents to Use | Core Skills | Syntax |
|------------|---------------|------------|--------|
| `spec/**/*.http` | spec-author / spec-debugger / spec-runner | http-editing-policy, http-syntax, http-gotchas, http-spec-conventions | `$(response).field()`, `auth.basic()` |
| `vulnerabilities/.../http/**/*.http` | demo-author / demo-debugger | http-editing-policy, http-syntax, http-gotchas, http-demo-conventions | `response.parsedBody`, manual headers |

### Agent Resume Pattern

For long-running or multi-step tasks, agents can be **resumed** to continue from where they left off. This preserves context and avoids re-reading files.

**When to use resume:**
- Agent hit a blocker and needs human input
- Task was interrupted but context is still valid
- Continuing iterative refinement

**How to resume:**
```
Use the Task tool with:
- subagent_type: "spec-debugger"
- resume: "{agent_id}"  # ID from previous run
- prompt: "Continue with the fix for..."
```

**Best practices:**
- Resume the same agent type (don't resume spec-runner as spec-author)
- Provide brief context of what changed since last run
- Clear the resume if starting fresh on same problem

### Human Contributor Guide

See `docs/MAINTAINER_AI.md` for human-readable AI tool documentation.
