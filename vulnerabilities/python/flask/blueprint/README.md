# Flask Blueprint Example

A Flask application demonstrating hierarchical routing with [Blueprints](https://flask.palletsprojects.com/en/stable/api/#flask.Blueprint) for vulnerability research and education.

## Quick Start

```bash
cd languages/python/flask/blueprint
docker compose up -d

# Test the hierarchical structure
curl http://localhost:8000/ii/

# Stop and clean up
docker compose down
```

## Project Structure

```
run.py              # Application entry point
webapp/             # Main application package
├── __init__.py     # App factory
├── routes.py       # Root blueprint registration
└── r01_ii/         # Inconsistent Interpretation (II) vulnerabilities
    ├── routes.py   # II section blueprint
    ├── r01_source_precedence/           # Source precedence confusion
    ├── r02_cross_component_parse/       # Cross-component parsing issues
    ├── r03_authz_binding/               # Authorization binding vulnerabilities
    ├── r04_http_semantics/              # HTTP semantics confusion
    ├── r05_multi_value_semantics/       # Multi-value handling issues
    └── r06_normalization_canonicalization/  # Normalization mismatches
```

## Blueprint Pattern

Each vulnerability example follows a consistent pattern:

```python
# webapp/r01_ii/r01_source_precedence/routes.py
from flask import Blueprint

bp = Blueprint("source_precedence", __name__)

@bp.route("/")
def index():
    return "Source precedence examples\n"

@bp.route("/example-1")
def example_1():
    # Vulnerable code demonstrating the issue
    pass
```

Parent blueprints register children:

```python
# webapp/r01_ii/routes.py
from flask import Blueprint
from .r01_source_precedence.routes import bp as source_precedence_bp

bp = Blueprint("ii", __name__)

@bp.route("/")
def index():
    return "Inconsistent Interpretation (II) examples\n"

bp.register_blueprint(source_precedence_bp, url_prefix="/source-precedence")
```

## Adding New Examples

1. **Create directory**: `webapp/r01_ii/new_category/`
2. **Add routes.py**: `bp = Blueprint("new_category", __name__)`
3. **Update parent**: Import and register in `webapp/r01_ii/routes.py`
