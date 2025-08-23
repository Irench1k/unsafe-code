from flask import Flask
# Explicit blueprint imports - clear and debuggable
from .demo.routes import bp as demo_bp
from .vuln.routes import bp as vuln_bp


def create_app():
    """Create Flask app with blueprint-based routing."""
    app = Flask(__name__)

    @app.route("/")
    def index():
        return "Flask Blueprint Example - visit /demo or /vuln\n"

    # Register main feature blueprints
    app.register_blueprint(demo_bp, url_prefix="/demo")
    app.register_blueprint(vuln_bp, url_prefix="/vuln")

    return app
