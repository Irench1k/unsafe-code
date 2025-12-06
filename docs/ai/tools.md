# CLI & Tooling Reference

Single-source reference for project tooling. All commands run from any directory unless noted.

---

## ucdemo — Interactive Demo Runner
Purpose: run `.http` demo files with httpyac.
```bash
ucdemo [target] [options]
```
### Targets
| Format | Description |
|--------|-------------|
| `r02` | All demos in section 02 |
| `r02/e03` | Exercise 03 in section 02 |
| `path/to/dir` | All .http files in directory |
| `file.http` | Single file |
| `.` | Current directory |

### Options
| Option | Description |
|--------|-------------|
| `--bail` | Stop at first failure |
| `-k`, `--keep-going` | Run all files even on failure |
| `-v`, `--verbose` | Full httpyac output |
| `--no-logs` | Skip docker logs on failure |

### Exit Codes
0 = pass; 1 = failures; 2 = invalid args.

### Examples
```bash
ucdemo r02
ucdemo r02/e03 --bail
ucdemo . -k
```

---

## uctest — E2E Spec Runner
Purpose: run specs in `spec/`.
```bash
uctest [target] [options]
```
Targets: `v301/`, `v301/cart/checkout/`, single file, `@vulnerable`, `@v301 @vulnerable`.
Options: fail-fast by default; `-k` keep going; `-a` run all; `--tag <tag>`; `-v` verbose.
Exit: 0 = pass; non-zero = failure.
Examples:
```bash
uctest v301/
uctest v301/cart/ -k
uctest @vulnerable
```

---

## ucsync — Spec Inheritance Manager
Purpose: regenerate inherited `~` files from `spec.yml`.
```bash
ucsync [versions...] [options]
```
Arguments: none = all versions; `v302` = specific; `clean` = remove all generated; `clean v302` = clean one version.
Options: `-n/--dry-run`, `-v/--verbose`, `-q/--quiet`.
Never edit `~` files directly.
Examples:
```bash
ucsync
ucsync v302 v303
ucsync -n
ucsync clean
```

---

## ucdiff — Exercise Diff Tool
Purpose: compare exercise versions to identify changes, drift, and missing specs.
```bash
ucdiff [versions] [options]
```

### Version Syntax
| Format | Description |
|--------|-------------|
| `v307` | Auto-compare with previous (v306) |
| `v306 v307` | Compare two specific versions |
| `v306..v307` | Range syntax (same as above) |
| `r03` | Show all diffs within section |

### Primary Flags
| Flag | Short | Description |
|------|-------|-------------|
| (default) | | Tree view with +/- stats per file |
| `--code` | `-c` | Syntax-aware diff (via difftastic) |
| `--outline` | `-o` | Function-level changes (added/modified/deleted) |
| `--routes` | `-r` | Route-level changes only (@bp.route decorators) |
| `--list` | `-l` | Just filenames (for scripting) |
| `--json` | | Machine-readable JSON |

### Display & Tool Options
| Option | Short | Description |
|--------|-------|-------------|
| `--side` | `-S` | Side-by-side view for `--code` (default: inline) |
| `--focused` | `-F` | Max noise reduction (ignore comments + context=1) |
| `--tool {difft,delta,icdiff}` | | Diff tool for `--code` (default: difft) |
| `--ignore-comments` | | Skip comment-only changes (difftastic only) |
| `--context N` | `-U N` | Context lines for diff (default: 3) |

**Tool differences:** `difft` = syntax-aware; `delta` = word-level highlighting; `icdiff` = traditional columns

**Ergonomic combos:** `-cS` (code side-by-side), `-cF` (focused code), `-cSF` (focused side-by-side)

### Filters
| Option | Description |
|--------|-------------|
| `-f`, `--file` | Filter to files matching pattern |
| `-b`, `--boring` | Show boring files at full brightness |
| `--added-only` | Only show added files |
| `--modified-only` | Only show modified files |
| `--deleted-only` | Only show deleted files |
| `--check-specs` | Warn if code changes lack spec updates |

**Boring files** (dimmed by default): `__init__.py`, `config.py`, `fixtures/`, `models/`, `database/`

### Evolution Mode
| Option | Description |
|--------|-------------|
| `-e` | Full section evolution matrix (all files) |
| `-e FILE` | Evolution filtered to matching files |
| `-oe` / `-eo` | Evolution + function outline per transition |
| `-re` / `-er` | Evolution + route changes per transition |

**Patterns:** exact path (`routes/orders.py`), partial name (`orders.py`), directory (`routes/`), glob (`routes/*.py`)

