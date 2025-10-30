# Unsafe Code Lab

**Unsafe Code Lab** is an open-source collection of vulnerable, runnable backend applications built with modern web frameworks. It's designed for security engineers, researchers, and developers to explore how modern frameworks work, what makes them tick, how they break, and most importantly, how to fix them.

## The Problem: Hidden Risks in Modern Frameworks

The security of a web application depends on more than just the framework's built-in protections; it's also shaped by the subtle ways developers can misuse framework APIs. While frameworks like **Next.js**, **Django**, and **FastAPI** provide strong security foundations, they can't prevent all misconfigurations or logical flaws.

**Unsafe Code Lab was created to address this gap.**

## What You'll Find Inside

This project provides a streamlined way to understand the security landscape of modern web development.

- **Runnable Vulnerable Apps:** Each directory contains a minimal, standalone application with a specific, documented vulnerability.
- **Focus on API Design:** See firsthand how framework API design can either create security traps or completely prevent mistakes that are common elsewhere.
- **Research Harness:** Use the runnable scenarios as a harness for advanced vulnerability research and exploit development.

## Supported Frameworks

**Flask** is our model framework with complete vulnerability coverage. [**Start here with Flask confusion examples →**](vulnerabilities/python/flask/confusion/webapp/README.md)

We're actively expanding coverage to include:

| Language       | Planned Frameworks                                              |
| -------------- | --------------------------------------------------------------- |
| **Python**     | Django, Django REST Framework, FastAPI, CherryPy, Bottle       |
| **JavaScript** | Next.js, Express.js, Koa, Meteor.js, Nest.js                   |

**Want to help?** We're looking for contributors to help build vulnerability examples for these frameworks. Each framework needs runnable applications demonstrating security pitfalls in production-quality code. Check out the Flask examples to see what we're aiming for, then open an issue or PR!

## Prerequisites and Setup

- Install Docker (Docker Desktop or Docker Engine with Compose v2)
- Install uv (https://docs.astral.sh/uv/). On macOS with Homebrew: `brew install uv`.
- Install REST Client extension for VS Code to execute exploit examples (like `exploit-19.http`) found in `/http/` directories
(https://marketplace.visualstudio.com/items?itemName=humao.rest-client)
- Clone this repository:

```bash
git clone https://github.com/Irench1k/unsafe-code
cd unsafe-code
```

## Development Setup

For the best development experience with instant code reload and debug-level logs, set up your environment to use the development Docker Compose configuration:

### Option 1: Environment Variable

Set this in your shell before running any examples:

```bash
export COMPOSE_FILE=compose.yml:compose.dev.yml
```

### Option 2: .envrc with direnv (Recommended)

If you use [direnv](https://direnv.net/) (requires additional setup but provides automatic environment configuration):

```bash
echo "export COMPOSE_FILE=compose.yml:compose.dev.yml" > .envrc
direnv allow
```

**Note:** The development configuration (`compose.dev.yml`) is only meant for development and provides instant code reload and debug-level logs.

## Quick Start

The most convenient way to run examples is using Docker Compose:

### 1. Navigate to an example directory

```bash
cd languages/python/fastapi/basic
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

## Alternative Ways to Run

### From Repository Root

You can run examples from anywhere using the full path:

```bash
# From repo root
docker compose -f languages/python/fastapi/basic/compose.yml up -d

# Override host port (by default every container will bind to port 8000)
PORT=8005 docker compose -f languages/python/fastapi/basic/compose.yml up -d
```

### Using Project Names

Manage containers from anywhere using the project name:

```bash
docker compose -p python-fastapi-basic ps
docker compose -p python-fastapi-basic logs -f
docker compose -p python-fastapi-basic down -v
```

## Using uv (Project Python)

We use uv to manage Python and project dependencies. uv creates and syncs a `.venv/` automatically and maintains a cross‑platform lockfile `uv.lock` for reproducible installs.

- Python version: pinned via `.python-version` to `3.12`. uv will download it if missing.
- Project metadata: see `pyproject.toml`.
- Lockfile: `uv.lock` (commit this file).

Common commands:

```bash
# First time (optional; uv run also auto-syncs)
uv sync

# Run the docs CLI (concise alias)
uv run docs --help
```

### Documentation Generation

This repo includes a documentation generator that scans for `@unsafe` annotations and produces README files.

```bash
# List all documentation targets
uv run docs list -v

# Generate documentation for all targets
uv run docs all -v

# Generate for a specific target
uv run docs generate \
  --target languages/python/flask/blueprint/webapp/r01_ii/r01_source_precedence/

# Dry run (no file writes) and verbose logging
uv run docs generate --dry-run -v --target <path/to/target>

# Run unit tests for the docs tool
uv run docs test -v

# Verify that README/index are up-to-date (CI-friendly)
uv run docs verify -v

# Run type checker (mypy) on tools/ directory
uv run mypy

# Run linter (ruff) on tools/ directory
uv run ruff check tools/

# Auto-fix linting issues where possible
uv run ruff check tools/ --fix

Tip: Enable shell completion for `docs` (optional):

uv run docs --install-completion

Or add an alias for even shorter commands:

alias docs='uv run docs'
```

uv will ensure the environment matches `pyproject.toml` and `uv.lock` before each run. No need to activate a virtualenv.

