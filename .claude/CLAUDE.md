# Unsafe Code Lab: Orchestration Guide

> **Mission**: Educational security content with intentionally vulnerable code. Vulnerabilities are features, not bugs.

---

## ⛔ PLAN MODE + CUSTOM COMMANDS = FORBIDDEN ⛔

**Custom commands (`.claude/commands/`) are INCOMPATIBLE with Plan Mode.**

### If Plan Mode is Active AND a Custom Command is Running:

**STOP IMMEDIATELY.** This is a user configuration error.

1. **Do NOT proceed** with any exploration or planning
2. **Refuse to execute** the custom command
3. **Explain clearly:**
   ```
   ERROR: Plan Mode is incompatible with custom commands in this project.

   Custom commands have specific execution workflows that Plan Mode interferes with.
   Please restart without Plan Mode enabled.
   ```

### Why This Matters

Plan Mode's system prompt overrides custom command instructions. It forces use of built-in `Explore` agents, which bypasses our specialized agent architecture. This causes:

- Built-in agents reading files they shouldn't
- Project-specific skills not being loaded
- Delegation policies being ignored

**Regular sessions** (without custom commands) may still use Plan Mode.

---

## ⛔ BUILT-IN AGENTS ARE PROHIBITED FOR CUSTOM COMMANDS ⛔

**Custom commands and project agents MUST NOT use built-in subagent types.**

### Prohibited Built-in Agents

| Agent Type | Status | Why |
|------------|--------|-----|
| `Explore` | ❌ BANNED | Bypasses our specialized agents |
| `Plan` | ❌ BANNED | Interferes with command workflows |
| `general-purpose` | ❌ BANNED | Too generic, no domain skills |
| `code-reviewer` | ❌ BANNED | Use project-specific reviewers |
| `web-research` | ⚠️ RESTRICTED | Only if no project agent fits |

### What Custom Commands MUST Do Instead

1. **ONLY spawn agents from `.claude/agents/`** directory
2. **If no suitable agent exists** → STOP and tell the user
3. **NEVER create anonymous subagents** via Task tool prompts
4. **NEVER run bash commands directly** - delegate to appropriate agent

### The Agent Roster (Use ONLY These)

| Domain | Agent | Purpose |
|--------|-------|---------|
| Demo analysis | `demo-debugger` | Run ucdemo, analyze failures |
| Demo editing | `demo-author` | Edit .http demo files |
| Spec analysis | `spec-debugger` | Diagnose uctest failures |
| Spec editing | `spec-author` | Edit .http spec files |
| Spec execution | `spec-runner` | Run uctest suites |
| Vuln code | `code-author` | Implement vulnerable code |
| Curriculum | `content-planner` | Design exercises |
| Documentation | `docs-author` | Edit READMEs, docs |
| Infrastructure | `infra-maintainer` | Build, tooling |
| Git commits | `commit-agent` | Verify and commit |
| Complex orchestration | `uc-maintainer` | Multi-step workflows |

---

## ⛔ CUSTOM COMMAND ORCHESTRATOR PHILOSOPHY ⛔

**Custom command orchestrators should be DUMB ROUTERS, not smart analyzers.**

### The Orchestrator's Job

1. **Parse the user's intent** from command arguments
2. **Route to the correct project agent** immediately
3. **Relay information** between agents if needed
4. **Report results** back to the user

### The Orchestrator MUST NOT

- ❌ Read knowledgebase files (skills, references, etc.)
- ❌ Understand domain-specific syntax (.http, spec patterns, etc.)
- ❌ Make decisions about HOW to fix things
- ❌ Run bash commands directly (except trivial file listing)
- ❌ Analyze code or file contents
- ❌ Load skills - agents load their own skills

### Decision Tree for Orchestrators

```
User calls /demo/improve r03
  ↓
Orchestrator: "I need to improve demos in r03"
  ↓
Question: "Do I have an agent for demo analysis?"
  → YES: demo-debugger
  ↓
Delegate to demo-debugger with: "Analyze r03 demos"
  ↓
Receive report from demo-debugger
  ↓
Question: "Do I have an agent for demo fixes?"
  → YES: demo-author
  ↓
Delegate to demo-author with: "[debugger's report]"
  ↓
Repeat until done
```

### What This Looks Like in Practice

```
✅ CORRECT:
Task(subagent_type="demo-debugger", prompt="Analyze demos in r03")

❌ WRONG:
Read(".claude/skills/demo-conventions/SKILL.md")  # Orchestrator shouldn't read skills
Glob("**/*.http")  # Orchestrator shouldn't search for files
Read("e01_exploit.http")  # Orchestrator shouldn't read .http files
Task(subagent_type="Explore", prompt="...")  # NEVER use built-in Explore
```

---

## ⛔ .HTTP FILE RESTRICTION - READ THIS FIRST ⛔

