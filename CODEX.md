# Unsafe Code Lab - Codex Guide

> GitHub Copilot / OpenAI Codex configuration for Unsafe Code Lab

## Foundation

See `AGENTS.md` for complete instructions. Load it before any task.

## Quick Rules

### Priority of Truth
1. Section README (planned evolution)
2. Exercise source code (actual implementation)
3. E2E specs in `spec/vNNN/`
4. Interactive demos in `vulnerabilities/.../http/`

### Key Invariants
- Inheritance is DEFAULT for specs
- If inherited test fails → fix source code first
- Interactive demos: behavior only, no root cause
- ONE new concept per exercise
- Attacker uses THEIR OWN credentials

### Character Rules (SpongeBob)
- SpongeBob: NEVER an attacker
- Plankton: External attacker → targets Krabs
- Squidward: Insider threat → targets SpongeBob

## Tool Commands

```bash
uctest vNNN/        # Run e2e specs
ucsync              # Regenerate inherited files
httpyac file.http -a   # Run interactive demos
uclogs              # Docker logs
```

## Red Flags

- ❌ SpongeBob as attacker
- ❌ Victim's password in exploit
- ❌ Technical jargon in annotations
- ❌ Editing ~ prefixed files directly
- ❌ Same impact 4+ times

## Decision: Fix Code or Fix Test?

**If inherited test fails → CODE IS SUSPECT**

Check source code diff between versions before modifying tests.

## MCP Integration

This repo's Claude Code agents are available via Polyagent MCP server.

If configured, you can invoke agents like:
- `uc-spec-runner` - Run e2e tests
- `uc-spec-debugger` - Diagnose failures
- `uc-exploit-narrator` - Create demos
- `uc-maintainer` - Orchestrate workflows

See `.claude/agents/` for agent definitions.

## Workflows

See `docs/ai/runbooks.md` for complete workflow checklists:
- Extend E2E to next exercise
- Add new vulnerability exercise
- Fix failing specs
- Maximize inheritance
- Refresh interactive demos
