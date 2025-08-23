from flask import Blueprint

# Confusion-based vulnerability examples
bp = Blueprint("confusion", __name__)

@bp.route("/")
def index():
    return "Confusion vulnerability examples\n"
