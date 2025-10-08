# Unsafe Code Lab: Pedagogical Design Philosophy

This memory captures the detailed approach to designing educational vulnerability examples, PoCs, and progression, distilled from the progression.md analysis.

## Core Principle: Minimize Cognitive Friction

Every decision should ask: "Does this help or hinder the student's learning journey?"

### The First-Time Student Perspective

Always imagine a student who:
- Is seeing these examples for the first time
- Doesn't know what's coming next
- Will compare files side-by-side to spot differences
- May have misconceptions we need to counter
- Needs to build intuition, not just memorize patterns

## Progressive Complexity: The Art of Micro-Steps

### Rule 1: Start Absurdly Simple

First examples should be the **simplest possible demonstration** of a concept, even if unrealistic:
- No advanced features
- No variables or abstractions (no `@base` in exploit-1.http)
- Full, explicit URLs and parameters
- Single-file implementations
- Minimal Flask features

**Why**: Students need a solid foundation before complexity. They're also learning your teaching structure itself.

### Rule 2: Introduce ONE New Dimension Per Example

Each example should change exactly one thing:
- Example 1 → 2: Add the vulnerability (same root cause, simplest form)
- Example 2 → 3: Same exploit, but code refactored into functions
- Example 3 → 4: Same vulnerability, but now across files

**Anti-pattern**: Example 2 introduces both the vulnerability AND request.values merging AND new database schema. Too much!

### Rule 3: When Root Cause Stays Same, Everything Else Should Too

If Example 2 and 3 demonstrate the exact same root cause (just with refactored code), the .http files should be **identical**. This makes the point unmissable: "Same vulnerability, different code organization."

**Exception**: When you WANT to highlight that different exploitation is possible, but then make this obvious in comments.

### Rule 4: Delay Abstractions Until Students Are Comfortable

- `@base` variable: Introduce around example 3, not example 1
- When introducing `@base`, end it at least one path segment short: `http://localhost:8000/confusion/source-precedence` not `http://localhost:8000/confusion/source-precedence/example3`
  - **Why**: Seeing `{{base}}/example3?key=value` is more intuitive than `{{base}}?key=value`

## Character-Driven Narrative: Not Just Fun, Essential

### Character Archetypes (Non-Negotiable)

**SpongeBob**: 
- **Role**: Innocent user, victim
- **NOT an attacker**: Never use SpongeBob's credentials in exploit (unless showing he was phished)
- **Voice**: Enthusiastic, simple, trusting
- **Usage**: Establish baseline behavior, show what normal looks like

**Squidward**:
- **Role**: Insider threat, petty antagonist
- **Motivation**: Jealousy, recognition, pranks
- **Target**: Usually SpongeBob (personal grudge)
- **Usage**: Horizontal privilege escalation, insider attacks

**Plankton**:
- **Role**: External attacker, sophisticated
- **Motivation**: Business espionage, formula theft
- **Target**: Usually Mr. Krabs / organization
- **Usage**: External attacks, sophisticated exploits

**Mr. Krabs**:
- **Role**: Admin, high-value target
- **Protects**: Safe combinations, secret formula, business secrets
- **Usage**: Vertical privilege escalation target

### Character Establishment Pattern

