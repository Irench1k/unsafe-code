# Security Tutorial Style Guide

This guide captures the principles and values that make our security tutorials effective, engaging, and educational. The goal is to teach students to identify realistic vulnerabilities in production-quality code, not just recognize obvious security anti-patterns.

## Core Philosophy

**Students learn best when vulnerabilities hide in code that looks reasonable.** If code screams "THIS IS VULNERABLE!", students learn to spot markers rather than understand root causes. Real-world vulnerabilities emerge from seemingly sensible architectural decisions, incomplete refactorings, and subtle inconsistencies—not from obvious mistakes.

---

## Naming Strategy

### Directory Structure and Prefixes

Use `rXX_` prefixes to indicate progressive complexity and learning order:

**Category level** (main vulnerability types):
```
r01_ii/r01_source_precedence/          # Simplest: parameter source confusion
r01_ii/r02_cross_component_parse/      # Medium: layer-to-layer drift
r01_ii/r03_authz_binding/              # Complex: post-auth resource/identity rebinding
```

**Subcategory level** (variations within a category):
```
r03_authz_binding/
  ├── r01_baseline/                # Secure pattern first
  ├── r02_path_query_confusion/    # Simple confusion variant
  └── r03_simple_rebinding/        # Pure rebinding pattern
```

The numbering reflects:
- **Conceptual complexity**: Start with fundamentals, build to sophisticated patterns
- **Framework knowledge**: Begin with basic Flask, progress to decorators, middleware, etc.
- **Code realism**: Evolve from simple functions to production-grade architecture

### Descriptive Names

Directory names should **answer "What vulnerability pattern does this demonstrate?"**

**Good**:
- `r02_path_query_confusion` — Immediately conveys the issue
- `r03_simple_rebinding` — Clear pattern name
- `r01_baseline` — Indicates secure reference implementation

**Avoid**:
- `r03_whitespace` — What about whitespace?
- `r04_whitespace` — Why are there two?
- `example_3` — Meaningless without context
- `test_case` — Unclear purpose

**Naming patterns that work**:
- Mechanism-based: `decorator_drift`, `middleware_short_circuit`
- Technique-based: `path_query_confusion`, `identity_rebinding`
- Feature-based: `insensitive_object_retrieval`, `multi_value_bypass`

Each name should tell students what they'll learn before they open the directory.

### Example Numbering

**Example IDs are unique per subcategory only**, starting from 1:

```yaml
# r01_ii/r03_authz_binding/readme.yml
outline:
  - title: Secure Authorization Baseline
    examples:
      - 1  # Not 13! Start fresh at 1
  - title: Path-Query Confusion
    examples:
      - 2  # Sequential within this subcategory
      - 3
  - title: Classic Identity Rebinding
    examples:
      - 4
```

This keeps example references simple and local. When discussing "Example 2" within authz_binding, students know exactly which one without cross-referencing a global index.

**File organization**:
- Single-file subcategories: All examples in `routes.py` with IDs 1, 2, 3...
- Multi-directory subcategories: Each directory has examples starting at 1
- Cross-references use directory + number: "See r02_path_query_confusion example 2"

---

## Educational Values

### Realism Over Obviousness

Code that appears well-architected with legitimate business justifications:

```python
def post_message(group):
    """
    Posts a message to a group.

    The from_user field allows attribution flexibility for:
    - Delegated posting (assistants posting on behalf of managers)
    - System notifications sent on behalf of administrators
    """
    from_user = request.json.get("from_user")
    post_message_to_group(from_user, group, message)
```

**Never** point to vulnerabilities in code:

```python
# AVOID: Code with security warnings
def post_message(group):
    # VULNERABILITY: Trusting user-controlled from_user!
    # Should use g.user instead!
    from_user = request.json.get("from_user")
```

### Annotations, Not Comments

**All vulnerability explanations belong in `@unsafe[block]` annotations.**

Annotations explain:
- Root cause clearly
- Attack flow step-by-step
- How this differs from similar patterns
- Realistic impact scenarios

Code should:
- Look production-ready
- Have natural docstrings explaining features
- Include comments explaining business logic only
- Use realistic naming and structure

### Progressive Complexity

Build understanding through careful ordering:

1. **Baseline (secure)**: Show correct pattern first
2. **Simple vulnerability**: Core issue in clearest form
3. **Subtle variations**: Same root cause, different contexts
4. **Complex scenarios**: Sophisticated exploitation

Each example adds one new dimension. Don't combine multiple new concepts.

---

## Impact-Driven Scenarios

### Make Consequences Obvious

Every vulnerability must demonstrate **clear, tangible harm**.

**Good**: "Squidward rigs Employee of the Month voting by impersonating SpongeBob"
- Immediate understanding of impact
- Relatable scenario (voting manipulation)
- Clear victim and attacker

**Avoid**: "Attacker can modify arbitrary user field"
- Abstract impact
- No concrete harm
- Students may not grasp significance

### Use Consistent Fictional Universe

The SpongeBob universe provides:
- **Recognizable characters** with distinct personalities
- **Clear motivations** (Plankton wants formula, Squidward wants recognition)
- **Lighthearted tone** while teaching serious concepts
- **Character voice** as exploit indicator

