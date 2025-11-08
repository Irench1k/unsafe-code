# Confusion Curriculum Blueprint for Contributors

This document is the master plan for the "Confusion / Inconsistent Interpretation" tutorial (runbooks r01-r05). This tutorial serves as the primary starting point for the Unsafe Code Lab.

## 1. Your Goal as a Contributor

Your mission is to **translate this narrative and these vulnerability patterns** into your target framework (e.g., Nest.js, Django, FastAPI, Express).

This plan exists to ensure a **consistent learning experience** across all languages. Students should be able to complete the Flask r01 tutorial and then the Nest.js r01 tutorial and feel a strong sense of familiarity. The endpoints, characters, and core vulnerability _patterns_ should be as identical as possible.

## 2. Our Guiding Philosophy

This is _not_ a "secure development" class. Our goal is to teach white-box code review and vulnerability discovery.

- **Embrace Realistic Code:** We are not building puzzles or CTFs. The code must feel _real_. This means it can be imperfect, missing DRY principles, or inconsistent, just like a real-world app that has evolved over time. The vulnerability should be a _plausible_ mistake a real developer would make under pressure.
- **No "Magic" Vulns:** The vulnerability should not rely on obscure, long-patched library bugs. It should stem from the _misuse of the framework's own APIs_.
- **Focus on the Pattern:** Our taxonomy is based on _code-level review patterns_. The lesson for a student isn't "this is how you hack a coupon." The lesson is "I must always trace where data comes from, and I must be suspicious if a security check and a business logic function read that data from different sources."
- **Follow the Narrative:** The story of Sandy, Mr. Krabs, and Plankton is our teaching tool. The app's evolution (MVP -> middleware -> sessions) provides the context for _why_ code is being added or refactored. Use this story to frame your examples.

## 3. Technical & Narrative Setup

- **Narrative:** "Cheeky SaaS" is an online ordering platform for restaurants.
  - 🐿️ **Sandy Cheeks:** The developer.
  - 🦀 **Mr. Krabs:** The first customer (Krusty Krab).
  - 🧪 **Plankton:** The attacker (Chum Bucket).
  - (Others: SpongeBob 🧽, Squidward 🦑, Patrick ⭐)
- **Technical Base:**
  - The API runs on `api.cheeky.sea`.
  - A (hypothetical) UI runs on `app.cheeky.sea`.
  - All endpoints for r01-r05 should ideally be bundled into a **single project/service** (e.g., one container).
  - Structure endpoints by version (v101-v199 for r01, v201-v299 for r02 and so on).
  - This mirrors real API evolution and keeps deployment simple (one container). If your framework makes this impractical, document your alternative approach and rationale.

**Important:** Design each endpoint as if the frontend exists. Include proper status codes, JSON responses, error handling, CORS configuration, etc. Don't build toy examples.

## 4. Why Start with Confusion?

Unlike SQL injection or CSRF, confusion vulnerabilities don't depend on framework-specific security features. They arise from fundamental mismatches in how different code paths interpret the "same" input. These patterns appear across all modern frameworks.

These bugs are everywhere because they're subtle: the code "works" in testing but breaks under adversarial input. Developers rarely test both `?item=burger` and `{"item": "burger"}` in the same request.

Finally, finding confusion bugs requires tracing data flow across functions, files, and layers. This is exactly the muscle memory needed for effective code review. Students learn to:

- Map logical inputs to their actual sources
- Compare security check assumptions vs. business logic reality
- Spot normalization mismatches and precedence conflicts

## 5. Code Quality Guidelines

This is **not** a secure development course. We're not teaching defensive coding, input validation best practices, or security-first architecture. That's unrealistic for code review work.

In real engagements, you can't tell clients "rewrite everything with security in mind." You need to find **actual exploitable bugs** in code that's already shipped. That's what we're training.

In particular:

