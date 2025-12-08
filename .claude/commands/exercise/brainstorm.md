---
description: "Brainstorm new vulnerability exercise with curriculum analysis"
model: opus
argument-hint: [vulnerability-idea]
---

# Brainstorm Exercise: $ARGUMENTS

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

### 3. I AM A DUMB ROUTER

**My ONLY job is to delegate to project agents.** I do NOT:

- ❌ Read source code files directly
- ❌ Read skill or reference files
- ❌ Design vulnerabilities myself

### 4. ALLOWED AGENTS (ONLY THESE)

| Task | Agent |
|------|-------|
| Gap analysis & design | `content-planner` |
| Implement code | `code-author` |
| Write demos | `demo-author` |
| Write specs | `spec-author` |

**Design work = Spawn content-planner, report its design to user.**

---

Think deeply and step by step about this vulnerability design. Consider natural evolution patterns and pedagogical principles.

Design a new vulnerability demonstration following pedagogical principles.

## Design Framework

### Step 1: Identify Gap

Check existing coverage:

- What vulnerability types exist?
- What's missing from natural SaaS evolution?
- What complexity level is needed?

Use `content-planner` for gap analysis if needed.

### Step 2: Define ONE Concept

**Golden Rule:** ONE new concept per example. Not zero, not two. ONE.

Ask:

- What's the single security insight?
- How does it emerge from realistic code?
- What natural pattern causes it?

### Step 3: Choose Natural Evolution Pattern

How does this vulnerability appear in real code?

| Pattern              | Description                                   | Example                                           |
| -------------------- | --------------------------------------------- | ------------------------------------------------- |
| Refactoring drift    | Decorator reads different source than handler | Session vs URL cart_id                            |
| Feature addition     | New feature introduces side effect            | "Support delegated posting" enables impersonation |
| Helper consolidation | DRY creates unexpected precedence             | `bind_to_restaurant()` checks multiple sources    |
| Consistency attempt  | Trying to unify creates confusion             | Multiple auth methods with different scopes       |

### Step 4: Design Attack Chain

Structure:

1. **Setup** - Normal operation (establishes context)
2. **Attack** - Exploitation step (shows the confusion)
3. **Verification** - Prove impact (crystal clear business harm)
4. **Impact Statement** - Why this matters

### Step 5: Consider Characters

Who attacks whom?

- **Plankton → Mr. Krabs**: External attacker, wants formula/sabotage
- **Squidward → SpongeBob**: Insider, petty revenge
- **Never**: SpongeBob as attacker

What credentials do they have?

- Attacker uses THEIR OWN credentials
- Exploitation comes from confusion, not stolen passwords

### Step 6: Validate Against Principles

- [ ] ONE new concept only?
- [ ] Natural evolution pattern?
- [ ] Production-quality code?
- [ ] Character logic sound?
- [ ] Business impact clear?
- [ ] Progressive complexity (builds on previous)?

## Output Format

Provide design document:

```markdown
## Vulnerability: [Name]

### Root Cause

[Single sentence]

### Natural Evolution

[How this code emerged realistically]

### Attack Chain

1. Setup: ...
2. Attack: ...
3. Verify: ...

### Characters

- Attacker: ... (using their own credentials)
- Victim: ...

### Impact

[Business harm in plain terms]

### Files to Create

- Source: e{XX}\_{name}/
- Demo: http/e{XX}/
```

## Delegation

After design is approved:

1. `code-author` - Implement vulnerable code
2. `demo-author` - Create .http demos
3. `spec-author` - Add e2e specs
