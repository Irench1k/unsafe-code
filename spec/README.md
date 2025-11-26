# E2E Spec Suite

Httpyac-based e2e tests with inheritance and version-aware utilities.

## Quick Start

```bash
# Run all v301 specs
httpyac v301 -a

# Stop at the first failure
httpyac v301 -a --bail

# Only run leaf requests (tags are auto-managed by spec-sync)
uv run spec-sync generate v301
httpyac v301 --tag ci

# Run specific spec
httpyac v301/spec.21.new.vuln-dual-auth-refund.http -a --bail

# Sync inherited specs from spec.yml
uv run spec-sync
```

## Structure

```
spec/
├── spec.yml          # Inheritance config
├── common.http       # Shared imports
├── utils.cjs         # Test utilities (see below)
├── v100/             # Baseline specs
│   ├── .env          # VERSION=v100
│   └── spec.*.http
└── v301/             # Authorization confusion (21 specs)
    ├── .env          # VERSION=v301
    └── spec.*.http
```

## Writing Specs

Every spec file needs:

```http
# @specname = get-orders-happy
# @import ../common.http

# Description of what this tests

// The JS script in global scope gets executed before EACH request.
// This BREAKS statefull multi-request tests.
{{
  await platform.seed({ plankton: 200 });
}}

### Test case name
// This JS script runs in the request scope, only when the request is made!
{{
  await platform.seedCredits("plankton", 200);
}}
GET /orders
Authorization: {{auth.basic("plankton")}}

?? js $(response).isOk() == true
?? js $(response).hasOnlyUserData("plankton") == true
```

## Utilities (utils.cjs)

### Response Wrapper `$(response)`

```http
?? js $(response).status() == 200
?? js $(response).isOk() == true
?? js $(response).hasFields("id", "email", "balance") == true
?? js $(response).field("email") == plankton@chum-bucket.sea
?? js $(response).hasOnlyUserData("plankton") == true
```

### Authentication

```http
# Basic Auth (version-aware)
Authorization: {{auth.basic("plankton")}}

# Session cookie
Cookie: {{auth.login("plankton")}}

# Restaurant API key
X-API-Key: {{auth.restaurant("krusty_krab")}}

# Admin/platform key
X-Admin-API-Key: {{auth.admin()}}
```

### Test Setup

```http
{{
  // Reset DB and seed user balances
  await platform.seed({
    plankton: 200,
    squidward: 150
  });
}}
```

### User Data

```http
{{
  const u = user("plankton");
  // u.email, u.password, u.id, u.role
}}
```

## Inheritance (spec.yml)

```yaml
v301:
  specs:
    # Inherited from another version
    - inherits: v300.get-orders-happy

    # New spec for this version
    - name: vuln-dual-auth-refund
```

Run `uv run spec-sync` to copy inherited specs and renumber files.

## Naming Convention

```
spec.NN.TYPE.SPECNAME.http

NN      = sequence number (01, 02, ...)
TYPE    = new | inherited
SPECNAME = matches @specname in file
```

## See v301 for Complete Examples

The `spec/v301/` directory contains 21 production-quality specs covering:

- Authentication (register, login, logout)
- Account management (credits, info)
- Cart operations (create, add items, checkout)
- Orders (list, refund, status)
- Restaurants (list)
- Vulnerability demo (dual-auth refund exploit)
