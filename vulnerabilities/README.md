# Vulnerabilities

**Vulnerabilities** is a collection of vulnerable, runnable backend applications that demonstrate security flaws in modern web frameworks. These examples showcase how developers can misuse framework APIs and create exploitable vulnerabilities despite built-in security protections.

## Purpose

Modern frameworks provide strong security foundations, but they can't prevent all misconfigurations or logical flaws. The **Vulnerabilities** directory provides real-world examples that demonstrate:

- **Common Vulnerabilities:** Security flaws that arise from framework misuse
- **Exploitable Scenarios:** Runnable applications with documented attack vectors
- **Framework-Specific Risks:** How different frameworks can create unique security traps

## Running the Examples

All examples follow the same Docker Compose setup as the main project:

```bash
# Navigate to any example
cd vulnerabilities/python/flask/blueprint

# Start the application
docker compose up -d

# View logs
docker compose logs -f

# Stop and clean up
docker compose down
```

For the best development experience, use the development configuration:

```bash
export COMPOSE_FILE=compose.yml:compose.dev.yml
docker compose up
```

## Development Setup

These examples use the same development environment as the main project. Refer to the main README for:

- Docker and uv installation
- Development configuration setup
- Environment management with direnv

## Current Examples

### Python

| Framework | Examples | Details |
|-----------|----------|---------|
| **[Flask](python/flask/)** | Blueprint route precedence vulnerabilities | [→ View Examples](python/flask/README.md) |
| **[Django](python/django/)** | Basic setup with potential security misconfigurations | [→ View Examples](python/django/README.md) |
| **[FastAPI](python/fastapi/)** | Basic setup with security considerations | [→ View Examples](python/fastapi/README.md) |
| **[CherryPy](python/cherrypy/)** | Dispatch and REST API security issues | [→ View Examples](python/cherrypy/README.md) |
| **[Bottle](python/bottle/)** | Minimal framework security patterns | [→ View Examples](python/bottle/README.md) |
| **[Pyramid](python/pyramid/)** | Web framework security patterns | [→ View Examples](python/pyramid/README.md) |

### JavaScript

| Framework | Examples | Details |
|-----------|----------|---------|
| **[Express.js](javascript/expressjs/)** | Basic setup with common security pitfalls | [→ View Examples](javascript/expressjs/README.md) |
| **[Next.js](javascript/nextjs/)** | Framework-specific security considerations | [→ View Examples](javascript/nextjs/README.md) |
| **[Koa](javascript/koa/)** | Middleware security patterns | [→ View Examples](javascript/koa/README.md) |
| **[Meteor.js](javascript/meteorjs/)** | Full-stack security scenarios | [→ View Examples](javascript/meteorjs/README.md) |
| **[Nest.js](javascript/nestjs/)** | Enterprise framework security issues | [→ View Examples](javascript/nestjs/README.md) |