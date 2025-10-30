# Flask Auto-Discovery Routing Example

A Flask application demonstrating **automatic route discovery** using `importlib` and `pkgutil`. No manual route imports required - just create route modules and they're automatically registered!

## Quick Start

```bash
cd foundations/python/flask/routing-multifile-autodiscovery
docker compose up -d

# View logs to see auto-discovery in action
docker compose logs -f

# Test endpoints
curl http://localhost:8000/users/
curl http://localhost:8000/posts/

# Stop and clean up
docker compose down
```

## How Auto-Discovery Works

The application [automatically scans](./webapp/__init__.py) for route modules and registers them:

```python
def _auto_discover_routes(app):
    """Automatically discover and register routes from subpackages."""
    import webapp

    for finder, name, ispkg in pkgutil.iter_modules(webapp.__path__):
        if not ispkg:  # Skip non-packages
            continue

        try:
            routes_module = importlib.import_module(f'webapp.{name}.routes')
        except ModuleNotFoundError:
            continue  # No routes.py in this subpackage

        # Register using blueprint or function approach
        if hasattr(routes_module, 'bp'):
            app.register_blueprint(routes_module.bp)
        elif hasattr(routes_module, 'register'):
            routes_module.register(app)
```

## Project Structure

```
run.py              # Application entry point
webapp/             # Main application module
├── __init__.py     # App factory with auto-discovery logic
├── users/          # Blueprint approach example
│   └── routes.py   # Exports 'bp' Blueprint
└── posts/          # Function registration example
    └── routes.py   # Exports 'register(app)' function
```

## Route Registration Approaches

### 1. Blueprint Approach (`/users/`)

```python
# users/routes.py
from flask import Blueprint
bp = Blueprint('users', __name__, url_prefix='/users')

@bp.route('/')
def list_users():
    return {"users": ["alice", "bob", "charlie"]}
```

**Pros:** Clean, idiomatic Flask, built-in URL prefixes, easy testing  
**Cons:** Slightly more setup

### 2. Function Registration (`/posts/`)

```python
# posts/routes.py
def register(app):
    # Decorator approach
    @app.route('/posts/', endpoint='posts.list')
    def list_posts():
        return {"posts": ["post1", "post2", "post3"]}

    # Function approach
    app.add_url_rule('/posts/<int:post_id>', 'posts.get', get_post)

def get_post(post_id):
    return {"post_id": post_id, "title": f"Post {post_id}"}
```

**Pros:** Maximum control, shows both decorator and function styles  
**Cons:** Need to manage endpoint names manually

## Benefits of Auto-Discovery

- ✅ **No manual imports** - Just create `routes.py` and it's discovered
- ✅ **Convention over configuration** - Follow naming patterns, get automatic registration
- ✅ **Flexible** - Supports both blueprints and function registration
- ✅ **Scalable** - Add new modules without touching main app code
- ✅ **Clean separation** - Each feature in its own package

## Available Endpoints

- `GET /users/` - List users (Blueprint approach)
- `GET /users/<id>` - Get user by ID
- `GET /posts/` - List posts (Function registration with decorator)
- `GET /posts/<id>` - Get post by ID (Function registration with add_url_rule)
