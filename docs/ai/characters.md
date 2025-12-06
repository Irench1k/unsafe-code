# SpongeBob Character Reference

Single-source character rules for narratives, demos, and specs.

---

## Golden Rule
> Attacker uses **their own credentials**. Exploits demonstrate application confusion, not password theft.
```http
# WRONG
Authorization: Basic {{btoa("spongebob:bikinibottom")}}
GET /messages?user=patrick

# CORRECT
Authorization: Basic {{btoa("plankton:i_love_my_wife")}}
GET /messages?user=patrick  # Confusion happens here
```

---

## Cast Profiles

### SpongeBob SquarePants
- Role: Primary victim, innocent user
- Email: `spongebob@krusty-krab.sea`
- Password: `bikinibottom`
- User ID: 1 (v301+)
- Personality: Enthusiastic, trusting
- **Never** an attacker

### Squidward Tentacles
- Role: Insider threat, disgruntled employee
- Email: `squidward@krusty-krab.sea`
- Password: `clarinet123`
- User ID: 2 (v301+)
- Attacks: SpongeBob (spite), Mr. Krabs (grievance)

### Plankton
- Role: External attacker, business rival
- Email: `plankton@chum-bucket.sea`
- Password: `i_love_my_wife`
- User ID: 3 (v301+)
- Attacks: Mr. Krabs (rivalry), Patrick (easy target)

### Patrick Star
- Role: VIP victim
- Email: `patrick@rock.sea`
- Password: `rock123`
- User ID: 4 (v301+)
- Personality: Innocent, wealthy, easy target

### Mr. Krabs
- Role: Business owner, high-value target
- Email: `krabs@krusty-krab.sea`
- Password: `money4ever`
- User ID: 5 (v301+)
- API Key: `key-krusty-krab-z1hu0u8o94`

### Sandy Cheeks
- Role: Technical user, verifier of fixes
- Email: `sandy@treedome.sea`
- Password: `science!`
- User ID: 6 (v301+)

---

## Attack Relationships
```
Squidward -> SpongeBob (spite, jealousy)
Squidward -> Mr. Krabs (workplace grievance)
Plankton  -> Mr. Krabs (business rivalry)
Plankton  -> Patrick (easy target)
```
Invalid: SpongeBob attacking anyone; Plankton attacking SpongeBob; Squidward attacking Plankton.

---

## Section Mapping
| Section | Attacker | Victim | Theme |
|---------|----------|--------|-------|
| r01 | Squidward | SpongeBob | Sneaky coworker |
| r02 | Squidward | SpongeBob | System manipulation |
| r03 | Plankton | Mr. Krabs/Patrick | Cross-tenant |
| r04+ | Vary | Vary | Keep variety |

---

## Restaurant Context
- **Krusty Krab**: Owner Mr. Krabs; employees SpongeBob & Squidward; API key `key-krusty-krab-z1hu0u8o94`.
- **Chum Bucket**: Owner Plankton; rival business; API key `key-chum-bucket-xyz123`.

---

## Narrative Patterns
- Titles are behavioral: `### EXPLOIT: Plankton reads Patrick's order history`.
- Impacts are business-focused (no jargon).
- Examples of good impacts:
  - `IMPACT: Squidward just read SpongeBob's private messages!`
  - `IMPACT: Plankton approved his own refund using Chum Bucket credentials at the Krusty Krab.`
  - `IMPACT: Patrick's credit card was charged for Plankton's order!`

---

## Auth Snippets
**Specs:**
```http
Authorization: {{auth.basic("squidward")}}
Cookie: {{auth.login("plankton")}}
X-API-Key: {{auth.restaurant("krusty_krab")}}
```
**Demos:**
```http
@squidward_auth = Basic squidward@krusty-krab.sea:clarinet123
Authorization: {{squidward_auth}}
```

---

## Red Flags
- SpongeBob shown as attacker
- Victim password used by attacker
- Plankton attacking SpongeBob; Squidward attacking Plankton
- Technical jargon in impact statements
- Multiple concepts or repeated impacts without variety