- **DRY violations are fine** – Repeated logic that later diverges is a common source of confusion bugs
- **Missing abstractions are fine** – Not everything needs to be perfectly architected
- **Inconsistent style is fine** – Sandy's refactoring Q3 code in Q4, patterns shift
- **Edge cases ignored is fine** – "That can't happen" assumptions are realistic

But avoid:

- Logic that makes no business sense (why would this endpoint exist?)
- Bugs that break basic functionality (can't create an order at all)
- Framework anti-patterns that would be caught in code review (SQL strings without parameterization when the ORM is right there)

## 6. Structure of the Lab

The five categories build naturally on each other, mirroring how real applications evolve:

1. [**r01: Input Source**](/docs/confusion_curriculum/r01_input_source_confusion.md) -> MVP with basic endpoints, multiple input formats
2. [**r02: Authentication**](/docs/confusion_curriculum/r02_authentication_confusion.md) -> Add middleware, API keys, user context
3. [**r03: Authorization**](/docs/confusion_curriculum/r03_authorization_confusion.md) -> Introduce resources, ownership, access control
4. [**r04: Cardinality**](/docs/confusion_curriculum/r04_cardinality_confusion.md) -> Handle lists, bulk operations, edge cases
5. [**r05: Normalization**](/docs/confusion_curriculum/r05_normalization_issues.md) -> String processing, database lookups, collision bugs

Each stage adds one major framework feature (middleware, sessions, JSON, SQL, validation) while showcasing how those features create new confusion opportunities.

## 7. Understanding Confusion Vulnerabilities (For Students)

Confusion vulnerabilities happen when code that **should be working with one logical value** ends up consulting **different representations or sources** of that value.

Think of it like this: you ask two people "What's the user's ID?" and get different answers because one person checked the URL path while the other read the request body. Both answers might be "correct" from their perspective, but the inconsistency creates a security gap.

### Why This Matters

Security decisions and business logic often live in different parts of your code:

- Middleware checks authentication: "Is this user allowed?"
- Handler performs actions: "Update this user's data"

If they're not reading from the same source, or if they normalize values differently, an attacker can satisfy the security check with one value while exploiting the business logic with another.

### How to Hunt for Confusion Bugs

When reviewing code, pick any important input (user ID, account ID, resource name, order ID) and trace it completely:

1. **Map all sources** – Where can this value enter? Query params? JSON body? Path? Headers? Session?
2. **Find all reads** – Every place the code accesses this value (searches help: grep for the key name)
3. **Compare access methods** – Does the security check looks at both the `request.args` and the `request.json` containers, while the handler only looks at one of them?
4. **Check normalization** – Does one path lowercase the value? Strip whitespace? Decode URLs? Cast types?
5. **Verify execution order** – Do guards run before or after merging/normalization?
6. **Test cardinality** – What happens if the attacker sends an array instead of a single value?

Look for "helpful" abstractions that hide complexity:

- Merged dictionaries that combine query + body + path
- Helper functions with precedence rules
- ORM methods that auto-cast types
- Middleware that modifies request context

The mismatch might be obvious (reading from different sources) or subtle (both use the same source but one normalizes first).

## 8. Ideas to consider in the future

1. JWT specific vulnerabilities
2. Multi-stage email verification
   - The way we implement it right now is within the same handler (it generates token and sends email when no `token` provided, and validates it when available)
   - This avoids the need to have pending-intent tables, reducing cognitive load on the student
   - However, there migth be some nice 'Confusion / Inconsistent Interpretation' vulnerabilities lurking in those multi-request flows
3. Session storage as stateful source of confusion
   - Similarly how many vulnerabilities are based on mixing the input source, there could be vulnerabilities where first request adds something to the session, and second request accesses that value for check / data access, instead of the regular request params
4. Other state management issues between endpoints?
5. Should we split r05 Normalization into:
   - Character Normalization (case, whitespace, unicode, regex)
   - Structural Normalization (truncation, slug generation, ID collisions)
