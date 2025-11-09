from flask import Blueprint

from .r01_input_source_confusion.routes import bp as input_source_confusion_bp

# Main blueprint
bp = Blueprint("confusion", __name__, url_prefix="/api")


@bp.route("/")
def index():
    return "Flask Confusion - NEW vulnerability examples\n"


# Register child blueprints
bp.register_blueprint(input_source_confusion_bp)
