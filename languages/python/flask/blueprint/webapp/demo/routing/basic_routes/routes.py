from flask import Blueprint

# Basic routing examples
bp = Blueprint("basic_routes", __name__)

@bp.route("/")
def index():
    return "Basic routing examples\n"