**Character roles**:
- **Plankton**: External attacker, sophisticated exploits
- **Squidward**: Insider threat, jealousy-motivated attacks
- **Mr. Krabs**: Admin/owner, privilege escalation victim
- **SpongeBob**: Innocent user, impersonation victim

### Real-World Parallels

Map fictional scenarios to actual security concerns:
- Employee of Month voting → Poll manipulation, reputation systems
- Secret formula theft → IP theft, data breaches
- Group message access → Multi-tenant isolation failures
- Staff credentials → Privileged account compromise

---

## Code Quality Standards

### Production-Grade Structure

Organize like real applications:
- Separate concerns (routes, decorators, database)
- Use meaningful abstractions
- Follow framework idioms
- Apply DRY appropriately

**Avoid tutorial-looking code**:
- Function names like `vulnerable_handler()`
- Parameter names like `unsafe_user_input`
- Variable names like `attacker_controlled_field`

### Natural Evolution

Vulnerabilities should emerge from realistic development patterns:

**Refactoring drift**:
```python
# Initially inline (secure)
def handler():
    if not is_member(g.user, request.args.get("group")):
        return 403
    return get_data(request.args.get("group"))

# After refactoring (introduces binding drift)
@check_membership  # reads from query
def handler(group):  # receives from path
    return get_data(group)
```

**Feature addition**: "Support delegated posting for managers" → Adds `from_user` parameter → Enables impersonation

**Consistency attempt gone wrong**: "Use single source of truth" → Sets `g.group` but handlers still use path params → Creates subtle inconsistency

### Minimal Docstrings

Docstrings explain functionality, not security:

```python
def check_group_membership(f):
    """
    Checks if the authenticated user is a member of the requested group.

    Supports flexible group parameter passing via query string or path.
    """
```

---

## Exploit Demonstrations

### Multi-Step Attack Narratives

HTTP exploit files tell a story:

1. **Setup**: Show legitimate use
2. **Attack**: Demonstrate vulnerability
3. **Verification**: Prove exploit worked
4. **Impact**: Explain consequences

### Character Voice as Indicator

Use character-inconsistent language to make exploits obvious:

**SpongeBob would say**: "I'm ready! I vote for SpongeBob because I LOVE working here!"

**Squidward makes "SpongeBob" say**: "I vote for Squidward. He is clearly the most sophisticated employee with refined artistic sensibility."

The mismatch is:
- **Educational**: Shows social engineering indicators
- **Engaging**: Makes attack memorable
- **Realistic**: Parallels real impersonation where tone reveals forgery

### Clear Impact Summaries

End exploits with explicit impact:

```
# IMPACT: Squidward has rigged the vote by impersonating SpongeBob!
# When Mr. Krabs tallies votes, he'll see two for Squidward,
# one appearing to be from SpongeBob himself.
```

---

## Documentation Structure

### Overview First

Each section starts with:
1. Concise summary (1-2 sentences)
2. Core mechanism (what makes this different)
3. Key distinctions (how it differs from similar vulnerabilities)
4. Common patterns (where it appears)
5. Detection guidance (spotting it in review)
6. Real-world scenarios (where it matters)

### Progressive Revelation

Don't frontload everything:
- Overview provides context
- Baseline shows secure pattern
- Each example reveals one dimension
- Students build understanding incrementally

### Avoid Repetition

If annotations explain thoroughly, don't repeat in README, code comments, docstrings, or HTTP comments. Each piece adds unique value.

---

## Anti-Patterns to Avoid

### Don't Insult Student Intelligence

Avoid:
- `# VULNERABILITY HERE` comments
- `@obviously_broken_function` decorators
- `dangerous_user_input` variable names
- Security warnings in docstrings

Students learn to spot markers, not vulnerabilities.

### Don't Create Strawman Code

Avoid:
- Code no experienced developer would write
- Patterns failing code review for non-security reasons
- Obvious logical errors unrelated to security
- Ignoring basic framework best practices

If code looks amateur, students dismiss it as irrelevant.

### Don't Over-Explain

Trust students to:
- Understand basic programming
- Follow attack flows (A→B→C)
- Connect to real-world scenarios
- Learn by analyzing, not reading prose

Be concise but complete.

### Don't Mix Concerns

Each example demonstrates **one vulnerability pattern**. Don't combine SQL injection + authorization bypass, or XSS + authentication bypass.

---

## Testing Educational Effectiveness

**The Realism Test**: Would an experienced developer write this in production?

**The Discovery Test**: Can students find the vulnerability by analyzing code, not reading comments?

**The Impact Test**: Does the example clearly show why this matters?

**The Memory Test**: Will students remember this scenario later?

**The Transfer Test**: Can students apply this to different contexts?

---

## Balancing Act

Balance:
- **Clarity vs. Obviousness**: Understandable without trivial
- **Realism vs. Accessibility**: Production patterns without overwhelming
- **Engagement vs. Seriousness**: Lighthearted while teaching critical concepts
- **Thoroughness vs. Brevity**: Complete without verbose

Prioritize developing **security intuition** over memorizing patterns.

---

## The Ultimate Goal

Students should:
1. Spot subtle vulnerabilities in well-written code
2. Understand root causes beyond symptoms
3. Explain attacks clearly to others
4. Recognize patterns in different codebases
5. Appreciate complexity of secure systems

We develop security mindsets, not teach checklists.
