from flask import Blueprint

# State management vulnerability examples
bp = Blueprint("state_management", __name__)

@bp.route("/")
def index():
    return "State management vulnerability examples\n"
