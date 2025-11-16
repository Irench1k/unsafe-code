from flask import Blueprint

from .r01_input_source_confusion.routes import bp as input_source_confusion_bp
from .r02_authentication_confusion.routes import bp as authentication_confusion_bp
from .r03_authorization_confusion.routes import bp as authorization_confusion_bp

# Main blueprint
bp = Blueprint("confusion", __name__, url_prefix="/api")


@bp.route("/")
def index():
    return "Flask Confusion - NEW vulnerability examples\n"


# Register child blueprints
bp.register_blueprint(input_source_confusion_bp)
bp.register_blueprint(authentication_confusion_bp)
bp.register_blueprint(authorization_confusion_bp)
