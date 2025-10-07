from flask import Blueprint

# Create vulnerability examples blueprint
bp = Blueprint("vuln", __name__)

@bp.route("/")
def index():
    return "Vulnerability examples - work in progress\n"
