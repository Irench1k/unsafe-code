# Flask Multi-File Routing Example

A Flask application demonstrating different approaches to organizing routes across multiple files and directories. Shows function-based vs decorator-based registration, URL prefixes, and endpoint naming patterns.

## Quick Start

```bash
cd foundations/python/flask/routing-multifile-register
docker compose up -d

# View logs
docker compose logs -f

# Test endpoints
curl http://localhost:8000/users/
curl http://localhost:8000/users/123
curl http://localhost:8000/posts/
curl http://localhost:8000/posts/123

# Stop and clean up
docker compose down
```

## Project Structure

```
run.py              # Application entry point
webapp/             # Main application module
├── __init__.py     # App setup and route registration
├── users/          # Example 1: Function-based routes
├── posts/          # Example 2: Decorator-based routes
├── admin/          # Example 3: Function-based + prefixes
└── api/            # Example 4: Decorator-based + prefixes
requirements.txt    # Python dependencies
Dockerfile          # Container configuration
```

## Routing Examples

This example demonstrates four different approaches to organizing Flask routes:

1. **Function-based registration** (`/users`) - Using `app.add_url_rule()`
2. **Decorator-based registration** (`/posts`) - Using `@app.route()` inside register functions
3. **Prefixed function routes** (`/admin`) - Shows endpoint naming conflicts and solutions
4. **Prefixed decorator routes** (`/api/v1`) - Clean API-style organization

Each approach has different trade-offs for maintainability, testability, and scalability.
