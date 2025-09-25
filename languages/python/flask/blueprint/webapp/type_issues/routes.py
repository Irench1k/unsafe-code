from flask import Blueprint

# Type-related vulnerability examples
bp = Blueprint("type_issues", __name__)

@bp.route("/")
def index():
    return "Type issue vulnerability examples\n"
