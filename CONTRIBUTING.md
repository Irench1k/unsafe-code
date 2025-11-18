# Contributing to Unsafe Code Lab

Thank you for your interest in contributing! Unsafe Code Lab demonstrates security vulnerabilities through production-quality, runnable code examples.

## Getting Started: Your First Contribution

All new development for our upcoming first release happens in the `develop` branch. To contribute, please fork the repository and create a new branch from `develop`. 

Before you start coding, the best way to understand our methodology is to review the existing Flask examples. For a detailed breakdown of the security concepts we're focused on, please review our [confusion curriculum](https://github.com/Irench1k/unsafe-code/tree/develop/docs/confusion_curriculum). 

## What Makes a Good Example

We create **realistic vulnerabilities** that emerge from natural coding patterns:

- Refactoring drift (decorator reads different source than handler)
- Feature additions that introduce edge cases
- Framework helper functions with subtle precedence rules

**Avoid:**

- CTF-style puzzles or contrived code
- Obvious markers like `# VULNERABILITY HERE` or `vulnerable_handler()`
- Code that would fail a normal code review for non-security reasons

## Development Setup

For the best development experience with instant code reload and debug-level logs, configure your environment to use the development Docker Compose setup:

### Option 1: Environment Variable

Set these in your shell before running examples:

```bash
# Docker Compose configuration
export COMPOSE_FILE=compose.yml:compose.dev.yml

# Python configuration (prevents __pycache__ clutter)
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export PYTHONUTF8=1
```

### Option 2: .envrc with direnv (Recommended)

If you use [direnv](https://direnv.net/), create a `.envrc` file in the project root:

```bash
# Docker Compose configuration
export COMPOSE_FILE=compose.yml:compose.dev.yml

# Python configuration for local development
export PYTHONDONTWRITEBYTECODE=1  # Prevents bytecode (.pyc) files and __pycache__ directories
export PYTHONUNBUFFERED=1          # Ensures real-time log output (no buffering)
export PYTHONUTF8=1                # Force UTF-8 encoding for cross-platform compatibility
```

Then activate it:

```bash
direnv allow
```

**Why these Python variables?**
- `PYTHONDONTWRITEBYTECODE=1` prevents Python from creating `__pycache__` directories and `.pyc` files when running local tools (`uv run docs`, `uv run mypy`, etc.), keeping your working directory clean
- `PYTHONUNBUFFERED=1` provides real-time log visibility, essential for debugging
- `PYTHONUTF8=1` ensures consistent UTF-8 handling across different platforms

The development configuration (`compose.dev.yml`) provides instant code reload and debug-level logs. Note that the Docker containers already have these Python variables set in the Dockerfile.

### Optional: Shell Ergonomics

For faster navigation you can source our helper script from your shell config (e.g., add `source /path/to/unsafe-code/tools/dev/unsafe-code-dev.sh` to `~/.bashrc` or `~/.zshrc`). This exposes handy commands such as `ucfocus`/`ucunfocus`/`ucstatus` (VSCode focus control), `ucup`/`ucdown`/`uclogs` (docker compose shortcuts), and navigation helpers like `ucgo`, `uclist`, and `uchelp`. These are purely optional ergonomics improvements.

## Quick Start

The most convenient way to run examples is using Docker Compose:

### 1. Navigate to an example directory

```bash
cd vulnerabilities/python/flask/confusion
```

### 2. Start the application

```bash
# Run in background
docker compose up -d

# Or run in foreground to see logs directly
docker compose up
```

### 3. Monitor and manage

```bash
# View logs (lists past logs and exits)
docker compose logs

# Follow logs in real-time (keeps monitoring until Ctrl+C)
docker compose logs -f

# Check status of the running containers
docker compose ps

# Stop and clean up
docker compose down
```

### 4. Rebuilding

```bash
# Rebuild after dependency changes
docker compose build

# Force rebuild (no cache)
docker compose build --no-cache
```

### 5. Automatically Update

```bash
# Enable watching for file changes without restarting docker
docker compose up --watch
```

## Alternative Ways to Run

### From Repository Root

You can run examples from anywhere using the full path:

```bash
# From repo root
docker compose -f vulnerabilities/python/flask/confusion/compose.yml up -d

# Override host port (by default every container will bind to port 8000)
PORT=8005 docker compose -f vulnerabilities/python/flask/confusion/compose.yml up -d
```

### Using Project Names

Manage containers from anywhere using the project name:

```bash
docker compose -p python-flask-confusion ps
docker compose -p python-flask-confusion logs -f
docker compose -p python-flask-confusion down -v
```

## Installing uctest (HTTP Spec Runner)

[uctest](https://github.com/execveat/uctest) is our HTTP test runner for running the `.http` spec files in `spec/`. Install it with npm:

```bash
npm install
```

Run tests:

```bash
# Run all tests in a version
npx uctest spec/v301/

# Run tests with specific tags
npx uctest @happy

# Run a specific test by name
npx uctest :checkout

# See all options
npx uctest --help
```

## Using uv (Project Python)

We use uv to manage Python and project dependencies. uv creates and syncs a `.venv/` automatically and maintains a cross‑platform lockfile `uv.lock` for reproducible installs.

- Python version: pinned via `.python-version` to `3.12`. uv will download it if missing.
- Project metadata: see `pyproject.toml`.
- Lockfile: `uv.lock` (commit this file).

Install uv: https://docs.astral.sh/uv/
On macOS with Homebrew: `brew install uv`

Common commands:

```bash
# First time (optional; uv run also auto-syncs)
uv sync

# Run the docs CLI
uv run docs --help
```

## Documentation Generation

The repo includes a documentation generator that scans for `@unsafe` annotations and produces README files. See [docs/ANNOTATION_FORMAT.md](docs/ANNOTATION_FORMAT.md) for the annotation format specification.

```bash
# List all documentation targets
uv run docs list -v

# Generate documentation for all targets
uv run docs all -v

# Generate for a specific target
uv run docs generate --target vulnerabilities/python/flask/confusion/webapp/r01_source_precedence/

# Verify that README/index are up-to-date (run before committing)
uv run docs verify -v

# Run unit tests for the docs tool
uv run docs test -v
```

**Tip:** Enable shell completion or add an alias:

```bash
uv run docs --install-completion
# or
alias docs='uv run docs'
```

## Code Quality

Before committing, run:

```bash
# Verify documentation is up-to-date
uv run docs verify -v

# Run type checker (mypy)
uv run mypy

# Run linter (ruff)
uv run ruff check tools/

# Auto-fix linting issues where possible
uv run ruff check tools/ --fix
```

## Adding New Examples

1. Study existing examples in `vulnerabilities/python/flask/confusion/webapp/` to understand the approach
2. Add `@unsafe[function]` or `@unsafe[block]` annotations to your code (see [docs/ANNOTATION_FORMAT.md](docs/ANNOTATION_FORMAT.md))
3. Create `.http` files demonstrating the exploit in the `http/` subdirectory
4. Generate documentation: `uv run docs generate --target <your-path>`
5. Verify: `uv run docs verify -v`
6. Test the examples work correctly via Docker Compose

## Submitting Changes

1. Ensure your code runs correctly in Docker
2. Test the exploitation examples work as documented
3. Run `uv run docs verify -v` to ensure documentation is current
4. Run linters and type checkers
5. Open a pull request with a clear description

## Questions?

Open an issue for discussion before starting major new categories or framework implementations.
