---
description: "Self-improving: review conversation, identify gaps, propose .claude/ improvements"
model: opus
argument-hint: [feedback]
---

# Align Configuration: $ARGUMENTS

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
| `general-purpose` | ❌ No domain skills |

### 3. THIS COMMAND EDITS .CLAUDE/ FILES DIRECTLY

Unlike other commands, `/meta/align` IS allowed to:
- ✅ Read and edit `.claude/` configuration files
- ✅ Analyze conversation history
- ✅ Propose and implement config improvements

But it MUST NOT:
- ❌ Spawn built-in agents for analysis
- ❌ Edit source code or test files
- ❌ Run tests or bash commands beyond diagnostics

---

Review this conversation, identify where .claude/ configuration fell short, propose and implement improvements.

## Purpose

When commands/agents don't meet expectations, this command:
1. **Introspects** - Reviews conversation history
2. **Analyzes** - Finds gaps between expectations and behavior
3. **Diagnoses** - Identifies root cause in .claude/ configuration
4. **Proposes** - Suggests specific improvements
5. **Implements** - Makes changes (with approval)

## Mindset

- **Eager** to understand unstated requirements
- **Proactive** at anticipating patterns behind complaints
- **Holistic** - looks at .claude/ configuration as a system
- **Problem-focused** - solves issues, doesn't debate methods
- **Creates** new commands/skills when existing ones don't fit

## Workflow

### Step 1: Introspect

Review the conversation above:
- What commands/skills were invoked?
- What did the user ask for?
- What did the agent actually do?
- Where was the disconnect?

### Step 2: Analyze Gaps

Common gap patterns:

| Symptom | Likely Cause |
|---------|--------------|
| Agent missed requirement | Command lacks explicit instruction |
| Wrong agent invoked | CLAUDE.md routing table incomplete |
| Agent didn't know how | Missing skill or insufficient detail |
| Agent over-complicated | Command encourages over-engineering |
| Agent asked too many questions | Command lacks defaults/opinions |
| Workflow didn't match user's | Command structured for different use case |

### Step 3: Diagnose Root Cause

Check these files:
- `.claude/CLAUDE.md` - Routing, global instructions
- `.claude/commands/` - Command definitions
- `.claude/agents/` - Agent boundaries
- `.claude/skills/` - Domain knowledge

Questions to answer:
- Is there a command for this task? Should there be?
- Does the command capture the user's intent, not just steps?
- Are skills loaded that should be?
- Does agent routing match the task?

### Step 4: Propose Improvements

Options (from most to least common):

1. **Edit existing command** - Add missing instruction, clarify intent
2. **Create new command** - For recurring task pattern
3. **Edit skill** - Add domain knowledge
4. **Create new skill** - For new domain area
5. **Edit agent** - Adjust boundaries/responsibilities
6. **Edit CLAUDE.md** - Update routing or global behavior

### Step 5: Implement

Present proposed changes. On approval:
1. Make edits to .claude/ files
2. Verify changes don't break existing commands
3. Summarize what changed and why

## User Feedback Patterns

**"It didn't understand what I wanted"**
→ Command lacks intent/philosophy section

**"It did too much / too little"**
→ Command scope unclear, needs explicit boundaries

**"It kept asking questions"**
→ Command needs opinionated defaults

**"It used the wrong approach"**
→ Missing skill or command guides wrong method

**"I had to explain the same thing again"**
→ Create reusable command or skill

## Success Criteria

After alignment:
- [ ] User's original intent is captured in configuration
- [ ] Future similar requests will work better
- [ ] Changes are minimal and targeted
- [ ] No regressions to other commands

## Meta-Notes

This command exists because configuration is never perfect on first try. Use it:
- After frustrating interactions
- When you notice recurring friction
- When you have ideas for improvement
- Before starting complex new workflows
