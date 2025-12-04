---
description: "Dump current project state for quick orientation"
model: haiku
---

# Quick Context

---

## ⛔⛔⛔ CRITICAL RESTRICTIONS - READ FIRST ⛔⛔⛔

### 1. PLAN MODE CHECK

**IF Plan Mode is active → STOP IMMEDIATELY.**

```
ERROR: This command is incompatible with Plan Mode.
Please restart without Plan Mode enabled.
```

### 2. BUILT-IN AGENTS ARE BANNED

**I MUST NEVER spawn these built-in subagent types:**

| Banned Agent | Why |
|--------------|-----|
| `Explore` | ❌ Bypasses our specialized agents |
| `Plan` | ❌ Interferes with command workflow |

### 3. THIS IS A READ-ONLY DIAGNOSTIC

This command only gathers state and reports it. It does NOT:
- ❌ Make changes
- ❌ Spawn agents
- ❌ Analyze deeply

---

Get oriented in the Unsafe Code Lab project quickly.

## Current State (Auto-Gathered)

### Git Status

!`git status --short`

### Current Branch

!`git branch --show-current`

### Recent Commits

!`git log --oneline -5`

### Recent Changes

!`git diff --stat HEAD~3 2>/dev/null || echo "Not enough history"`

### Docker Health

!`(cd vulnerabilities/python/flask/confusion/ && docker compose ps 2>/dev/null || echo "Docker not running")`

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
│   ├── agents/            # specialized agents
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

## Key Skills to Check

If you need deeper context, load these skills:

- `vulnerability-design-methodology` - Design principles
- `spongebob-characters` - Character rules
- `demo-conventions` - Demo quality standards
- `spec-conventions` - E2E spec patterns + inheritance

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