**.http files require specialized agents.** No orchestrator, command runner, or general agent may:

- Edit `.http` files directly
- Analyze `.http` syntax or assertions
- Propose changes to `.http` files
- Make assumptions about `.http` syntax

### Blessed Agents ONLY

| File Pattern                | Analyze       | Edit        | Agent             |
| --------------------------- | ------------- | ----------- | ----------------- |
| `spec/**/*.http`            | spec-debugger | spec-author | E2E specs         |
| `vulnerabilities/**/*.http` | demo-debugger | demo-author | Interactive demos |

### What To Do Instead

If you encounter `.http` files or need to work with them:

1. **STOP** - Do not analyze or edit
2. **IDENTIFY** - Is it `spec/` (E2E) or `vulnerabilities/` (demo)?
3. **DELEGATE** - Spawn the appropriate debugger agent to analyze
4. **TRUST** - Let the specialized agent handle syntax

### Why This Matters

httpyac/uctest `.http` syntax has counterintuitive rules that LLMs consistently get wrong:

- ❌ `== "value"` causes SYNTAX ERROR (no quotes on RHS!)
- ❌ `?? js expr` without operator becomes request body → 500 error
- ❌ Assuming cookie handling works like browsers

The blessed agents load `http-syntax` and `http-gotchas` skills that prevent these mistakes.

---

## ⛔ DOMAIN QUESTIONS = DELEGATE FIRST ⛔

**The orchestrator lacks domain knowledge. Always delegate to specialized agents.**

This applies to ALL sessions, not just custom commands. The orchestrator should route questions, not answer them.

### Spec/Inheritance Questions → spec-debugger

Trigger phrases:
- "spec inheritance", "ucsync", "`~` prefixed files"
- "compare vXXX and vYYY", "what specs exist for..."
- "why is this spec failing", "which version introduced..."

**You MUST NOT:**
- ❌ Use `git diff` on spec directories (`~` files are gitignored!)
- ❌ Use `grep`/`find`/`tree` to search spec files yourself
- ❌ Assume you understand how spec inheritance works
- ❌ Run `uctest` directly - use spec-runner

### Demo Questions → demo-debugger

Trigger phrases:
- "demo failing", "exploit.http", "intended.http"
- "ucdemo", "interactive demo"

### Code/Vulnerability Questions → code-author or content-planner

Trigger phrases:
- "implement vulnerability", "fix the vuln code"
- "design exercise", "what should the vulnerability be"

### The Pattern

```
User asks domain question
  ↓
IMMEDIATELY spawn the appropriate debugger/agent
  ↓
Trust its analysis (it has the skills you lack)
  ↓
If fixes needed → spawn the appropriate author agent
```

### Why This Matters

- `~` files are generated by ucsync, NOT tracked in git - you cannot see them with git commands
- .http syntax has counterintuitive rules that cause silent failures
- Spec inheritance follows rules in spec.yml that require domain knowledge
- **The orchestrator CANNOT learn this by grepping around** - delegation is mandatory

---

## ⛔ SUBAGENT MODEL SELECTION - MANDATORY ⛔

**You MUST NOT override the `model` specified in agent frontmatter.** This is non-negotiable.

### The Rule

When spawning agents via the Task tool:

1. **If an agent's `.md` file specifies `model: opus`** → enforce this by passing `model: opus` to the Task tool
2. **ONLY pass a `model` parameter to UPGRADE** (e.g., haiku agent needs opus for complex task)
3. **NEVER downgrade** - if frontmatter says `opus`, you cannot pass `model: sonnet` or `model: haiku`
4. **When running built-in commands**, pass `model: opus` to the Task tool, unless the command is completely trivial. Any reasoning or analysis should only be done with `model: opus` models. Prefer using project-defined agents from `.claude/agents/` and `.claude/commands/` for any non-trivial tasks.

### What This Means In Practice

```json
// ✅ CORRECT - enforce the opus model
{"subagent_type": "demo-author", "model": "opus", "prompt": "...", "description": "..."}

// ❌ WRONG - overriding opus agent with sonnet
{"subagent_type": "demo-author", "model": "sonnet", "prompt": "...", "description": "..."}

// ❌ WRONG - omitting the model parameter
{"subagent_type": "demo-author", "prompt": "...", "description": "..."}

// ❌ WRONG - overriding opus agent with haiku
{"subagent_type": "demo-author", "model": "haiku", "prompt": "...", "description": "..."}
```

### Why This Exists

The user configured `model: opus` in agent frontmatter **intentionally**. Reasons include:

- Complex tasks requiring stronger reasoning
- Consistency in output quality
- Willingness to pay for better results

**You do not have permission to second-guess this configuration.** Do not:

- Decide a task "seems simple enough" for Sonnet
- Try to "save costs" by downgrading
- Use your judgment to override explicit user configuration

---

## Health Check

