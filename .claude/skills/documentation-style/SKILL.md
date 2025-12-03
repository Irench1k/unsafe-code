---
name: documentation-style
description: Writing educational documentation for Unsafe Code Lab. Auto-invoke when editing README.md files, writing exercise descriptions, section plans, or converting technical descriptions to student-friendly narrative. Focus on behavioral language, not security jargon.
---

# Documentation Style Guide

## When to Use This Skill

- Editing README.md files in vulnerabilities/
- Writing exercise descriptions
- Creating section plans
- Converting technical explanations to narrative
- Polishing educational content

## When NOT to Use This Skill

- Writing @unsafe annotations (technical is fine there)
- Writing e2e specs (use http-spec-conventions)
- Writing exploit demos (use http-demo-conventions)
- Maintaining the docs generator tool (use infra-maintainer)

## Core Principles

### 1. Show, Don't Tell

Describe WHAT happens, not vulnerability taxonomy:

**Good**: "Plankton reads SpongeBob's order history"
**Bad**: "This demonstrates an IDOR vulnerability"

**Good**: "The cart belongs to SpongeBob but Squidward modifies it"
**Bad**: "Broken access control allows unauthorized modification"

### 2. Avoid Security Jargon

Students should learn concepts through examples, not definitions:

| Avoid | Use Instead |
|-------|-------------|
| IDOR | "accessing someone else's resource" |
| Broken access control | "confusion about who owns what" |
| Authentication bypass | "the system thinks you're someone else" |
| Authorization failure | "allowed to do something you shouldn't be" |
| CWE-863 | (don't mention CWE in student docs) |

Save technical terms for @unsafe annotations where they're appropriate.

### 3. Use Character Names and Scenarios

**Good**: "Squidward, annoyed at SpongeBob's promotion, decides to peek at his pay stub"
**Bad**: "An attacker accesses another user's private data"

### 4. Focus on Business Impact

**Good**: "SpongeBob's personal order history is exposed to a competitor"
**Bad**: "Information disclosure vulnerability"

**Good**: "Plankton can place orders on behalf of Krusty Krab customers"
**Bad**: "Unauthorized action execution"

### 5. Progressive Revelation

Don't frontload everything. Let understanding build:

1. **What**: Describe the scenario
2. **Why**: Explain why this matters
3. **How**: Show the mechanism
4. **Impact**: Reveal the consequence

## Document Types

### Section README.md

Structure:
```markdown
# Section Name (e.g., Authorization Confusion)

Brief overview of the vulnerability category.

## What You'll Learn

- Concept 1
- Concept 2
- Concept 3

## Exercises

| Version | Vulnerability | Fix |
|---------|--------------|-----|
| v301 | [Description] | - |
| v302 | [Description] | Fixes v301 |
| ... | ... | ... |

## The Story

[SaaS evolution narrative - how these features emerged]
```

### Exercise Description

Structure:
```markdown
## Exercise N: [Name]

### The Feature
What is Sandy adding and why?

### The Problem
What confusion does this create?

### The Exploit
How can this be abused? (behavioral, not technical)

### The Impact
What's the business consequence?
```

## Templates

### Vulnerability Block Template

```markdown
### v301: Session Cart Confusion

**Feature**: Sandy adds support for guest checkout by reading cart ID from URL.

**Problem**: The authorization decorator checks if the user owns the cart from their session, but the handler reads the cart ID from the URL parameter. These can be different!

**Exploit**: Squidward logs in, notes his session cart ID. He then changes the URL to include SpongeBob's cart ID. The decorator approves (Squidward's session cart is his), but the handler processes SpongeBob's cart.

**Impact**: Squidward can view and modify any customer's cart.
```

### Impact Statement Template

Vary the impacts - don't always say "data leak":

- **Financial**: "Plankton gets free meals charged to Krusty Krab"
- **Reputational**: "Orders appear to come from Krusty Krab but contain Chum Bucket items"
- **Privacy**: "Customer order history exposed to competitors"
- **Operational**: "Mr. Krabs can't trust his own order reports"
- **Sabotage**: "Squidward cancels SpongeBob's scheduled orders"

## Quality Checklist

Before finalizing documentation:
- [ ] No security jargon in student-facing content?
- [ ] Character names used for scenarios?
- [ ] Business impact clear and varied?
- [ ] Progressive complexity maintained?
- [ ] Links verified (`uv run docs check-links`)?
- [ ] Voice consistent with project style?

## Anti-Patterns

### Too Technical
❌ "This endpoint is vulnerable to CWE-863: Incorrect Authorization"
✅ "The endpoint lets Plankton access Krusty Krab orders"

### Too Abstract
❌ "Improper access control leads to unauthorized data access"
✅ "SpongeBob's paycheck amount is visible to Squidward"

### Too Dry
❌ "The user can access other users' resources"
✅ "Plankton, sitting in his Chum Bucket office, pulls up the Krusty Krab's secret recipe inventory"

### Too Long
❌ [3 paragraphs explaining the technical mechanism]
✅ [1 sentence scenario + code example]

## Link Verification

After any documentation edit:

```bash
uv run docs check-links
```

Must show "✓ No broken links found" before completing.

## See Also

- [spongebob-characters](../spongebob-characters/SKILL.md) - Character reference
- [http-demo-conventions](../http-demo-conventions/SKILL.md) - Demo writing (similar style)
- `tools/docs/STYLE_GUIDE.md` - Extended style guidance
