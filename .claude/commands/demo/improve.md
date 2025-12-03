---
description: "Improve demo quality: assertions, state management, clarity, educational impact"
model: opus
argument-hint: [section|path]
---

# Improve Demos: $ARGUMENTS

Enhance interactive `.http` demos for educational impact and maintainability.

## Philosophy

Great demos make attacks **visceral and obvious**. Students should feel the "aha!" when unauthorized data appears or balances change unexpectedly. Every line advances the attack narrative or helps students understand what just happened.

**Balance**: Introduce quality-of-life improvements without overwhelming students. Use features that clarify, not features for their own sake. Explicit is better than magical.

## Location

```
vulnerabilities/python/flask/confusion/webapp/r{NN}_*/http/e{XX}/
├── e{XX}_{name}.exploit.http   # Demonstrates current vuln
└── e{XX}_{name}.fixed.http     # Shows previous fix works
```

## Improvement Categories

### 1. Assertions

**Goal**: One assertion that catches vuln regression + optional educational assertions.

| Replace | With |
|---------|------|
| `?? js response.parsedBody.field == x` | `?? body field == x` |
| `?? js response.status == 200` | `?? status == 200` |

**Keep**: Assertions that visualize security violations (e.g., showing attacker accessed victim's data).

**Remove**: Assertions that don't aid understanding or catch regressions.

**Smoke test guarantee**:
- `.exploit.http` MUST fail if vuln is accidentally fixed
- `.fixed.http` MUST fail if fix is accidentally removed

### 2. State Management

**Goal**: Demos must be idempotent and replayable.

For demos with DB mutations (balance changes, registrations):
1. Add setup request near top that resets relevant state
2. Use `common/setup.http` for shared seed logic
3. Port minimal `platform.seedCredits` equivalent (not full utils.cjs)

**Pattern**:
```http
### Reset state for demo
# @name setup_seed
POST {{host}}/e2e/balance
X-E2E-API-Key: {{e2e_key}}
Content-Type: application/json

{"user_id": "plankton@chum-bucket.sea", "balance": 100}
```

### 3. Clarity

**Goal**: Make implicit state explicit. Show before/after.

**Replace magic numbers**:
```http
# BAD: What is 4?
POST /cart/add
{"item_id": 4}

# GOOD: Named variable explains intent
@item_krabby_patty = 4
POST /cart/add
{"item_id": {{item_krabby_patty}}}
```

**Add console.info at state transitions**:
```http
{{
  const before = response.parsedBody.balance;
  console.info(`💰 Plankton's balance BEFORE attack: $${before}`);
  exports.balanceBefore = before;
}}
```

**Query and compare**:
```http
### Check balance after exploit
GET /account/credits
Authorization: {{plankton_auth}}

{{
  const after = response.parsedBody.balance;
  console.info(`💰 Plankton's balance AFTER attack: $${after}`);
  console.info(`📈 Gained: $${after - balanceBefore} (should not be possible!)`);
}}

?? body balance > {{balanceBefore}}
```

### 4. Educational Assertions

**Goal**: Help students see what's being violated.

Good educational assertions:
- Show attacker accessed victim's data: `?? body user_id == victim@email`
- Show unauthorized balance increase
- Show business invariant violated

Remove if:
- Just checking HTTP 200 (doesn't teach anything)
- Duplicates another assertion
- Tests implementation, not behavior

## Workflow

1. **Load skills**: `http-syntax`, `http-demo-conventions`, `spongebob-characters`
2. **List demo files** in target section
3. **For each demo**:
   - Read current content
   - Identify improvements by category
   - Apply changes preserving attack narrative
   - Verify with `httpyac file.http -a --all`
4. **Update common/setup.http** if seed helpers needed

## Red Flags

- `$(response).field()` → spec syntax, not demo
- `auth.basic()` → demos use raw Authorization headers
- Multiple dense `{{ }}` blocks → keep simple for students
- No assertion catching vuln → add smoke test
- Magic numbers without explanation

## Success Criteria

After improvements:
- [ ] Each demo is replayable (idempotent)
- [ ] httpyac runs pass
- [ ] Exploit demos would fail if vuln fixed
- [ ] Fixed demos would fail if fix removed
- [ ] State transitions are visible (console.info)
- [ ] No unexplained magic numbers
- [ ] Assertions are educational or catch regressions
