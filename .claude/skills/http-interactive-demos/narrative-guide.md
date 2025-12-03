# Narrative Guide for Interactive Demos

How to write engaging, educational exploit demonstrations.

## Story Arc Structure

Every demo should follow a three-part story:

### 1. Setup (Normal Usage)

Show legitimate use of the feature:

```http
### SpongeBob checks his recent orders
GET {{host}}/orders
Authorization: {{spongebob_auth}}

?? status == 200
```

### 2. Attack (Exploitation)

Show the exploit in action:

```http
### EXPLOIT: Plankton reads SpongeBob's orders using his own credentials
GET {{host}}/orders?user_id=1
Authorization: {{plankton_auth}}

?? status == 200
```

### 3. Impact (The "Aha!" Moment)

Make the business harm crystal clear:

```http
# IMPACT: Plankton now knows SpongeBob's delivery addresses
# and can intercept his Krabby Patty deliveries!
```

## Title Patterns

### Good Titles (Behavioral)

```http
### SpongeBob checks his messages
### Plankton logs in and orders a Krabby Patty
### EXPLOIT: Squidward reads SpongeBob's private notes
### Krusty Krab processes the order
```

### Bad Titles (Technical)

```http
### GET request to /messages endpoint
### POST /auth/login with JSON body
### Vulnerability test: parameter confusion
### API endpoint test
```

## Impact Comments

### Good Impact Statements

```http
# IMPACT: Plankton just charged Patrick's credit card!

# IMPACT: Squidward can now read all of SpongeBob's private messages
# including his secret Krabby Patty recipes!

# IMPACT: Plankton approved his own refund using Chum Bucket credentials
# at Krusty Krab - cross-tenant privilege escalation!
```

### Bad Impact Statements

```http
# VULNERABILITY: Parameter source confusion in authentication layer

# The authorization check uses OR logic instead of AND logic

# This demonstrates IDOR vulnerability (CWE-639)
```

## Character Voice

### SpongeBob (Victim, innocent)
- Enthusiastic, trusting
- Does everything by the book
- Never suspicious

### Squidward (Insider threat)
- Grumpy, opportunistic
- Knows the system
- Targets SpongeBob out of spite

### Plankton (External attacker)
- Scheming, clever
- Has legitimate access (Chum Bucket owner)
- Targets Mr. Krabs for business rivalry

### Patrick (High-value victim)
- Innocent, wealthy VIP customer
- Easy target
- High impact when compromised

## Flow Examples

### Data Theft Demo

```http
# @import ../common/setup.http
@host = {{base_host}}/v301

### SpongeBob logs in to check his messages
POST {{host}}/auth/login
Content-Type: application/json

{
  "email": "spongebob@krusty-krab.sea",
  "password": "bikinibottom"
}

?? status == 200


### SpongeBob reads his private messages
GET {{host}}/messages
Authorization: {{spongebob_auth}}

?? status == 200


### --- ATTACK BEGINS ---

### Squidward logs in with his own credentials
POST {{host}}/auth/login
Content-Type: application/json

{
  "email": "squidward@krusty-krab.sea",
  "password": "clarinet123"
}

?? status == 200


### EXPLOIT: Squidward reads SpongeBob's messages using parameter confusion
GET {{host}}/messages?user=spongebob
Authorization: {{squidward_auth}}

?? status == 200
?? js response.parsedBody.messages.length > 0

# IMPACT: Squidward can read SpongeBob's private messages
# including his secret Krabby Patty formula notes!
```

### Financial Exploit Demo

```http
### Record Patrick's starting balance
# @name initial_balance
GET {{host}}/account/credits
Authorization: {{patrick_auth}}


### --- EXPLOIT ---

### Plankton transfers credits FROM Patrick TO himself
POST {{host}}/credits/transfer
Authorization: {{plankton_auth}}
Content-Type: application/json

{
  "from_user": "patrick",
  "to_user": "plankton",
  "amount": 50
}

?? status == 200


### Patrick's balance is now lower
GET {{host}}/account/credits
Authorization: {{patrick_auth}}

?? js parseFloat(response.parsedBody.balance) < {{parseFloat(initial_balance.balance)}}

# IMPACT: Plankton just stole $50 from Patrick's account!
```

## What to Avoid

### Don't Explain Root Cause

```http
# WRONG - too technical
# The vulnerability occurs because the auth decorator checks
# request.args but the handler reads from request.form, creating
# a parameter source confusion vulnerability.

# RIGHT - just show impact
# IMPACT: Squidward accessed SpongeBob's private data!
```

### Don't Use Technical Terms

```http
# WRONG
### Test IDOR vulnerability via horizontal privilege escalation

# RIGHT
### EXPLOIT: Plankton accesses Patrick's order history
```

### Don't Over-Comment

```http
# WRONG - cluttered
### Login endpoint test
# This tests the login functionality
# Using POST method with JSON body
# Content-Type must be application/json
POST {{host}}/auth/login
Content-Type: application/json
# The body contains email and password fields
{
  "email": "...",
  "password": "..."
}

# RIGHT - clean
### Plankton logs in
POST {{host}}/auth/login
Content-Type: application/json

{
  "email": "plankton@chum-bucket.sea",
  "password": "i_love_my_wife"
}
```

## Variety by Example 4-5

Avoid staleness by rotating:

| Aspect | Early Examples | Later Examples |
|--------|----------------|----------------|
| Attacker | Squidward | Plankton |
| Victim | SpongeBob | Mr. Krabs, Patrick |
| Impact | Read data | Modify, delete, transfer |
| Target | Messages | Orders, credits, menu |

## Quality Checklist

Before finalizing a demo:

- [ ] Story arc clear? (Setup → Attack → Impact)
- [ ] Titles are behavioral, not technical?
- [ ] ONE assert per test?
- [ ] Attacker uses THEIR OWN credentials?
- [ ] Impact statement is business-focused?
- [ ] No technical jargon in comments?
- [ ] Flow is self-contained (no imports except common.http)?
