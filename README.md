# Unsafe Code Lab

**Unsafe Code Lab** is an open-source collection of vulnerable, runnable backend applications built with modern web frameworks. It's designed for security engineers, researchers, and developers to explore how modern frameworks work, what makes them tick, how they break, and most importantly, how to fix them.

## The Problem: Hidden Risks in Modern Frameworks

The security of a web application depends on more than just the framework's built-in protections; it's also shaped by the subtle ways developers can misuse framework APIs. While frameworks like **Nest.js**, **Django**, and **FastAPI** provide strong security foundations, they can't prevent all misconfigurations or logical flaws.

**Unsafe Code Lab was created to address this gap.**

To get an idea of what this project is all about, we recommend to start with the [Confusion vulnerabilities](vulnerabilities/python/flask/confusion/webapp/README.md) in Flask:

1. [Source Precedence](r01_source_precedence/README.md) — Different components pull the "same" logical parameter from different places (path vs. query vs. body vs. headers vs. cookies), leading to precedence conflicts, merging issues, or source pollution.
2. [Cross-Component Parse](r02_cross_component_parse/README.md) — Middleware, decorators, or framework helpers parse or reshape inputs in ways that differ from what the view sees.
3. [Authorization Binding](r03_authz_binding/README.md) — Authorization checks identity or value X, but the handler acts on identity or value Y.
4. [HTTP Semantics](r04_http_semantics/README.md) — Wrong assumptions about HTTP methods or content types (e.g., GET with body, form vs. JSON) cause components to read different sources.
5. [Multi-Value Semantics](r05_multi_value_semantics/README.md) — One component treats a parameter as a list while another grabs only the first value, or `.get()` vs `.getlist()` disagreements create different effective values.
6. [Normalization & Canonicalization](r06_normalization_canonicalization/README.md) — Case folding, whitespace stripping, URL decoding, or path normalization makes "equal" values diverge when checked versus used.

## What You'll Find Inside

This project provides a streamlined way to understand the security landscape of modern web development.

- **Runnable Vulnerable Apps:** Each directory contains a minimal, standalone application with a specific, documented vulnerability.
- **Focus on API Design:** See firsthand how framework API design can either create security traps or completely prevent mistakes that are common elsewhere.
- **Research Harness:** Use the runnable scenarios as a harness for advanced vulnerability research and exploit development.

## Supported Frameworks

**Flask** is our model framework with complete vulnerability coverage.

We're actively expanding coverage to include:

| Language       | Planned Frameworks                                              |
| -------------- | --------------------------------------------------------------- |
| **Python**     | Django, Django REST Framework, FastAPI, CherryPy, Bottle       |
| **JavaScript** | Express.js, Koa, Meteor.js, Nest.js                   |

**Want to help?** We're looking for contributors to help build vulnerability examples for these frameworks. Each framework needs runnable applications demonstrating security pitfalls in production-quality code. Check out the Flask examples to see what we're aiming for, then see [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to contribute!

## Prerequisites and Setup

- Install Docker (Docker Desktop or Docker Engine with Compose v2)
- Install REST Client extension for VS Code to execute exploit examples (like `exploit-19.http`) found in `/http/` directories (https://marketplace.visualstudio.com/items?itemName=humao.rest-client)
- Clone this repository:

```bash
git clone https://github.com/Irench1k/unsafe-code
cd unsafe-code
```

**Contributors:** See [CONTRIBUTING.md](CONTRIBUTING.md) for additional setup including `uv` and the documentation generator.

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

