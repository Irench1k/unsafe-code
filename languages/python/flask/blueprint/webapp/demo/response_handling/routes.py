from flask import Blueprint

# Simple response handling examples  
bp = Blueprint("response_handling", __name__)

@bp.route("/")
def index():
    return "Response handling examples\n"
