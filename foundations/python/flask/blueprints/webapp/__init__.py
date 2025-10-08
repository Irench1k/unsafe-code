"""
Flask Blueprints Example - Application Factory Pattern

Blueprints solve several practical problems in Flask applications:

1. NAMESPACE ISOLATION: Multiple modules can define routes with the same function
   names (e.g., index(), list(), detail()) without conflicts. Flask uses the
   blueprint name as a namespace prefix for endpoints.

2. MODULAR ORGANIZATION: Each feature area (users, posts, admin) is self-contained
   in its own module with clear URL prefixes and route definitions.

3. REUSABILITY: Blueprints can be registered multiple times with different URL
   prefixes or configuration, enabling patterns like versioned APIs.

4. APPLICATION FACTORY: The create_app() pattern (shown here) enables better
   testing, multiple app instances, and late configuration binding.

Compare this to foundations/python/flask/routing-multifile-register/ which
requires manual endpoint naming ('admin.list_users') to avoid collisions.
Blueprints handle this automatically.
"""
from flask import Flask


def create_app():
    """
    Application factory: creates and configures a Flask app instance.

    Benefits for security auditors:
    - Enables testing multiple configurations without global state
    - Shows initialization order (important for middleware/hook analysis)
    - Makes blueprint registration explicit and auditable
    """
    app = Flask(__name__)

    # Register blueprints with URL prefixes
    # Each blueprint acts as a namespace for routes and templates
    from .users.routes import users_bp
    from .posts.routes import posts_bp
    from .admin.routes import admin_bp

    # URL prefixes define the routing hierarchy
    # These become the base path for all routes in each blueprint
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(posts_bp, url_prefix='/posts')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Root route for basic app info
    @app.route('/')
    def index():
        """Show available blueprint routes."""
        return {
            "app": "Flask Blueprints Example",
            "endpoints": {
                "users": "/users/",
                "posts": "/posts/",
                "admin": "/admin/"
            }
        }

    return app
