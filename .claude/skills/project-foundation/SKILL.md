---
name: project-foundation
description: Core project knowledge for ALL Unsafe Code Lab agents. Auto-loads version structure, repository layout, infrastructure rules, agent roster, and key invariants. MUST be loaded by every agent.
---

# Unsafe Code Lab Foundation

**Every agent MUST understand this foundation before doing any work.**

---

## ⛔⛔⛔ INFRASTRUCTURE RULE - NON-NEGOTIABLE ⛔⛔⛔

### Docker Is ALWAYS Running

**`ucup` is running in the background with auto-reload enabled.**

| ❌ NEVER Do | ✅ Instead |
|-------------|-----------|
| `docker compose up` | User manages via `ucup` |
| `python app.py` | App runs in Docker, auto-reloads |
| `pip install` / `uv sync` on host | Dependencies are in Docker |
| `source .venv/bin/activate` | No local venv needed |
| Start/restart services | Ask user to check `ucup` |

**Verify changes work:**
```bash
uclogs --since 1m                    # Check app reloaded
uclogs --since 2m | grep -i error    # Check for errors
```

**If Docker seems down - SAY THIS:**
> "Docker compose doesn't seem to be responding. Could you check if `ucup` is running?"

---

## Version Structure

### Format: `vNMM`

```
v{N}{MM} → Section r0{N}, Exercise e{MM}

Examples:
  v101 → r01_authentication_confusion/e01_session_vs_basic/
  v203 → r02_input_source_confusion/e03_header_injection/
  v301 → r03_authorization_confusion/e01_dual_auth_refund/
  v403 → r04_cardinality_confusion/e03_duplicate_coupons/
```

### Sections (Current)

| Section | Name | Focus |
|---------|------|-------|
| r01 | Authentication Confusion | Who is this user? Token vs session vs API key |
| r02 | Input Source Confusion | Where does the value come from? URL vs body vs header |
| r03 | Authorization Confusion | What are they allowed to do? Owner vs admin vs delegated |
| r04 | Cardinality Confusion | How many? Single vs multiple, one-time vs reusable |

### Parsing a Version

```python
version = "v403"
section_num = int(version[1])      # 4
exercise_num = int(version[2:])    # 03
section_dir = f"r0{section_num}_*" # r04_*
exercise_dir = f"e{exercise_num:02d}_*"  # e03_*
```

---

## Repository Layout

```
vulnerabilities/python/flask/confusion/
├── webapp/
│   ├── r01_authentication_confusion/
│   │   ├── README.md              # Section plan (AUTHORITATIVE)
│   │   ├── routes.py              # Blueprint registration
│   │   ├── http/                  # Interactive demos
│   │   │   ├── .httpyac.js        # Demo config
│   │   │   ├── common/setup.http  # Shared setup
│   │   │   ├── e01/               # Exercise 01 demos
│   │   │   ├── e02/               # Exercise 02 demos
│   │   │   └── ...
│   │   ├── e01_session_vs_basic/  # Exercise code
│   │   │   ├── __init__.py        # create_app(), blueprints
│   │   │   ├── config.py          # Version string
│   │   │   ├── routes/            # Endpoint handlers
│   │   │   ├── auth/              # Auth decorators (often vulnerable!)
│   │   │   └── database/          # Models, services, fixtures
│   │   └── e02_.../
│   ├── r02_input_source_confusion/
│   ├── r03_authorization_confusion/
│   └── r04_cardinality_confusion/
│
spec/
├── spec.yml                       # Inheritance configuration
├── utils.cjs                      # E2E test helpers
├── v101/                          # Version specs
├── v102/                          # Inherits from v101
└── ...

tools/
├── cli/                           # CLI tools (uctest, ucdemo, etc.)
└── docs/                          # Documentation generator
```

---

## Exercise Development Lifecycle

```
1. DESIGN (content-planner)
   └── What vulnerability? What endpoints? What narrative?

2. DEMO FIRST (demo-author)
   └── Write exploit/fixed demos that assert expected behavior
   └── Demos SHOULD FAIL initially (TDD)

3. CODE (code-author)
   └── Implement vulnerability with @unsafe annotation
   └── Make demos pass

4. FIX PREVIOUS (code-author)
   └── Fix the PREVIOUS exercise's vulnerability
   └── Make fixed demo pass

5. SPECS (spec-author)
   └── Port demo assertions to E2E specs
   └── Set up inheritance in spec.yml

6. DOCS (docs-author)
   └── Align README with implementation
   └── Behavioral language, not security jargon

7. COMMIT (commit-agent)
   └── Verify all quality gates
   └── Create appropriate commit
```

### What Makes a Complete Exercise

- [ ] Vulnerability implemented with `@unsafe` annotation
- [ ] Previous vulnerability is fixed
- [ ] `*.exploit.http` demo shows attack succeeds
- [ ] `*.fixed.http` demo shows attack blocked
- [ ] E2E specs test vulnerability
- [ ] E2E specs test normal functionality
- [ ] README matches implementation

---

## Agent Roster

