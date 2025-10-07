# Foundations

**Foundations** is a collection of non-vulnerable, educational examples that demonstrate common architectural patterns and best practices in modern web frameworks. These examples serve as building blocks for understanding how frameworks work before exploring their security vulnerabilities.

## Purpose

Before diving into security vulnerabilities, it's essential to understand how frameworks are designed to work correctly. The **Foundations** directory provides clean, well-structured examples that showcase:

- **Framework Fundamentals:** Basic application structure and setup patterns
- **Architectural Patterns:** Common ways to organize and structure larger applications
- **Best Practices:** Recommended approaches for routing, configuration, and code organization

These examples complement the vulnerable code in the main project by providing a solid baseline of how things *should* work.

## Running the Examples

All examples follow the same Docker Compose setup as the main project:

```bash
# Navigate to any example
cd foundations/python/flask/basic

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
| **[Flask](/foundations/python/flask/)** | Blueprint route precedence vulnerabilities | [→ View Examples](/foundations/python/flask/README.md) |
| **[Django](/foundations/python/django/)** | Basic setup | [→ View Examples](/foundations/python/django/basic/README.md) |
| **[Django REST Framework](/foundations/python/django_rest_framework/)** | Basic setup | [→ View Examples](/foundations/python/django_rest_framework/basic/README.md) |
| **[FastAPI](/foundations/python/fastapi/)** | Basic setup with security considerations | [→ View Examples](/foundations/python/fastapi/basic/README.md) |
| **[CherryPy](/foundations/python/cherrypy/)** | Dispatch and REST API security issues | [→ View Examples](/foundations/python/cherrypy/README.md) |
| **[Bottle](/foundations/python/bottle/)** | Minimal framework security patterns | [→ View Examples](/foundations/python/bottle/basic/README.md) |

### JavaScript

| Framework | Examples | Details |
|-----------|----------|---------|
| **[Express.js](/foundations/javascript/expressjs/)** | Basic setup with common security pitfalls | [→ View Examples](/foundations/javascript/expressjs/basic/README.md) |