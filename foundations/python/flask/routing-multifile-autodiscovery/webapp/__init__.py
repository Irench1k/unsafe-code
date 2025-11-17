import importlib
import pkgutil

from flask import Flask


def create_app():
    """Application factory with automatic route discovery.
    
    This example demonstrates automatic route discovery using importlib and pkgutil.
    Routes can be registered in two ways:
    
    1. Blueprint approach: Define 'bp' variable in routes.py
    2. Function approach: Define 'register(app)' function in routes.py
    """
    app = Flask(__name__)

    # Auto-discover and register route modules
    _auto_discover_routes(app)

    return app

def _auto_discover_routes(app):
    """Automatically discover and register routes from subpackages.
    
    Scans all subpackages in the current package for route modules.
    Each routes.py can either:
    - Export a 'bp' Blueprint that will be registered
    - Export a 'register(app)' function that will be called
    """
    import webapp

    for _finder, name, ispkg in pkgutil.iter_modules(webapp.__path__):
        if not ispkg:  # Skip non-packages
            continue

        try:
            # Try to import the routes module from each subpackage
            routes_module = importlib.import_module(f'webapp.{name}.routes')
        except ModuleNotFoundError:
            # No routes.py in this subpackage, skip it
            continue

        # Register routes using blueprint or register function
        if hasattr(routes_module, 'bp'):
            app.register_blueprint(routes_module.bp)
            print(f"✓ Registered blueprint from {name}.routes")

        elif hasattr(routes_module, 'register'):
            routes_module.register(app)
            print(f"✓ Registered routes from {name}.routes using register()")

        else:
            print(f"⚠ Module {name}.routes found but no 'bp' or 'register' to use")

# Create the app instance
app = create_app()
