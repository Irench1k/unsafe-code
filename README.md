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

## Use Cases

You can use Unsafe Code Lab to:

- **Onboard Quickly:** Get up to speed on the security nuances of an unfamiliar framework or tech stack.
- **Perform Better Code Reviews:** Run targeted secure code reviews by using these examples as a reference for what to look for.
- **Conduct Security Research:** Analyze how different frameworks handle security-sensitive operations and discover new vulnerabilities.
- **Learn & Teach:** Demonstrate common security pitfalls to your team in a practical, hands-on way.

## Supported Frameworks

Our first public release covers ten modern frameworks across Python and JavaScript. Each framework lives in its own directory in this repository.

| Language       | Frameworks                                                      |
| -------------- | --------------------------------------------------------------- |
| **Python**     | Django, Django REST Framework, FastAPI, Flask, CherryPy, Bottle |
| **JavaScript** | Next.js, Express.js, Koa, Meteor.js, Nest.js                    |

_...and more coming soon!_

## Prerequisites and Setup

- Install Docker (Docker Desktop or Docker Engine with Compose v2)
- Clone this repository:

```bash
git clone https://github.com/Irench1k/unsafe-code
cd unsafe-code
```

## Development Setup (Recommended)

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

## Legacy Docker Commands

For simple examples without Docker Compose, you can use Docker directly:

```bash
cd languages/python/fastapi/basic
docker build -t unsafe-fastapi-basic .
docker run --rm -p 8000:8000 --name fastapi-basic unsafe-fastapi-basic
```

**Note:** This approach doesn't provide the development benefits (code reload, debug logs) and requires manual container management.

## Documentation Generation

This project includes a documentation generation tool that automatically creates README files from code annotations. The tool scans source code for `@unsafe` annotations and generates comprehensive documentation with examples, HTTP requests, and images.

### Usage

```bash
# List all documentation targets
python -m tools.unsafe_docs list-targets -v

# Generate documentation for all targets
python -m tools.unsafe_docs run-all -v

# Generate for a specific target
python -m tools.unsafe_docs generate --target languages/python/flask/blueprint/webapp/vuln/confusion/parameter_source/
```

The tool automatically discovers `readme.yml` configuration files and processes code annotations to create detailed documentation with table of contents, code examples, and security explanations.
