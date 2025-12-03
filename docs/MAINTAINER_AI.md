# AI-Assisted Development Guide

Guide for human contributors on using AI tools effectively in Unsafe Code Lab.

## Overview

This project uses Claude Code with specialized agents and auto-loading Skills. The AI tools are optimized for:

- Writing E2E specs and interactive demos
- Managing test inheritance across versions
- Creating vulnerability demonstrations
- Maintaining documentation consistency

## Quick Start

### 1. Use Slash Commands

```bash
# Review exercises comprehensively
/project:review-exercises v301-v303

# Run E2E specs with smart interpretation
/project:run-specs v301/

# Validate interactive demos
/project:validate-demos e01

# Check inheritance health
/project:check-inheritance v302

# Brainstorm new vulnerability ideas
/project:brainstorm-exercise "type confusion in JSON parsing"

# Get quick context dump
/project:quick-context
```

### 2. Skills Auto-Load

Claude automatically loads relevant Skills based on context:

| Working In | Auto-Loaded Skill |
|------------|-------------------|
| `spec/vNNN/` files | `http-e2e-specs` |
| `http/eNN/` directories | `http-interactive-demos` |
| Assertion failures | `http-assertion-gotchas` |
| `spec.yml`, ucsync | `spec-inheritance` |
| Demo narratives | `spongebob-characters` |
| CLI tool usage | `uclab-tools` |

### 3. Subagents Handle Complex Work

Specialized agents are delegated automatically:

| Task Type | Agent |
|-----------|-------|
| Run E2E specs | `uc-spec-runner` |
| Debug failures | `uc-spec-debugger` |
| Write/fix tests | `uc-spec-author` |
| Manage inheritance | `uc-spec-sync` |
| Create demos | `uc-exploit-narrator` |
| Design vulnerabilities | `uc-vulnerability-designer` |

## Key Workflows

### Writing E2E Specs

1. Work in `spec/vNNN/` directory
2. Claude auto-loads `http-e2e-specs` skill
3. Use helpers like `$(response).field()`, `auth.basic()`
4. Run with `uctest v301/path/to/file.http`

```http
### Test title here
# @tag authn, v301
POST /endpoint
Authorization: {{auth.basic("plankton")}}

?? js $(response).status() == 200
?? js $(response).field("email") == {{user("plankton").email}}
```

### Creating Interactive Demos

1. Work in `vulnerabilities/.../http/eNN/`
2. Claude auto-loads `http-interactive-demos` skill
3. Use plain `response.parsedBody` (NO utils.cjs helpers!)
4. Run with `httpyac file.http -a`

```http
### SpongeBob checks his messages
GET {{host}}/messages
Authorization: Basic {{btoa("spongebob:bikinibottom")}}

?? status == 200

### EXPLOIT: Squidward reads SpongeBob's messages
GET {{host}}/messages?user=spongebob
Authorization: Basic {{btoa("squidward:clarinet123")}}

?? status == 200
# IMPACT: Squidward accessed SpongeBob's private data!
```

### Fixing Spec Failures

1. Run `/project:fix-failing-specs v301/`
2. Claude uses `spec-inheritance` skill automatically
3. **Remember**: Inherited test fails → suspect code first!

Decision flow:
```
Inherited test fails
├── Check source code for changes
├── Did refactoring accidentally fix vuln?
│   └── YES → Restore vulnerable code
└── Should test be excluded?
    └── Only after confirming vuln shouldn't exist
```

### Managing Inheritance

```bash
# Regenerate inherited files
ucsync v302
```

## Critical Distinctions

### E2E Specs vs Interactive Demos

| Aspect | E2E Specs | Interactive Demos |
|--------|-----------|-------------------|
| Location | `spec/vNNN/` | `http/eNN/` |
| Run with | `uctest` | `httpyac` |
| Response access | `$(response).field()` | `response.parsedBody` |
| Auth helper | `{{auth.basic()}}` | Manual `Authorization:` header |
| Imports | Heavy use | NO imports (except setup.http) |
| Asserts per test | Multiple OK | ONE per test |
| Style | Technical, DRY | Narrative, engaging |

### Confusion Categories

| Category | Style | Implications |
|----------|-------|--------------|
| `confusion/` | Sequential | Progressive complexity (r01→r02→r03) |
| Others | Random-access | Each example standalone |

## File Conventions

| Pattern | Meaning |
|---------|---------|
| `~*.http` | INHERITED - never edit directly |
| `*.exploit.http` | Shows vulnerability succeeds |
| `*.fixed.http` | Shows vulnerability is fixed |
| `_fixtures.http` | Shared setup (no tags) |
| `_imports.http` | Import chain file |

## Character Rules

**Attacker uses THEIR OWN credentials** - exploit = confusion, not password theft!

| Character | Role | Use For |
|-----------|------|---------|
| SpongeBob | Victim | Never attacker |
| Squidward | Insider threat | r01, r02 attacks |
| Plankton | External attacker | r03+ attacks |
| Patrick | VIP victim | High-impact scenarios |

## Assertion Gotchas

1. **Operator required** - `?? js value` becomes body → 500!
2. **No quotes on RHS** - `== "approved"` fails
3. **Assertions run AFTER request** - capture pre-state in `{{ }}`
4. **Use parseFloat()** for numeric comparisons

## Available Tools

### CLI Commands

```bash
uctest v301/          # Run E2E specs
httpyac file.http -a  # Run demos
ucsync v302           # Manage inheritance
uclogs                # View Docker logs
uv run docs generate  # Generate READMEs
```

### Slash Commands

| Command | Purpose |
|---------|---------|
| `/project:run-specs v301/` | Run E2E specs |
| `/project:review-exercises v301-v303` | Full review |
| `/project:validate-demos e01` | Check demo quality |
| `/project:check-inheritance v302` | Inheritance health |
| `/project:brainstorm-exercise "idea"` | New vulnerability ideation |
| `/project:quick-context` | Dump current state |

## Quality Checklist

Before committing changes:

- [ ] E2E specs pass (`uctest v301/`)
- [ ] Interactive demos run (`httpyac ... -a`)
- [ ] Character logic correct (attacker uses own creds)
- [ ] ONE new concept per example
- [ ] No technical jargon in demo annotations
- [ ] READMEs regenerated if annotations changed

## Red Flags

Stop and reconsider if you see:

- ❌ SpongeBob as attacker
- ❌ Victim's password in exploit request
- ❌ Technical jargon in demo annotations
- ❌ About to edit a `~` prefixed file
- ❌ About to exclude inherited test without checking code
- ❌ Multiple new concepts in one example

## Getting Help

- Skills: Auto-load based on file context
- Slash commands: `/project:*` for common workflows
- AGENTS.md: Full agent documentation
- docs/ai/: Decision trees and runbooks
