---
name: uclab-tools
description: CLI tool quick reference for Unsafe Code Lab. Auto-invoke when running tests, debugging failures, managing inheritance, checking logs, troubleshooting "Connection refused" errors, diagnosing 500 errors, or needing uctest/ucdemo/ucsync/uclogs/docs command syntax. Covers all project CLI tools.
---

# Unsafe Code Lab CLI Tools

Quick reference for project CLI tools.

## Tool Overview

| Tool | Purpose | Used For |
|------|---------|----------|
| `uctest` | E2E spec runner | `spec/vNNN/` files ONLY |
| `ucdemo` | Demo runner | Interactive demos in `vulnerabilities/.../http/` |
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

## ucdemo - Interactive Demo Runner

**ALWAYS use `ucdemo` for demos.** It wraps httpyac with sensible defaults.

```bash
# Run all demos in a section
ucdemo r02

# Run specific exercise demos
ucdemo r02/e03

# Run single file
ucdemo path/to/demo.http

# Stop on first failure (for debugging)
ucdemo r02 --bail

# Keep going to see ALL failures (for analysis)
ucdemo r02 -k

# Verbose output (show all request/response exchanges)
ucdemo r02 -v

# Full help
ucdemo --help
```

### What ucdemo Does Automatically

1. **Finds config:** Locates `.httpyac.js` and runs from correct directory
2. **Isolates failures:** Runs each file separately to prevent cascading errors
3. **Shows debug info:** On failure, shows request/response exchange + docker logs
4. **Reports summary:** Pass/fail counts with failed file list

### Output Example

```
Running 14 demo file(s) in: vulnerabilities/.../r02/http

  e01_session_hijack.exploit.http                   PASS
  e01_session_hijack.fixed.http                     PASS
  e02_credit_top_ups.exploit.http                   FAIL

─── Failure Details: e02_credit_top_ups.exploit.http ───
✖ status == 200 (AssertionError: status (401) == 200)
───────────────────────────────────────────

─── Docker Compose Logs (last 30 lines) ───
app-1    | Invalid credentials for plankton@...
────────────────────────────────────────────

Summary: 2 passed, 1 failed (of 3 files)
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
ucdemo r02/e03

# 2. If failures, check docker logs (ucdemo shows them automatically)
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
| Run student demos | `ucdemo` |
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
Check for missing operator in `?? js` line. See `http-gotchas` + `http-syntax` skills.

## See Also

- `spec-conventions` skill - Writing E2E tests + inheritance
- `demo-conventions` skill - Writing demos
- `http-syntax` + `http-gotchas` skills - Assertion syntax & pitfalls
