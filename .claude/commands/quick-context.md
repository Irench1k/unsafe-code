---
description: "Dump current project state for quick orientation"
---

# Quick Context

Get oriented in the Unsafe Code Lab project quickly.

## Gather State

### Git Status
```bash
git status --short
git branch --show-current
git log --oneline -5
```

### Recent Changes
```bash
git diff --stat HEAD~3
```

### Active Version Detection
Look for recent work in:
- `spec/v*/` - Which version specs were touched?
- `vulnerabilities/.../e*/` - Which exercises modified?
- `.claude/` - Configuration changes?

## Project Structure Reminder

```
unsafe-code/
├── .claude/
│   ├── CLAUDE.md          # Orchestration guide
│   ├── agents/            # 12 specialized agents
│   ├── commands/          # Slash commands (you are here)
│   └── references/        # Shared reference docs
├── spec/
│   ├── spec.yml           # Inheritance config
│   ├── v201-v206/         # r02 (auth confusion)
│   └── v301-v307/         # r03 (authz confusion)
├── vulnerabilities/
│   └── python/flask/confusion/webapp/
│       ├── r01_*/         # Input source confusion
│       ├── r02_*/         # Authentication confusion
│       └── r03_*/         # Authorization confusion
└── tools/
    └── dev/               # uctest, ucsync, etc.
```

## Key Memories to Check

If you need deeper context, read these Serena memories:
- `pedagogical-design-philosophy` - Design principles
- `version-roadmap` - What each version introduces
- `spongebob-characters` - Character rules
- `http-demo-standards` - Demo quality standards
- `spec-inheritance-principles` - E2E spec patterns

## Common Starting Points

**Review exercises**: `/project:review-exercises v301-v303`
**Run specs**: `/project:run-specs v301/`
**Validate demos**: `/project:validate-demos e01`
**Check inheritance**: `/project:check-inheritance v302`
**Brainstorm new**: `/project:brainstorm-exercise "idea"`

## Quick Health Checks

```bash
# All v301 specs pass?
uctest v301/

# Inheritance in sync?
ucsync -n

# Docs generate?
uv run docs verify
```
