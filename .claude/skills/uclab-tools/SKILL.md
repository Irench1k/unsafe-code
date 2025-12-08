---
name: uclab-tools
description: CLI tool quick reference for Unsafe Code Lab. Auto-invoke when running tests, debugging failures, managing inheritance, checking logs, comparing exercises, troubleshooting "Connection refused" errors, diagnosing 500 errors, or needing uctest/ucdemo/ucsync/ucdiff/uclogs/docs command syntax. Covers all project CLI tools.
---

# Unsafe Code Lab CLI Tools

Quick reference for project CLI tools.

---

## ⛔ CRITICAL: Docker Infrastructure Rule

**`ucup` is ALWAYS running in the background with auto-reload enabled.**

### What This Means

- The Flask app runs inside Docker, NOT on your host
- When Python files change, the app auto-reloads
- You verify changes via `uclogs`, NOT by running Python

### NEVER Do These

| ❌ Forbidden | Why |
|--------------|-----|
| `docker compose up` | User manages via `ucup` |
| `python app.py` | App runs in Docker |
| `pip install` / `uv sync` on host | Dependencies in Docker |
| `source .venv/bin/activate` | No local venv needed |

### If Docker Seems Down

**DO NOT try to start it yourself!**

Say to the user:
```
Docker compose doesn't seem to be responding.
Could you check if `ucup` is running?
```

### Verify Changes Work

```bash
# After editing Python files, check if app reloaded cleanly
uclogs --since 1m

# If you see errors, fix them and check again
uclogs --since 2m | grep -i error
```

---

## Tool Overview

| Tool | Purpose | Used For |
|------|---------|----------|
| `uctest` | E2E spec runner | `spec/vNNN/` files ONLY |
| `ucdemo` | Demo runner | Interactive demos in `vulnerabilities/.../http/` |
| `ucsync` | Inheritance manager | `spec.yml` sync |
| `ucdiff` | Exercise diff tool | Compare versions, find drift, check spec gaps |
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

## ucdiff - Exercise Diff Tool

Compare exercise versions to identify changes, drift, and missing specs.
**Use this BEFORE propagating fixes or reviewing exercise quality.**

```bash
# Overview: What changed? (default tree view)
ucdiff v307                       # Auto-compare with v306
ucdiff r03                        # All changes in section

# Code: How did it change? (syntax-aware diff)
ucdiff v307 -c                    # Inline syntax-aware diff
ucdiff v307 -cS                   # Side-by-side view
ucdiff v307 -cF                   # Focused (max noise reduction)

# Outline: What functions changed?
ucdiff v307 -o                    # Function-level changes
ucdiff v307 -r                    # Route handlers only

# Evolution (track changes across ALL section versions)
ucdiff r03 -e                     # Full section evolution matrix
ucdiff r03 -e routes/             # Evolution of routes/ only
ucdiff r03 -e orders.py           # Evolution of specific file
ucdiff r03 -oe                    # Function evolution for section
ucdiff r03 -re                    # Route evolution for section

# Scripting
ucdiff v307 -l                    # Just filenames
ucdiff v307 --json                # Machine-readable
```

### Primary Flags

| Flag | Short | Description |
|------|-------|-------------|
| (default) | | Tree view with +/- stats per file |
| `--code` | `-c` | Syntax-aware diff (via difftastic) |
| `--outline` | `-o` | Function-level changes (added/modified/deleted) |
| `--routes` | `-r` | Route-level changes only (@bp.route decorators) |
| `--list` | `-l` | Just filenames (for scripting) |
| `--json` | | Machine-readable output |

### Display Options

| Flag | Short | Description |
|------|-------|-------------|
| `--side` | `-S` | Side-by-side view for `--code` mode |
| `--focused` | `-F` | Max noise reduction (--ignore-comments + context=1) |
| `--tool {difft,delta,icdiff}` | | Diff tool for `--code` mode (default: difft) |

**Tool differences:**
- `difft` (default): Syntax-aware, understands code structure, supports `--ignore-comments`
- `delta`: Word-level highlighting, shows exact characters changed
- `icdiff`: Traditional side-by-side columns

### Noise Reduction

| Flag | Description |
|------|-------------|
| `--ignore-comments` | Skip comment-only changes (difftastic only) |
| `--focused` | Max noise reduction (`--ignore-comments` + context=1) |
| `-U N` | Context lines for diff (default: 3) |

### Filters

| Flag | Description |
|------|-------------|
| `-f`, `--file` | Only files matching pattern |
| `-b`, `--boring` | Show boring files at full brightness |
| `--added-only` | Only show added files |
| `--modified-only` | Only show modified files |
| `--deleted-only` | Only show deleted files |

**Boring files** (dimmed by default): `__init__.py`, `config.py`, `fixtures/`, `models/`, `database/`

### Evolution Mode

| Flag | Description |
|------|-------------|
| `-e` | Full section evolution matrix (all files) |
| `-e FILE` | Evolution filtered to matching files |
| `-oe` / `-eo` | Evolution + function outline per transition |
| `-re` / `-er` | Evolution + route changes per transition |

**Patterns:** exact path (`routes/orders.py`), partial name (`orders.py`), directory (`routes/`), glob (`routes/*.py`)

### When to Use

- **Before propagating a fix**: `ucdiff v306 v307` to see exactly what changed
- **Detecting drift**: `ucdiff r03 -e file.py` to track file evolution
- **Review exercise quality**: `ucdiff r03` for section overview
- **Find missing specs**: `ucdiff v307 --check-specs`
- **Scripting/CI**: `ucdiff v306..v307 --json`

### Integration Hints

After showing diff, ucdiff suggests relevant follow-up commands:
- Code changed → `uctest v307/`
- Spec drift detected → `ucsync v307`
- Demo files changed → `ucdemo r03/e07`

Disable with `--no-hints`.

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

### Propagate Fix to Next Exercise

```bash
# 1. See what changed in current fix
ucdiff v306 v307

# 2. Identify which files need copying to v308
ucdiff v306..v307 -m files

# 3. After copying, verify spec coverage
ucdiff v308 --check-specs

# 4. Run tests
uctest v308/
```

### Review Exercise Quality

```bash
# 1. Overview of section changes
ucdiff r03

# 2. Track specific file evolution
ucdiff r03 -e routes/restaurants.py

# 3. Check all specs pass
uctest v301/ && uctest v302/ && uctest v303/

# 4. Run all demos
ucdemo r03 -k
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
| Compare exercises | `ucdiff v307` |
| Track file drift | `ucdiff r03 -e file.py` |
| Find spec gaps | `ucdiff v307 --check-specs` |

## Common Errors

### "ref not found"
```bash
ucsync v302 --check  # See what's missing
ucsync v302          # Regenerate
```

### "Connection refused"

Server not running. **Do NOT try to start it yourself!**

Say to the user:
```
Docker doesn't seem to be responding. Could you check if `ucup` is running?
```

Then wait for the user to resolve the infrastructure issue.

### "Assertion syntax error"
Check for missing operator in `?? js` line. See `http-gotchas` + `http-syntax` skills.

## See Also

- `spec-conventions` skill - Writing E2E tests + inheritance
- `demo-conventions` skill - Writing demos
- `http-syntax` + `http-gotchas` skills - Assertion syntax & pitfalls
