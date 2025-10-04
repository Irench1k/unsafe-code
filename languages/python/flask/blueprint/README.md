# Flask Blueprint Example

A Flask application demonstrating hierarchical routing with [Blueprints](https://flask.palletsprojects.com/en/stable/api/#flask.Blueprint) - organized, scalable, and beginner-friendly.

## Quick Start

```bash
cd languages/python/flask/blueprint
docker compose up -d

# Test the hierarchical structure
curl http://localhost:8000/demo/routing/basic-routes/
curl http://localhost:8000/vuln/type-issues/

# Stop and clean up
docker compose down
```

## Project Structure

```
run.py              # Application entry point
webapp/             # Main application package (standardized name)
├── __init__.py     # App factory with main blueprint registration
# Removed utils.py - explicit Blueprint() calls are clearer
├── demo/           # Demo examples section
│   ├── routes.py   # Demo section blueprint
│   ├── routing/
│   │   ├── routes.py          # Routing examples blueprint
│   │   ├── basic_routes/      # Basic routing examples
│   │   ├── parametric_routes/ # URL parameter examples
│   │   └── route_constraints/ # Route constraint examples
│   ├── request_handling/      # Request handling examples
│   └── response_handling/     # Response handling examples
└── vuln/           # Vulnerability examples section
    ├── routes.py   # Vulnerability section blueprint
    ├── confusion/  # Confusion-based vulnerabilities
    ├── type_issues/ # Type-related vulnerabilities
    └── state_management/ # State management issues
```

## Blueprint Pattern

Each route module follows a simple, consistent pattern:

```python
# webapp/demo/routing/basic_routes/routes.py
from flask import Blueprint

# Create blueprint - explicit and clear
bp = Blueprint("basic_routes", __name__)

@bp.route("/")
def index():
    return "Basic routing examples\n"

# Add your routes
@bp.route("/example")
def example_route():
    return "Example response"
```

For blueprints with children:

```python
# webapp/demo/routes.py
from flask import Blueprint
from .routing.routes import bp as routing_bp
from .request_handling.routes import bp as request_handling_bp

# Create parent blueprint
bp = Blueprint("demo", __name__)

@bp.route("/")
def index():
    return "Demo examples - try /routing, /request-handling\n"

# Register children - explicit and clear
bp.register_blueprint(routing_bp, url_prefix="/routing")
bp.register_blueprint(request_handling_bp, url_prefix="/request-handling")
```

## Adding New Examples

Adding new examples is straightforward:

1. **Create directory**: `webapp/demo/new_feature/`
2. **Add routes.py**: `bp = Blueprint("new_feature", __name__)`
3. **Update parent**: Add import and registration in parent's `routes.py`

The explicit pattern scales easily to hundreds of examples while staying readable and debuggable.
