from flask import Blueprint

# Parametric routing examples
bp = Blueprint("parametric_routes", __name__)

@bp.route("/")
def index():
    return "Parametric routing examples\n"
