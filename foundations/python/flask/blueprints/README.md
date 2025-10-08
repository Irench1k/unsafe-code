# Flask Blueprints

A Flask application demonstrating hierarchical blueprint organization for structuring large, maintainable applications. Blueprints enable modular code organization by grouping related routes, templates, and static files into reusable components.

## Quick Start

```bash
# Navigate to any Flask example with blueprints (e.g., confusion vulnerability examples)
cd vulnerabilities/python/flask/confusion
docker compose up -d

# Test the hierarchical structure
curl http://localhost:8000/confusion/

# Explore nested blueprints
curl http://localhost:8000/confusion/source-precedence/
curl http://localhost:8000/confusion/authz-binding/

# Stop and clean up
docker compose down
```

## What Are Blueprints?

[Blueprints](https://flask.palletsprojects.com/en/stable/blueprints/) are Flask's way of organizing application components. They allow you to:

- **Modularize code**: Group related routes, templates, and static files
- **Create hierarchies**: Nest blueprints to reflect application structure
- **Enable reuse**: Build components that can be registered in multiple applications
- **Separate concerns**: Keep authentication, API, admin, and business logic distinct

Blueprints are similar to Flask applications but cannot run independently—they must be registered with an app.

## When to Use Blueprints

**Use blueprints when:**
- Your application has distinct functional areas (admin panel, API, public site)
- You want to organize routes into logical groups
- Multiple developers work on different features
- You need to reuse components across projects
- Your app has grown beyond a single file

**Simpler alternatives for small apps:**
- [Single-file applications](../basic/) for prototypes
- [Multi-file manual registration](../routing-multifile-register/) for moderate complexity
- [Auto-discovery patterns](../routing-multifile-autodiscovery/) for convention-based organization

## Project Structure

Here's a typical Flask application using hierarchical blueprints:

```
run.py                  # Application entry point
webapp/                 # Main application package
├── __init__.py         # App factory with blueprint registration
├── routes.py           # Root blueprint
└── feature_area/       # Feature-specific package
    ├── routes.py       # Feature blueprint with nested registration
    ├── subfeature_a/   # Nested feature component
    │   └── routes.py   # Leaf blueprint with actual handlers
    └── subfeature_b/
        └── routes.py
```

This structure creates a URL hierarchy like:
```
/                                    # Root
/feature_area/                       # Feature area index
/feature_area/subfeature_a/          # Subfeature routes
/feature_area/subfeature_b/
```

## Blueprint Pattern

### Creating a Blueprint

Each feature module defines its own blueprint:

```python
# webapp/feature_area/subfeature_a/routes.py
from flask import Blueprint, jsonify

# Create blueprint with a unique name
bp = Blueprint("subfeature_a", __name__)

@bp.route("/")
def index():
    """Subfeature landing page."""
    return jsonify({"message": "Subfeature A", "status": "active"})

@bp.route("/items")
def list_items():
    """List all items in this subfeature."""
    return jsonify({"items": ["item1", "item2", "item3"]})

@bp.route("/items/<int:item_id>")
def get_item(item_id):
    """Retrieve a specific item by ID."""
    return jsonify({"item_id": item_id, "name": f"Item {item_id}"})
```

### Registering Child Blueprints

Parent blueprints import and register child blueprints with URL prefixes:

```python
# webapp/feature_area/routes.py
from flask import Blueprint, jsonify
from .subfeature_a.routes import bp as subfeature_a_bp
from .subfeature_b.routes import bp as subfeature_b_bp

# Create parent blueprint
bp = Blueprint("feature_area", __name__)

@bp.route("/")
def index():
    """Feature area landing page."""
    return jsonify({
        "message": "Feature Area",
        "subfeatures": ["subfeature_a", "subfeature_b"]
    })

# Register child blueprints with URL prefixes
bp.register_blueprint(subfeature_a_bp, url_prefix="/subfeature-a")
bp.register_blueprint(subfeature_b_bp, url_prefix="/subfeature-b")
```

### Application Factory

The app factory registers top-level blueprints:

```python
# webapp/__init__.py
from flask import Flask
from .routes import bp as root_bp

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Register root blueprint (which includes nested blueprints)
    app.register_blueprint(root_bp, url_prefix="/feature_area")

    return app
```

### Application Entry Point

The entry point creates and runs the application:

```python
# run.py
import os
from webapp import create_app

app = create_app()

if __name__ == "__main__":
    host = os.environ.get("APP_HOST", "0.0.0.0")
    port = int(os.environ.get("APP_PORT", 8000))
    debug = os.environ.get("DEV_RELOAD", "0") == "1"

    app.run(host=host, port=port, debug=debug)
```

## Blueprint Benefits

### Clear Organization

Related code stays together:
```
auth/
├── routes.py         # Login, logout, register routes
├── models.py         # User model
└── templates/        # Auth-specific templates
    ├── login.html
    └── register.html
```

### URL Namespace Management

Blueprints create logical URL structures:
```python
# Register with different prefixes for versioning
app.register_blueprint(api_v1_bp, url_prefix="/api/v1")
app.register_blueprint(api_v2_bp, url_prefix="/api/v2")
```

### Independent Development

Teams can work on separate blueprints without conflicts:
```python
# Team A works on admin blueprint
from admin.routes import bp as admin_bp

# Team B works on API blueprint
from api.routes import bp as api_bp

# Both register independently
app.register_blueprint(admin_bp, url_prefix="/admin")
app.register_blueprint(api_bp, url_prefix="/api")
```

### Reusable Components

Create blueprint packages for common functionality:
```python
# Reusable auth blueprint
from auth_library import auth_bp

# Register in multiple applications
app.register_blueprint(auth_bp, url_prefix="/auth")
```

## Common Patterns

### Hierarchical Feature Organization

Group related features with parent blueprints:
```python
# webapp/api/routes.py
from flask import Blueprint
from .users.routes import bp as users_bp
from .posts.routes import bp as posts_bp
from .comments.routes import bp as comments_bp

bp = Blueprint("api", __name__)

bp.register_blueprint(users_bp, url_prefix="/users")
bp.register_blueprint(posts_bp, url_prefix="/posts")
bp.register_blueprint(comments_bp, url_prefix="/comments")
```

Result:
- `/api/users/`
- `/api/posts/`
- `/api/comments/`

### Blueprint-Specific Resources

Blueprints can have their own templates and static files:
```python
# Templates stored in blueprint directory
bp = Blueprint("admin", __name__,
               template_folder="templates",
               static_folder="static")

@bp.route("/dashboard")
def dashboard():
    # Looks for templates in admin/templates/
    return render_template("dashboard.html")
```

### Shared Logic with Before/After Request

Apply middleware to blueprint routes only:
```python
from flask import Blueprint, g
from .auth import require_admin

bp = Blueprint("admin", __name__)

@bp.before_request
def before_admin_request():
    """Run before every request to admin blueprint."""
    require_admin()

@bp.after_request
def after_admin_request(response):
    """Run after every admin response."""
    response.headers["X-Admin-Request"] = "true"
    return response

@bp.route("/")
def admin_index():
    # before_request and after_request automatically apply
    return "Admin Dashboard"
```

## Best Practices

### Naming Conventions

Use consistent, descriptive blueprint names:
```python
# ✅ Clear, descriptive names
bp = Blueprint("user_management", __name__)
bp = Blueprint("api_v2_posts", __name__)

# ❌ Vague or generic names
bp = Blueprint("routes", __name__)
bp = Blueprint("main", __name__)
```

### Import Aliases

Use consistent aliases to avoid naming conflicts:
```python
# Import with descriptive aliases
from .users.routes import bp as users_bp
from .posts.routes import bp as posts_bp
from .admin.routes import bp as admin_bp

# Register with clear prefixes
app.register_blueprint(users_bp, url_prefix="/users")
app.register_blueprint(posts_bp, url_prefix="/posts")
app.register_blueprint(admin_bp, url_prefix="/admin")
```

### URL Prefix Strategy

Design URL structure upfront:
```python
# Versioned API with nested resources
app.register_blueprint(api_bp, url_prefix="/api/v1")

# Inside api_bp, nested blueprints create:
# /api/v1/users/
# /api/v1/users/<id>
# /api/v1/posts/
# /api/v1/posts/<id>/comments
```

### Keep Blueprints Focused

Each blueprint should have a single, clear purpose:
```python
# ✅ Focused blueprint for user authentication
auth_bp = Blueprint("auth", __name__)
# Routes: /login, /logout, /register, /reset-password

# ✅ Focused blueprint for user profile management
profile_bp = Blueprint("profile", __name__)
# Routes: /profile, /profile/edit, /profile/settings

# ❌ Mixed concerns in one blueprint
user_stuff_bp = Blueprint("user_stuff", __name__)
# Routes: /login, /profile, /admin/users, /api/users (too broad)
```

## Adding New Features

To add a new feature area:

1. **Create feature directory**: `webapp/new_feature/`
2. **Add blueprint definition**: Create `routes.py` with `bp = Blueprint("new_feature", __name__)`
3. **Implement routes**: Add route handlers to the blueprint
4. **Register with parent**: Import and register in parent blueprint or app factory

Example:
```python
# 1. Create webapp/reporting/routes.py
from flask import Blueprint, jsonify

bp = Blueprint("reporting", __name__)

@bp.route("/")
def index():
    return jsonify({"available_reports": ["sales", "inventory", "users"]})

@bp.route("/<report_type>")
def generate_report(report_type):
    return jsonify({"report": report_type, "status": "generated"})

# 2. Register in webapp/__init__.py
from .reporting.routes import bp as reporting_bp

def create_app():
    app = Flask(__name__)
    app.register_blueprint(reporting_bp, url_prefix="/reports")
    return app
```

## Real-World Example Structure

A production application might organize blueprints like:

```
webapp/
├── __init__.py           # App factory
├── auth/                 # Authentication & authorization
│   ├── routes.py
│   └── middleware.py
├── api/                  # REST API
│   ├── routes.py         # API root blueprint
│   ├── v1/
│   │   ├── routes.py     # API v1 parent blueprint
│   │   ├── users/
│   │   ├── posts/
│   │   └── comments/
│   └── v2/
│       └── routes.py
├── admin/                # Admin panel
│   ├── routes.py
│   ├── dashboard/
│   ├── users/
│   └── settings/
└── public/               # Public-facing pages
    ├── routes.py
    ├── home/
    ├── about/
    └── contact/
```

This creates a clear URL structure:
```
/auth/login
/auth/logout
/api/v1/users/
/api/v1/posts/
/api/v2/users/
/admin/dashboard/
/admin/users/
/
/about
/contact
```

## Further Reading

- [Flask Blueprints Documentation](https://flask.palletsprojects.com/en/stable/blueprints/)
- [Flask Application Factories](https://flask.palletsprojects.com/en/stable/patterns/appfactories/)
- [Modular Applications with Blueprints](https://flask.palletsprojects.com/en/stable/tutorial/views/)
- [Blueprint Template and Static Files](https://flask.palletsprojects.com/en/stable/blueprints/#blueprint-resources)

## See Also

For working examples of blueprint organization in this project:
- [Flask Confusion Examples](../../../vulnerabilities/python/flask/confusion/) - Demonstrates hierarchical blueprint structure with nested feature areas