First example in a series should establish ALL relevant characters:
1. Show SpongeBob logging in successfully (baseline)
2. Show Squidward logging in successfully (establish he exists)
3. Show Squidward attacking SpongeBob (now we know who's who)

**Why**: If we jump straight to "Plankton authenticates as SpongeBob", students don't know if Plankton has an account, how he got SpongeBob's password, etc. Confusion!

### Narrative Must Make Logical Sense

**Bad** (from exploit-2.http original):
- First request: SpongeBob's password used
- Second request: SpongeBob's password used again, but accessing Squidward's data
- Comment says: "Plankton authenticates as SpongeBob"
- **Problem**: How does Plankton have SpongeBob's password? This isn't what the vulnerability is about!

**Good**:
- First request: Squidward logs in with his own credentials
- Second request: Squidward uses his own password + two different usernames
- **Clear**: Squidward is exploiting parameter confusion, not password theft

## Annotation Writing: Behavioral, Not Technical

### Comment Style Hierarchy

**Per-request annotations** (in .http files):
- Should be **behavioral**: "SpongeBob accesses his own messages"
- NOT technical: "SpongeBob authenticates and retrieves his own messages using consistent parameters"
- NOT root-cause: "Authentication protects messages: wrong password is rejected"

**Why**: Students are reading this alongside code and other context. You're providing the "delta" - what to notice, not a complete explanation.

**Anti-patterns to avoid**:
- Mixing technical jargon with vague statements ("authenticate", "retrieve", "consistent parameters")
- Academic pedantry (sounds smart but says little)
- Two-line annotations when one suffices

### When Annotations Should Be From Attacker's Perspective

During exploitation, annotations should reflect **attacker's thought process**:
- "Why are we sending the same username twice? I wonder what would happen if I changed one of those?" (Example 2)
- "Oh this looks more secure - only one username now. Hm, I wonder if the server would still accept the old trick?" (Example 5)

**Why**: This teaches students how attackers discover vulnerabilities.

### The Optional Business Impact Summary

After some exploit responses, you MAY add a final summary line:
- "IMPACT: Plankton has stolen Squidward's private notes, learning where Mr. Krabs hides the safe key!"

**Rules for impact summaries**:
- ✅ Use when introducing new business impact
- ✅ Use to connect technical exploit to story consequence
- ✅ Keep concise (1-2 lines)
- ❌ Don't repeat what previous annotations already said
- ❌ Don't use in every single example (gets tedious)
- ❌ Prefer to omit unless it adds unique value

## Managing Repetition: The Boredom Problem

### Recognize When Examples Feel Stale

By example 4, if we're showing the same "Squidward accesses SpongeBob's messages" attack for the 4th time, students are bored.

**Solutions**:
1. **Switch characters**: Example 4 shows Plankton attacking (different attacker, same technical exploit)
2. **Change business impact**: Example 6 shows message deletion instead of reading
3. **Introduce new functionality**: Add password reset endpoint that's vulnerable in a related way

### Creative Variety Without Overwhelming

**Good variety techniques**:
- Same root cause, different HTTP method (GET vs DELETE vs POST)
- Same root cause, different victim (SpongeBob → Mr. Krabs)
- Same root cause, different attacker (Squidward → Plankton)
- Same root cause, different business function (read → delete → update)

**Bad variety**:
- Completely different business logic AND different root cause AND new Flask features (too much!)

### The Surprise Twist Pattern

Example 6 proposed: Plankton deletes Mr. Krabs' messages
- Setup: Mr. Krabs reads his messages (normal)
- Attack: Plankton deletes them using parameter confusion
- Verification: Mr. Krabs tries to read again - messages gone!
- **Impact**: Shows destructive capability, not just read access

**Why this works**: Unexpected yet logical progression from previous examples.

## Code Organization: When to Split Files/Directories

### File Structure Progression

Examples 1-3: Single file (`routes.py`)
- **Why**: Keep it simple, students see everything at once

Example 4: Separate into subdirectories
- Structure: `e0103_intro/` and `e04_cross_module/`
- **Why**: Now we're demonstrating cross-module confusion, so we NEED multiple files to make the point

### Naming Convention for Grouped Examples

When examples naturally cluster:
- `e0103_intro/` - Contains examples 1-3 (all in one file)
- `e04_cross_module/` - Contains example 4 (split across files)

**Why**: The directory name tells students what's in it and what it demonstrates.

### Adding Characters to Database

If you introduce Plankton as an attacker, he needs an account in the database:
```python
db = {
    "passwords": {
        "spongebob": "bikinibottom",
        "squidward": "clarinet123",
        "plankton": "chumbucket"  # Add when he becomes relevant
    },
    # ...
}
```

**Don't add all characters upfront** - only add them when they're used, to avoid confusion about who's in the system.

## Handling Technical Complexity: The Developer Psychology Angle

### Building Developer Empathy

Remember that Unsafe Code Lab teaches **non-developers** (pentesters, researchers) how developers think.

**Show realistic development patterns**:
- Example 7: Developers use form body for credentials (best practice!)
- Example 8: Developers "fix" example 7 by using request.values in auth, but introduce NEW vulnerability elsewhere

**The narrative**: "We fixed the vulnerability!" → "Oh no, the fix created a new one in the password reset endpoint!"

**Why**: This teaches that vulnerabilities emerge from well-intentioned changes, not just mistakes.

### The "Apparent Fix" Technique

Example 8 proposed pattern:
1. Example 7: `/messages` endpoint is vulnerable
2. Example 8: `/messages` endpoint is now fixed (uses request.values consistently)
3. Example 8: NEW `/password_reset` endpoint is vulnerable (uses the old auth function)

**Why hilarious and educational**: Shows how partial fixes create false security. The "fixed" auth is still used by new code!

## The Meta-Patterns You Should Internalize

### 1. Delta Highlighting

When two examples differ slightly, **minimize all other differences** so the delta is obvious:
- Same characters
- Same URL patterns (if possible)
- Same comment structure
- Only change what you're trying to teach

### 2. Foreshadowing and Callbacks

Example 2 comment: "Why are we sending username twice? I wonder..."
Example 5 comment: "Remember when we sent username twice? This looks different..."

**Why**: Creates continuity, helps students build mental model.

### 3. Student Self-Discovery

Don't explain everything upfront. Let students:
- Compare files side-by-side
- Notice patterns
- Draw conclusions
- Have "aha!" moments

Your annotations guide but don't spoonfeed.

### 4. Real-World Connection Without Preaching

Show realistic patterns (form body for credentials is best practice), but don't say:
"This is secure! You should always do this!"

Instead: Students see it working correctly, then see it can still be vulnerable if mixed incorrectly with other approaches.

### 5. Respect Student Intelligence

**Don't**:
- Over-explain simple concepts
- Use condescending language
- Make vulnerabilities too obvious
- Add training wheels they don't need

**Do**:
- Trust them to compare examples
- Trust them to understand attack flow
- Give them challenges appropriate to their level
- Let them figure some things out

## Quality Checklist for Any New Example

Before finalizing:

- [ ] Is this the simplest possible demonstration of this concept at this stage?
- [ ] Does this change exactly ONE thing from the previous example (or is there good reason to change more)?
- [ ] Do the characters make sense (right attacker for right target)?
- [ ] Do the character credentials match their role (attacker uses their own password, not victim's)?
- [ ] Are annotations behavioral rather than technical jargon?
- [ ] Is the business impact different enough from recent examples?
- [ ] Will students be able to spot the difference by comparing files?
- [ ] Have I avoided introducing new syntax/features until students are comfortable?
- [ ] Does the narrative flow logically from previous examples?
- [ ] Am I respecting student intelligence (not over-explaining)?

## Anti-Patterns to Actively Avoid

1. **Premature Abstraction**: Don't use `@base` in first examples
2. **Character Confusion**: Don't make SpongeBob an attacker
3. **Credential Confusion**: Don't use victim's password in exploit unless that's the vulnerability
4. **Verbose Annotations**: Don't write two lines when one is enough
5. **Technical Pedantry**: Don't use jargon when plain language works
6. **Repetitive Impact**: Don't show same harm 5 times in a row
7. **Surprise Complexity**: Don't combine multiple new concepts
8. **Over-Explanation**: Don't write impact summaries that repeat obvious things
9. **Inconsistent Delta**: When showing "same vulnerability, different code", keep examples identical

## The Ultimate Test

Ask yourself:
- "If I were seeing this for the first time, would this help or confuse me?"
- "What misconception might a student develop from this, and how do I counter it?"
- "Is the difference between this and the previous example crystal clear?"
- "Does the narrative make sense, or am I using characters illogically?"
- "Am I building intuition or just showing variations?"
