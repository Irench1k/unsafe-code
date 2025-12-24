import uuid

from flask import Flask

from .routes import bp


def create_app():
    """Create Flask app with blueprint-based routing."""
    app = Flask(__name__)
    app.secret_key = uuid.uuid4().hex

    # Register API routes
    app.register_blueprint(bp)

    return app
