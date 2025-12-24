# Contributing to Unsafe Code Lab

Thank you for your interest in contributing!

## Development Setup

Development happens on the `develop` branch, which contains additional tooling and infrastructure not needed by end users.

```bash
# Clone and switch to develop
git clone https://github.com/Irench1k/unsafe-code
cd unsafe-code
git checkout develop

# Install development dependencies
uv sync --all-extras

# Start the Flask app
cd vulnerabilities/python/flask/confusion
docker compose up -d
```

## Quick Start

1. Navigate to an exercise directory (e.g., `flask-confusion/webapp/r01_input_source_confusion/e01_dual_parameters/`)
2. Read the `README.md` to understand the vulnerability
3. Open the `.http` files in VSCode with REST Client
4. Study the source code to understand why the vulnerability exists

## What Makes a Good Vulnerability Example

We create **realistic vulnerabilities** that emerge from natural coding patterns:

- Refactoring drift (decorator reads different source than handler)
- Feature additions that introduce edge cases
- Framework helper functions with subtle precedence rules

**Avoid:**
- CTF-style puzzles or contrived code
- Obvious markers like `# VULNERABILITY HERE`
- Code that would fail a normal code review for non-security reasons

## Reporting Issues

Please open an issue on GitHub for:
- Bugs in the vulnerable code (that aren't the intended vulnerability!)
- Documentation improvements
- New vulnerability ideas

## Code of Conduct

Be respectful and constructive. This is an educational project.
