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

### Content Agents
| Agent | Purpose |
|-------|---------|
| `uc-vulnerability-designer` | Design WHAT to build, WHY it matters |
| `uc-code-crafter` | Implement vulnerable code |
| `uc-exploit-narrator` | Create .http PoC demos |

### Docs Agents
| Agent | Purpose |
|-------|---------|
| `uc-docs-editor` | Edit READMEs, polish text |
| `uc-taxonomy-maintainer` | Maintain @unsafe annotations |
| `uc-curriculum-strategist` | Gap analysis, curriculum planning |

### Spec Agents
| Agent | Purpose |
|-------|---------|
| `uc-spec-runner` | Execute uctest (haiku - fast) |
| `uc-spec-debugger` | Diagnose failures (sonnet) |
| `uc-spec-author` | Write/fix .http tests (sonnet) |
| `uc-spec-sync` | Manage inheritance (haiku) |

### Infrastructure
| Agent | Purpose |
|-------|---------|
| `uc-docs-generator-maintainer` | Maintain `uv run docs` tooling |
| `commit-agent` | Verify + commit changes |
| `uc-maintainer` | Top-level orchestrator |

---

## 9. Decision Trees

### When Inherited Test Fails

```
Inherited test fails in vN+1
├── Was behavior supposed to change? (Check README)
│   ├── YES → uc-spec-author: adjust spec for new behavior
│   └── NO → Continue...
├── Did refactoring accidentally fix the vulnerability?
│   ├── YES → Add exclusion to spec.yml, document WHY
│   └── NO → Continue...
└── Is there a bug in the exercise code?
    └── YES → uc-code-crafter: fix to match intended behavior
```

### When to Fix Code vs Spec

```
Test fails
├── Inherited from earlier version? → SUSPECT CODE
├── New test for new feature? → Verify assertion logic
├── "ref not found"? → Check imports, run ucsync
└── Assertion mismatch?
    ├── API changed intentionally → Fix spec
    └── API changed accidentally → Fix code
```

---

## 10. Workflow Quick Reference

### Extend E2E to Next Exercise
1. Read section README
2. `uctest vN/` (baseline green?)
3. Update spec.yml to inherit
4. `ucsync && uctest vN+1/`
5. Debug failures → code fix OR spec fix
6. Verify all green

### Add New Vulnerability Exercise
1. `uc-vulnerability-designer` → design
2. `uc-code-crafter` → implement
3. `uc-spec-author` + `uc-spec-sync` → specs
4. `uc-exploit-narrator` → demos
5. `commit-agent` → finalize

### Fix Failing Specs
1. `uc-spec-runner` → run, capture failures
2. `uc-spec-debugger` → classify each failure
3. Appropriate fix agent → fix
4. `uc-spec-runner` → verify

See `docs/ai/runbooks.md` for complete workflows.

---

## 11. Claude Code Skills

Skills provide auto-loaded context when working in specific areas. They load just-in-time based on file patterns and task context.

### Available Skills

| Skill | Auto-Triggers When | Location |
|-------|-------------------|----------|
| `http-e2e-specs` | Working in `spec/vNNN/`, using `$(response)`, `@ref` | `.claude/skills/http-e2e-specs/` |
| `http-interactive-demos` | Working in `http/eNN/`, `.exploit.http` files | `.claude/skills/http-interactive-demos/` |
| `http-assertion-gotchas` | Assertion failures, 500 errors, syntax issues | `.claude/skills/http-assertion-gotchas/` |
| `spec-inheritance` | "ref not found", `ucsync`, `spec.yml` edits | `.claude/skills/spec-inheritance/` |
| `spongebob-characters` | Choosing attacker/victim, writing demos | `.claude/skills/spongebob-characters/` |
| `uclab-tools` | Running tests, debugging, CLI commands | `.claude/skills/uclab-tools/` |

### Skill Contents

Each skill directory contains:
- `SKILL.md` - Main skill with frontmatter description (triggers auto-loading)
- Supporting files - Detailed reference docs

### E2E vs Demo Distinction

**This is the most critical distinction.** Skills enforce it:

| Working In | Skill Loaded | Syntax |
|------------|--------------|--------|
| `spec/vNNN/` | `http-e2e-specs` | `$(response).field()`, `auth.basic()` |
| `http/eNN/` | `http-interactive-demos` | `response.parsedBody`, manual headers |

### Human Contributor Guide

See `docs/MAINTAINER_AI.md` for human-readable AI tool documentation.
