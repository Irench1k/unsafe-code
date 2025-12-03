# Common Gotchas

Top 10 mistakes to avoid in Unsafe Code Lab development.

## 1. Wrong Character as Attacker

**Bad**: SpongeBob attacks anyone
**Good**: Squidward attacks SpongeBob, Plankton attacks Krabs

## 2. Using Victim's Password

**Bad**: Attacker knows victim's password (that's password theft, not the vulnerability)
**Good**: Attacker uses their own credentials, exploits confusion

```http
# BAD
Authorization: Basic {{btoa("spongebob:bikinibottom")}}

# GOOD
Authorization: Basic {{btoa("squidward:clarinet123")}}
GET /messages?user=spongebob
```

## 3. Quotes on Assertion RHS

**Bad**: `?? js $(response).field("status") == "delivered"`
**Good**: `?? js $(response).field("status") == delivered`

The right side is a literal, not JavaScript.

## 4. Assertions Testing Pre-State

Assertions run AFTER the request:

```http
# BAD - both check post-request
?? js balance == 100  # "before"
?? js balance == 110  # "after"

# GOOD - capture pre-state
{{ exports.before = await user("p").balance(); }}
POST /refund
?? js await user("p").balance() == {{before + 10}}
```

## 5. @base in Early Examples

**Bad**: Using `@base` in examples 1-2
**Good**: Full explicit URLs in examples 1-2, `@base` starting example 3

Students need to see full URLs first.

## 6. Multiple New Concepts

**Bad**: Example introduces new auth method + new endpoint + new attack
**Good**: ONE new concept per example

## 7. Same Impact Repeated

**Bad**: "Reads SpongeBob's messages" 4 times in a row
**Good**: Vary impact (read → delete → modify), vary victim, vary attacker

## 8. Technical Jargon in Annotations

**Bad**: "User authenticates and retrieves messages using consistent parameters"
**Good**: "SpongeBob checks his messages"

## 9. Editing ~ Prefixed Files

**Bad**: Editing `~happy.http` directly
**Good**: Edit in base version, run `ucsync` to regenerate

Files with `~` prefix are auto-generated.

## 10. Assuming Test is Broken

When inherited test fails:
- **Bad**: Immediately fix/exclude the test
- **Good**: Check source code first - refactoring may have accidentally fixed vuln

## Quick Checklist

Before finalizing any work:
- [ ] Character logic makes sense?
- [ ] Attacker uses own credentials?
- [ ] ONE new concept?
- [ ] No @ base in early examples?
- [ ] Variety in impacts?
- [ ] Behavioral annotations?
- [ ] No ~ file edits?