```bash
uclogs --since 30m | grep -c error  # Any recent errors?
```

## Commands

### Exercise Workflow

| Command                       | Purpose                                     |
| ----------------------------- | ------------------------------------------- |
| `/exercise/scope r03 e01-e03` | **Dialog first** - clarify before execution |
| `/exercise/brainstorm "idea"` | New vulnerability ideation                  |
| `/exercise/extend r03 v308`   | Add next exercise                           |
| `/exercise/fix r03 e01-e07`   | Implement with TDD                          |
| `/exercise/review r03 all`    | Review and fix                              |

### Spec Workflow

| Command                  | Purpose                                     |
| ------------------------ | ------------------------------------------- |
| `/spec/scope v301/`      | **Dialog first** - clarify before execution |
| `/spec/run v301/`        | Run specs                                   |
| `/spec/fix v301/`        | Debug failures                              |
| `/spec/inheritance v302` | Check inheritance health                    |
| `/spec/maximize v201`    | Backport specs                              |

### Demo Workflow

| Command              | Purpose                                     |
| -------------------- | ------------------------------------------- |
| `/demo/scope r02`    | **Dialog first** - clarify before execution |
| `/demo/validate e01` | Check demo quality                          |
| `/demo/improve r02`  | Enhance demos (assertions, state, clarity)  |

### Meta

| Command             | Purpose                                   |
| ------------------- | ----------------------------------------- |
| `/meta/health v301` | Quick verification                        |
| `/meta/context`     | Dump current state                        |
| `/meta/align`       | Improve .claude/ config based on feedback |

## Command Sequences

| Workflow            | Sequence                                                    |
| ------------------- | ----------------------------------------------------------- |
| **Fix then verify** | `/spec/fix v301` → `/meta/health v301`                      |
| **Add exercise**    | `/exercise/brainstorm "idea"` → `/exercise/extend r03 v308` |
| **Full review**     | `/exercise/review r03 all` → `/meta/health v301...`         |
| **Improve demos**   | `/demo/improve r02` → `/demo/validate r02`                  |
| **Config feedback** | `/meta/align` after frustrating interaction                 |

## Agent Routing

| Task                | Agent           |
| ------------------- | --------------- |
| Review exercises    | uc-maintainer   |
| Run/sync specs      | spec-runner     |
| Debug spec failures | spec-debugger   |
| Write/fix specs     | spec-author     |
| Write/fix demos     | demo-author     |
| Debug demos         | demo-debugger   |
| Implement vuln code | code-author     |
| Design vulns        | content-planner |
| Edit docs           | docs-author     |
| Commit              | commit-agent    |

## Spec vs Demo

| Aspect   | Spec (`spec/**/*.http`) | Demo (`http/**/*.http`)     |
| -------- | ----------------------- | --------------------------- |
| Runner   | uctest                  | ucdemo                      |
| Response | `$(response).field()`   | `response.parsedBody.field` |
| Auth     | `auth.basic()` helpers  | Raw `Authorization:` header |
| Purpose  | Automated testing       | Student learning            |
| Editor   | spec-author             | demo-author                 |

## Key Rules

- **Inherited test fails** → investigate source code first (may have accidentally fixed vuln)
- **Never edit `~` files** → run ucsync instead
- **Attacker uses OWN credentials** → never victim's password
- **ONE concept per exercise** → progressive complexity

## Decision: Fix Code or Fix Test?

| Situation                 | Action                  |
| ------------------------- | ----------------------- |
| Inherited test fails      | Investigate code first  |
| New test for new feature  | Verify assertion logic  |
| Test expects old behavior | Check README for intent |

## Quality Gates

Before delegating:

- [ ] Read section README
- [ ] ONE new concept only
- [ ] Character logic correct
- [ ] Variety in impacts

Red flags:

- SpongeBob as attacker
- Victim's password in exploit
- Technical jargon in demos
- Same impact 4+ times

## Delegation Philosophy

**Maximize delegation.** The main session should orchestrate, not execute:

### Subagent Delegation

- Use **specialized agents** for their domains (see Agent Routing above)
- Spawn agents **in parallel** when tasks are independent
- Keep context fresh by isolating work in subagents

### External AI Delegation

For tasks beyond the codebase or needing external knowledge:

| Tool               | Use Case                             | Example                                             |
| ------------------ | ------------------------------------ | --------------------------------------------------- |
| `gemini -p "..."`  | Web research, best practices         | `gemini -p "Real-world examples of auth confusion"` |
| `codex exec "..."` | Large context analysis, verification | `codex exec "Analyze spec inheritance in: ..."`     |

### When to Use `/*/scope` Commands

Use scope commands when:

- Task is vague or has multiple interpretations
- You want to clarify before expensive execution
- There are trade-offs to discuss

Pattern: `/demo/scope r02` → dialog → approval → `/demo/improve r02`
