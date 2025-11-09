from flask import Flask
from .routes import bp


def create_app():
    """Create Flask app with blueprint-based routing."""
    app = Flask(__name__)

    # Register API routes
    app.register_blueprint(bp)

    return app