### Examples
```bash
# Overview (what changed?)
ucdiff v307                       # Auto-compare with v306
ucdiff r03                        # All diffs in section

# Code inspection (how did it change?)
ucdiff v307 -c                    # Syntax-aware inline diff
ucdiff v307 -cS                   # Side-by-side view
ucdiff v307 -cF                   # Focused (max noise reduction)

# Function/route outline (which functions changed?)
ucdiff v307 -o                    # Function-level changes
ucdiff v307 -r                    # Route handlers only

# Evolution (track changes across ALL versions)
ucdiff r03 -e                     # Full section evolution matrix
ucdiff r03 -e routes/             # Evolution of routes/ only
ucdiff r03 -e orders.py           # Evolution of specific file
ucdiff r03 -oe                    # Function evolution for section
ucdiff r03 -re                    # Route evolution for section
ucdiff r03 -re routes/            # Route evolution for routes/

# Scripting & analysis
ucdiff v307 -l                    # Just filenames
ucdiff v307 --json                # Machine-readable
```

### Integration Hints
After showing diff, ucdiff suggests relevant commands:
- Code changed → `uctest v307/`
- Spec drift detected → `ucsync v307`
- Demo files changed → `ucdemo r03/e07`

Disable with `--no-hints`.

---

## Docker Compose Helpers
compose file at `vulnerabilities/python/flask/confusion/compose.yml` (wrappers auto-detect).
- `ucup [-d|--no-build]` – start services
- `ucdown` – stop services (`--volumes --remove-orphans`)
- `uclogs [--tail=50|-f|service]` – view logs

Services: app (8000), db (internal), mailpit (8025). Restart after Dockerfile/dependency/env changes or crashes.

---

## uclint — Spec Linter
```bash
uclint [VERSION...] [options]
```
Options: `-a/--all`, `--strict`.
Checks: jurisdiction violations, file length warnings, test count warnings, fake tests (JS only, no HTTP).
Examples:
```bash
uclint v301
uclint --all --strict
```

---

## uv run docs — README Generator
```bash
uv run docs list
uv run docs verify        # Fails if READMEs stale
uv run docs generate
uv run docs all           # Index + generate
```

---

## Key Paths
| Path | Purpose |
|------|---------|
| `spec/` | E2E specs |
| `spec/spec.yml` | Inheritance config |
| `spec/utils.cjs` | Test helpers |
| `vulnerabilities/python/flask/confusion/` | Flask tutorial |
| `vulnerabilities/.../webapp/r0N_*/http/` | Demos |
| `vulnerabilities/.../compose.yml` | Docker Compose |
| `tools/` | Project tooling |

---

## Directory Requirements
| Command | Run From | Notes |
|---------|----------|-------|
| `uctest` | Anywhere | Auto-`cd` to `spec/` |
| `ucsync` | Anywhere | Auto-detects `spec.yml` |
| `ucdemo` | Anywhere | Auto-resolves paths |
| `ucdiff` | Anywhere | Auto-resolves version paths |
| `ucup`/`ucdown`/`uclogs` | Near compose.yml | Wrappers auto-detect compose path |
| `uclint` | Anywhere | Auto-detects specs |

---

## Quick Reference
| Task | Command |
|------|---------|
| Run demos | `ucdemo r02` |
| Run specs | `uctest v301/` |
| Regenerate inherited | `ucsync` |
| Start services | `ucup -d` |
| View logs | `uclogs -f` |
| Stop services | `ucdown` |
| Lint specs | `uclint --all` |
| Verify docs | `uv run docs verify` |
| Compare exercises | `ucdiff v307` |
| Function changes | `ucdiff v307 -o` |
| Route changes | `ucdiff v307 -r` |
| Code side-by-side | `ucdiff v307 -cS` |
| Section evolution | `ucdiff r03 -e` |
| Route evolution | `ucdiff r03 -re` |
| File evolution | `ucdiff r03 -e routes.py` |

---

## Common Tool Workflows
- Debug failing spec: `uctest v301/cart/checkout/post/authn.http -v`; `uclogs --tail=50`; `ucsync v301 -n`.
- Validate demo changes: `ucdemo r02/e03`; `uclogs --tail=30`.
- Full version test: `ucsync v302`; `uctest v302/`; `uclogs --tail=50`.
- Pre-commit (content): `uctest v301/ -k`; `ucdemo r03 -k`; `uv run docs verify -v` for docs changes.
- Propagate fix to next version: `ucdiff v306 v307`; identify changes; copy to v308.
- Detect drift across section: `ucdiff r03 -e auth/decorators.py`; find unexpected changes.
- Verify spec coverage: `ucdiff v307 --check-specs`; address any spec gaps.
