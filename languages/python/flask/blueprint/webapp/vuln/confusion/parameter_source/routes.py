from flask import Blueprint

# Confusion-based vulnerability examples
bp = Blueprint("parameter_source", __name__)

@bp.route("/")
def index():
    return "Parameter source confusion vulnerability examples\n"
