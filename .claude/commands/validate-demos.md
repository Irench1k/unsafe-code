---
description: "Validate interactive .http demos for quality, character logic, and engagement"
model: opus
argument-hint: [exercise-id|path]
---

# Validate Demos: $ARGUMENTS

Consider carefully the student experience. Is the demo engaging? Is character logic sound?

Validate student-facing interactive exploit demonstrations.

## Location Pattern

```
vulnerabilities/python/flask/confusion/webapp/r{NN}_{category}/http/e{XX}/
├── e{XX}_{name}.exploit.http    # Demonstrates the vulnerability
└── e{XX}_{name}.fixed.http      # Shows the fix works
```

## Before Validating

Read Serena memories:

- `spongebob-characters` - Character rules and logic
- `http-demo-standards` - Demo quality standards
- `pedagogical-design-philosophy` - ONE concept rule

## Validation Checklist

### Technical Correctness

- [ ] Exploit actually exploits the vulnerability
- [ ] Fixed version actually blocks the exploit
- [ ] Assertions verify expected behavior
- [ ] No hardcoded values that break on reseed
- [ ] Works with `httpyac {file}.http -a`

### Character Logic

- [ ] Attacker uses THEIR credentials (not victim's)
- [ ] Plankton attacks Mr. Krabs/organization
- [ ] Squidward attacks SpongeBob (petty revenge)
- [ ] SpongeBob is NEVER an attacker
- [ ] Credentials match character roles

### Engagement Quality

- [ ] Business impact immediately clear
- [ ] Not boring or formulaic
- [ ] Fun in underhanded way (via examples, not explanations)
- [ ] Minimal annotations (show, don't tell)
- [ ] No overexplaining what's visible in the code

### Format Standards

- [ ] One assert per test (unlike e2e specs)
- [ ] Variables defined for reusable values
- [ ] Console.info at key moments (sparingly)
- [ ] No complex .http syntax
- [ ] Plain httpyac patterns (no utils.cjs helpers)

## Red Flags

- Using `$(response).field()` - that's e2e spec syntax, not demo syntax
- Using `auth.basic()` - demos use raw Authorization headers
- Multiple paragraphs of explanation
- Same business impact as previous demo
- Technical jargon ("authenticates", "instantiates")

## Running Demos

```bash
# Run single demo
httpyac vulnerabilities/.../http/e01/e01_demo.exploit.http -a

# If balance issues occur
# Reset DB via docker compose or platform.seed() in separate spec
```

## Demo vs E2E Spec Comparison

| Aspect          | Interactive Demo            | E2E Spec              |
| --------------- | --------------------------- | --------------------- |
| Response access | `response.parsedBody.field` | `$(response).field()` |
| Auth            | Raw `Authorization:` header | `{{auth.basic()}}`    |
| Asserts         | 1 per test                  | Multiple OK           |
| Helpers         | None (plain httpyac)        | Full utils.cjs        |
| Purpose         | Student learning            | Automated testing     |
