# SpongeBob Character Profiles

Quick reference for character usage in Unsafe Code Lab.

## Primary Cast

### SpongeBob SquarePants
- **Role**: Innocent user, victim
- **Credentials**: `spongebob` / `bikinibottom`
- **Email**: `spongebob@krusty-krab.sea`
- **NEVER**: Make him an attacker
- **Usage**: Baseline behavior, normal operation

### Squidward Tentacles
- **Role**: Insider threat
- **Credentials**: `squidward` / `clarinet123`
- **Email**: `squidward@krusty-krab.sea`
- **Motivation**: Jealousy, petty revenge
- **Target**: SpongeBob (personal grudge)
- **Best for**: r01, r02 (insider scenarios)

### Sheldon J. Plankton
- **Role**: External attacker
- **Credentials**: `plankton` / `i_love_my_wife`
- **Email**: `plankton@chum-bucket.sea`
- **Motivation**: Business espionage
- **Target**: Mr. Krabs, Krusty Krab
- **Best for**: r03 (cross-tenant attacks)

### Eugene H. Krabs
- **Role**: Admin, high-value target
- **Email**: `krabs@krusty-krab.sea`
- **Protects**: Secret formula, business

### Patrick Star
- **Role**: VIP customer
- **Credentials**: `patrick` / `pineapple`
- **Email**: `patrick@bikini-bottom.sea`
- **Usage**: Regular customer flows

## Attack Relationships

```
Squidward ──[insider grudge]──► SpongeBob
Plankton ──[business rival]──► Mr. Krabs
```

## Credential Rule

**Attacker uses THEIR OWN credentials.**

Exploit comes from confusion, NOT stolen passwords.

```http
# WRONG - using victim's password
Authorization: Basic {{btoa("spongebob:bikinibottom")}}

# CORRECT - attacker's own credentials
Authorization: Basic {{btoa("squidward:clarinet123")}}
GET /messages?user=spongebob  # confusion happens here
```

## Section Mapping

| Section | Attacker | Victim |
|---------|----------|--------|
| r01 | Squidward | SpongeBob |
| r02 | Squidward | SpongeBob |
| r03 | Plankton | Mr. Krabs |

## Variety by Example 4-5

Avoid staleness:
- Change attacker (Squidward → Plankton)
- Change victim (SpongeBob → Mr. Krabs)
- Change impact (read → delete → modify)
- Change function (messages → orders → menu)
