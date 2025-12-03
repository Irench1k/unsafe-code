---
name: uclab-tools
description: CLI tool quick reference for Unsafe Code Lab. Auto-invoke when running tests, debugging failures, managing inheritance, or checking logs. Covers uctest, ucsync, httpyac, uclogs, and the docs generator.
---

# Unsafe Code Lab CLI Tools

Quick reference for project CLI tools.

## Tool Overview

| Tool | Purpose | Used For |
|------|---------|----------|
| `uctest` | E2E spec runner | `spec/vNNN/` files ONLY |
| `httpyac` | HTTP client | Interactive demos ONLY |
| `ucsync` | Inheritance manager | `spec.yml` sync |
| `uclogs` | Docker log viewer | Debugging server issues |
| `uv run docs` | Doc generator | README generation |

## uctest - E2E Spec Runner

Run E2E specs in `spec/` directory. **NOT for interactive demos!**

```bash
# Run all tests in a version
uctest v301/

# Run specific endpoint tests
uctest v301/cart/checkout/

# Run single file
uctest v301/cart/checkout/post/happy.http

# Run with tag filter
uctest v301/ --tag authn
uctest v301/ --tag happy

# Verbose output
uctest v301/ -v

# Stop on first failure
uctest v301/ --fail-fast
```

### Common Patterns

```bash
# Run all auth tests
uctest v301/ --tag authn

# Run exploit-specific tests
uctest v301/ --tag exploit

# Run happy path only
uctest v301/ --tag happy
```

### Output Interpretation

```
✓ cart/checkout/post/happy.http::Successful checkout (3 assertions)
✗ cart/checkout/post/authn.http::Missing auth header
  Expected: 401
  Actual: 200
```

- `✓` = Test passed
- `✗` = Test failed (shows expected vs actual)

## httpyac - Interactive Demo Runner

Run interactive demos in `vulnerabilities/.../http/` directories.

```bash
# Run all requests in file
httpyac file.http -a

# Run single request (by name/line)
httpyac file.http -n "SpongeBob checks messages"

# Verbose output
httpyac file.http -a -v

# Output response bodies
httpyac file.http -a --output-responses
```

### Demo Locations

```
vulnerabilities/python/flask/confusion/webapp/
└── r03_authorization_confusion/
    └── http/
        ├── common/
        │   └── setup.http
        ├── e01/
        │   ├── e01_dual_auth_refund.exploit.http
        │   └── e01_dual_auth_refund.fixed.http
        └── e02/
            └── ...
```

## ucsync - Inheritance Manager

Manage spec inheritance from `spec.yml`.

```bash
# Regenerate inherited files for version
ucsync v302

# Check inheritance health (dry run)
ucsync v302 --check

# Force regeneration (removes stale ~files)
ucsync v302 --force

# Sync all versions
ucsync --all

# Show what would change
ucsync v302 --dry-run
```

### When to Run

- After editing `spec.yml`
- After adding exclusions
- When `~` files seem stale
- After "ref not found" errors

## uclogs - Docker Log Viewer

View and filter Docker container logs.

```bash
# View recent logs
uclogs

# Follow logs (tail -f style)
uclogs -f

# Filter by level
uclogs --level error
uclogs --level warning

# Filter by time
uclogs --since 5m
uclogs --since 1h

# Filter by container
uclogs --container webapp
```

### Common Debug Patterns

```bash
# See errors from last 10 minutes
uclogs --level error --since 10m

# Watch for issues during test run
uclogs -f &
uctest v301/
```

## uv run docs - Documentation Generator

Generate README files from `@unsafe` annotations.

```bash
# Generate all docs
uv run docs generate

# Generate for specific path
uv run docs generate --target vulnerabilities/python/flask/confusion/

# Verify annotations (no generation)
uv run docs verify

# Show what would be generated
uv run docs generate --dry-run
```

### Annotation Format

```python
# @unsafe {
#   "vulnerability": "parameter-source-confusion",
#   "severity": "high",
#   "cwe": "CWE-20"
# }
def vulnerable_function():
    ...
```

## Workflow Combinations

### Debug Failing Spec

```bash
# 1. Run the failing test
uctest v301/cart/checkout/post/authn.http -v

# 2. Check server logs for errors
uclogs --level error --since 5m

# 3. If inheritance issue
ucsync v301 --check
```

### Validate New Demo

```bash
# 1. Run the demo
httpyac vulnerabilities/.../http/e03/e03_exploit.http -a

# 2. Check server processed correctly
uclogs --since 1m

# 3. Regenerate docs if annotations changed
uv run docs generate --target vulnerabilities/.../
```

### Full Version Test

```bash
# 1. Sync inheritance
ucsync v302

# 2. Run all specs
uctest v302/

# 3. Check for server issues
uclogs --level error
```

## Tool Selection Guide

| Task | Tool |
|------|------|
| Run E2E tests | `uctest` |
| Run student demos | `httpyac` |
| Fix "ref not found" | `ucsync` |
| Debug 500 errors | `uclogs` |
| Update READMEs | `uv run docs` |
| Check inheritance | `ucsync --check` |

## Common Errors

### "ref not found"
```bash
ucsync v302 --check  # See what's missing
ucsync v302          # Regenerate
```

### "Connection refused"
```bash
# Server not running
docker compose up -d
uclogs -f  # Watch startup
```

### "Assertion syntax error"
Check for missing operator in `?? js` line. See `http-assertion-gotchas` skill.

## See Also

- `http-e2e-specs` skill - Writing E2E tests
- `http-interactive-demos` skill - Writing demos
- `spec-inheritance` skill - Inheritance details
- `http-assertion-gotchas` skill - Assertion syntax
