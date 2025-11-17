from flask import Flask

# This example demonstrates manual route registration without Blueprints.
#
# 🔄 FOR LARGER APPS, CONSIDER:
# - Flask Blueprints (recommended)
# - Application Factory pattern with create_app()
# - Class-based views for complex route logic

app = Flask(__name__)

# === Route Registration ===

# Example 1: Function-based route registration (users/routes.py)
from .users import routes as users_routes

users_routes.register(app)

# Example 2: Decorator-based route registration (posts/routes.py)
from .posts import routes as posts_routes

posts_routes.register(app)

# Example 3: Function-based routes with consistent prefixes (admin/routes.py)
from .admin import routes as admin_routes

admin_routes.register(app, prefix='/admin')

# Example 4: Decorator-based routes with consistent prefixes (api/routes.py)
from .api import routes as api_routes

api_routes.register(app, prefix='/api/v1')