| Agent | Purpose | Edits |
|-------|---------|-------|
| `code-author` | Implement vulnerable Flask code | Python files ONLY |
| `demo-author` | Write interactive demos | `vulnerabilities/**/*.http` ONLY |
| `demo-debugger` | Diagnose demo failures | Read-only (mostly) |
| `spec-author` | Write E2E specs | `spec/**/*.http` ONLY |
| `spec-debugger` | Diagnose spec failures | Read-only (mostly) |
| `spec-runner` | Run uctest, manage ucsync | No .http editing |
| `content-planner` | Design vulnerabilities | Design docs, no code |
| `docs-author` | Edit READMEs, annotations | Markdown ONLY |
| `infra-maintainer` | Maintain tools, Docker | `tools/`, configs |
| `commit-agent` | Verify and commit | Git operations |
| `uc-maintainer` | Complex orchestration | Delegates to others |

### .HTTP File Restriction

**CRITICAL: Only blessed agents may edit `.http` files.**

| Pattern | Analyze | Edit |
|---------|---------|------|
| `spec/**/*.http` | spec-debugger | spec-author |
| `vulnerabilities/**/*.http` | demo-debugger | demo-author |

**All other agents MUST delegate `.http` work.**

---

## Key Invariants

### Testing
- **TDD-1**: Demo/spec must fail when feature is missing
- **INH-1**: New versions inherit specs from previous
- **INH-4**: NEVER edit `~` files directly (run ucsync)

### .HTTP Syntax
- **HTTP-1**: NO quotes on RHS (`== pending` not `== "pending"`)
- **HTTP-2**: Assertions NEED operators (`== true`, not just expression)
- **HTTP-3**: Demos use `response.parsedBody`, specs use `$(response)`

### Characters
- **CHAR-1**: Attacker uses THEIR OWN credentials (never victim's password)
- **CHAR-2**: SpongeBob is NEVER an attacker
- **CHAR-3**: Plankton → Krusty Krab, Squidward → SpongeBob

### Code
- **CODE-1**: Vulnerabilities must be subtle (no `vulnerable_` names)
- **CODE-2**: Production-quality code with proper error handling
- **CODE-3**: ONE concept per exercise

---

## CLI Tools Quick Reference

### uctest - E2E Specs
```bash
uctest v301/                    # All specs for version
uctest v301/cart/checkout/      # Specific endpoint
uctest v301/ --tag authn        # Filter by tag
uctest v301/ -v                 # Verbose output
uctest v301/ --fail-fast        # Stop on first failure
```

### ucdemo - Interactive Demos
```bash
ucdemo r02                      # All demos in section
ucdemo r02/e03                  # Specific exercise
ucdemo path/to/file.http        # Single file
ucdemo r02 --bail               # Stop on first failure
ucdemo r02 -v                   # Verbose output
```

### ucdiff - Exercise Comparison
```bash
ucdiff v307                     # Tree view of changes
ucdiff v307 -o                  # Function outline
ucdiff v307 -c                  # Code diff
ucdiff v307 -cS                 # Side-by-side
ucdiff r03 -e                   # Section evolution
```

### ucsync - Inheritance Manager
```bash
ucsync v302                     # Regenerate inherited files
ucsync v302 --check             # Dry run
ucsync --all                    # Sync all versions
```

### uclogs - Docker Logs
```bash
uclogs                          # Recent logs
uclogs -f                       # Follow (tail -f)
uclogs --since 5m               # Last 5 minutes
uclogs --level error            # Errors only
```

---

## File Naming Conventions

### Exercise Code
```
e{NN}_{descriptive_name}/
  e01_session_vs_basic/
  e02_dual_auth_refund/
  e03_duplicate_coupons/
```

### Demo Files
```
e{NN}_{slug}.exploit.http    # Shows vulnerability works
e{NN}_{slug}.fixed.http      # Shows fix blocks exploit
e{NN}_{slug}.intended.http   # Shows intended behavior (optional)
```

### Spec Files
```
spec/v{NMM}/
  endpoint/
    method/
      happy.http             # Normal path
      authn.http             # Authentication tests
      authz.http             # Authorization tests
      vuln-{name}.http       # Vulnerability-specific
```

---

## Error Recovery Guide

### "Connection refused"
Docker not running. Ask user to check `ucup`.

### "ref X not found"
```bash
ucsync vNNN --check    # See what's missing
ucsync vNNN            # Regenerate
```

### "500 Internal Server Error"
```bash
uclogs --since 5m      # Check server errors
```

### "Assertion syntax error"
Missing operator. Use `== true`, `> 0`, not bare expressions.

### Import/module errors
Check `uclogs` for traceback, fix the import path.

### Database errors
May need `ucdown && ucup` to reinitialize. Ask user.

---

## See Also

- `uclab-tools` skill - Full CLI tool documentation
- `http-syntax` + `http-gotchas` skills - .http file syntax
- `spec-conventions` skill - E2E spec patterns
- `demo-conventions` skill - Demo patterns
- `spongebob-characters` skill - Character rules
- `vulnerable-code-patterns` skill - Code implementation
