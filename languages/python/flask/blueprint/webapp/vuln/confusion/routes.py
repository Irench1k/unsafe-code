from flask import Blueprint
from .parameter_source.routes import bp as parameter_source_bp

# Confusion-based vulnerability examples
bp = Blueprint("confusion", __name__)

@bp.route("/")
def index():
    return "Confusion vulnerability examples\n"

bp.register_blueprint(parameter_source_bp, url_prefix="/parameter-source")
