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

---

## Common Tool Workflows
- Debug failing spec: `uctest v301/cart/checkout/post/authn.http -v`; `uclogs --tail=50`; `ucsync v301 -n`.
- Validate demo changes: `ucdemo r02/e03`; `uclogs --tail=30`.
- Full version test: `ucsync v302`; `uctest v302/`; `uclogs --tail=50`.
- Pre-commit (content): `uctest v301/ -k`; `ucdemo r03 -k`; `uv run docs verify -v` for docs changes.
