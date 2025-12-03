---
name: spongebob-characters
description: Character rules for exploit narratives in Unsafe Code Lab. Auto-invoke when choosing attacker/victim roles, writing demo annotations, mentioning SpongeBob/Squidward/Plankton/Patrick/Mr.Krabs/Sandy, or validating character logic. CRITICAL RULE - Attacker uses THEIR OWN credentials; exploit comes from application confusion, NOT password theft.
---

# SpongeBob Characters Guide

Character profiles and rules for exploit narratives.

## The Golden Rule

> **Attacker uses THEIR OWN credentials.**
> The exploit comes from **application confusion**, NOT password theft.

```http
# WRONG - This is password theft, not a vulnerability demo!
Authorization: Basic {{btoa("spongebob:bikinibottom")}}
GET /messages?user=spongebob

# CORRECT - Attacker's credentials, victim's data
Authorization: Basic {{btoa("squidward:clarinet123")}}
GET /messages?user=spongebob  # ← Confusion happens HERE
```

## Character Cast

### SpongeBob SquarePants
- **Role**: Primary victim, innocent user
- **Email**: `spongebob@krusty-krab.sea`
- **Password**: `bikinibottom`
- **User ID**: 1 (in v301+)
- **Personality**: Enthusiastic, trusting, does everything by the book
- **Never**: Attacker (he's too innocent!)

### Squidward Tentacles
- **Role**: Insider threat, disgruntled employee
- **Email**: `squidward@krusty-krab.sea`
- **Password**: `clarinet123`
- **User ID**: 2 (in v301+)
- **Personality**: Grumpy, opportunistic, knows the system
- **Attacks**: SpongeBob (out of spite), occasionally Mr. Krabs
- **Use for**: r01, r02 sections (input confusion, state confusion)

### Plankton
- **Role**: External attacker, business rival
- **Email**: `plankton@chum-bucket.sea`
- **Password**: `i_love_my_wife`
- **User ID**: 3 (in v301+)
- **Personality**: Scheming, clever, legitimate business owner
- **Attacks**: Mr. Krabs (business rivalry), Patrick (easy target)
- **Use for**: r03+ sections (authorization confusion, cross-tenant)

### Patrick Star
- **Role**: High-value victim, VIP customer
- **Email**: `patrick@rock.sea`
- **Password**: `rock123`
- **User ID**: 4 (in v301+)
- **Personality**: Innocent, wealthy, easy target
- **Impact**: High when compromised (VIP status)

### Mr. Krabs
- **Role**: Business owner, high-value target
- **Email**: `krabs@krusty-krab.sea`
- **Password**: `money4ever`
- **User ID**: 5 (in v301+)
- **API Key**: `key-krusty-krab-z1hu0u8o94`
- **Personality**: Business-focused, money-obsessed
- **Target for**: Plankton's schemes, financial exploits

### Sandy Cheeks
- **Role**: Technical user, researcher
- **Email**: `sandy@treedome.sea`
- **Password**: `science!`
- **User ID**: 6 (in v301+)
- **Use when**: Need a technically-savvy character

## Attack Relationships

```
Squidward ───attacks───► SpongeBob (spite, jealousy)
    │
    └───attacks───► Mr. Krabs (workplace grievance)

Plankton ───attacks───► Mr. Krabs (business rivalry)
    │
    └───attacks───► Patrick (easy target, high value)
```

## Section Mapping

| Section | Primary Attacker | Primary Victim | Theme |
|---------|-----------------|----------------|-------|
| r01 (Input Confusion) | Squidward | SpongeBob | Sneaky coworker |
| r02 (State Confusion) | Squidward | SpongeBob | System manipulation |
| r03 (Auth Confusion) | Plankton | Mr. Krabs/Patrick | Cross-tenant attack |
| r04+ | Vary | Vary | Keep it fresh |

## Restaurant Context

### Krusty Krab
- Owner: Mr. Krabs
- Employees: SpongeBob, Squidward
- API Key: `key-krusty-krab-z1hu0u8o94`

### Chum Bucket
- Owner: Plankton
- Legitimate but rival business
- API Key: `key-chum-bucket-xyz123`

## Narrative Patterns

### Good Titles (Behavioral)
```http
### SpongeBob checks his messages
### Squidward logs in to the employee portal
### EXPLOIT: Plankton reads Patrick's order history
### Mr. Krabs reviews the day's sales
```

### Bad Titles (Technical)
```http
### GET request to /messages endpoint
### Authentication with Basic Auth header
### Test IDOR vulnerability
### API authorization bypass test
```

## Impact Statement Examples

### Good (Business-Focused)
```http
# IMPACT: Squidward just read SpongeBob's private messages!

# IMPACT: Plankton approved his own refund using Chum Bucket credentials
# at the Krusty Krab - cross-tenant privilege escalation!

# IMPACT: Patrick's credit card was charged for Plankton's order!
```

### Bad (Technical Jargon)
```http
# VULNERABILITY: IDOR via parameter manipulation (CWE-639)

# The authorization check uses OR logic instead of AND logic
# creating a privilege escalation vector

# Horizontal privilege escalation demonstrated
```

## Red Flags (Stop & Fix)

❌ **SpongeBob as attacker** - He's the innocent victim!
❌ **Using victim's password** - That's password theft, not confusion
❌ **Plankton attacking SpongeBob** - Wrong relationship (use Squidward)
❌ **Squidward attacking Plankton** - No workplace relationship
❌ **Technical impact statements** - Keep it narrative

## Auth Header Patterns

### E2E Specs (uctest)
```http
Authorization: {{auth.basic("squidward")}}
Cookie: {{auth.login("plankton")}}
X-API-Key: {{auth.restaurant("krusty_krab")}}
```

### Interactive Demos (httpyac)
```http
Authorization: Basic {{btoa("squidward@krusty-krab.sea:clarinet123")}}
```

## Variety Checklist (By Example 4-5)

To avoid staleness, rotate these elements:

| Aspect | Early Examples | Later Examples |
|--------|----------------|----------------|
| Attacker | Squidward | Plankton, Sandy |
| Victim | SpongeBob | Mr. Krabs, Patrick |
| Impact | Read data | Modify, delete, transfer |
| Target | Messages | Orders, credits, menu |

## Quick Reference

| Character | Email | Password | Typical Role |
|-----------|-------|----------|--------------|
| SpongeBob | spongebob@krusty-krab.sea | bikinibottom | Victim |
| Squidward | squidward@krusty-krab.sea | clarinet123 | Insider attacker |
| Plankton | plankton@chum-bucket.sea | i_love_my_wife | External attacker |
| Patrick | patrick@rock.sea | rock123 | VIP victim |
| Mr. Krabs | krabs@krusty-krab.sea | money4ever | High-value target |
| Sandy | sandy@treedome.sea | science! | Technical user |

## See Also

- [Character Profiles Quick Ref](../../references/character-profiles.md) - Condensed reference card
- [http-demo-conventions](../http-demo-conventions/SKILL.md) - Using characters in demos
