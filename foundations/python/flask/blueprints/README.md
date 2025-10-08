# Flask Blueprints Example

A Flask application demonstrating blueprint-based modular organization. Blueprints group related routes into namespaced modules that can be registered with URL prefixes.

## Quick Start

```bash
cd foundations/python/flask/blueprints
docker compose up -d

# Test blueprint routes
curl http://localhost:8000/
curl http://localhost:8000/users/
curl http://localhost:8000/users/123
curl http://localhost:8000/posts/
curl http://localhost:8000/admin/

# Stop and clean up
docker compose down
```

## Project Structure

```
run.py              # Application entry point
webapp/             # Main application module
├── __init__.py     # App factory with blueprint registration
├── users/          # Users blueprint
│   └── routes.py
├── posts/          # Posts blueprint
│   └── routes.py
└── admin/          # Admin blueprint
    └── routes.py
```

## What Blueprints Demonstrate

- **Namespace isolation**: Multiple `index()` and `detail()` functions don't conflict (e.g., `users.index` vs `posts.index`)
- **URL organization**: Each blueprint gets a prefix (`/users/`, `/posts/`, `/admin/`) defined at registration
- **Modular structure**: Related routes grouped into self-contained modules
- **NOT a security boundary**: Blueprints organize code but don't provide authorization or isolation

## Why This Matters for Security

When auditing Flask applications with blueprints, recognize that namespace isolation is a code organization feature, not a security control. Authorization must be explicitly implemented—blueprint prefixes don't restrict access. Look for authentication/authorization decorators applied consistently across blueprint routes, and verify that similar route patterns across blueprints have equivalent security controls.

## Further Reading

- [Flask Blueprints Documentation](https://flask.palletsprojects.com/en/stable/blueprints/)
