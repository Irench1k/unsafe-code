from flask import Blueprint

bp = Blueprint("constraints_bp", __name__)


@bp.route("/")
def index():
    return "3️⃣ Blueprint at /demo/routing/route_constraints directory \n"
