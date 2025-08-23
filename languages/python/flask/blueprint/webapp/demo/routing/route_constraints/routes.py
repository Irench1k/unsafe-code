from flask import Blueprint

# Route constraint examples
bp = Blueprint("route_constraints", __name__)

@bp.route("/")
def index():
    return "Route constraint examples\n"
