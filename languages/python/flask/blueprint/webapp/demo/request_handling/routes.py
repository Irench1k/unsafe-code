from flask import Blueprint

# Simple request handling examples
bp = Blueprint("request_handling", __name__)

@bp.route("/")
def index():
    return "Request handling examples\n"
