from flask import Flask
from .routes import bp


def create_app():
    """Create Flask app with blueprint-based routing."""
    app = Flask(__name__)

    # Register main feature blueprints
    app.register_blueprint(bp)

    return app
