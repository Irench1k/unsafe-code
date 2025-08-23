from flask import Blueprint

bp = Blueprint("basic_bp", __name__)


@bp.route("/")
def index():
    return "3️⃣ Blueprint at /demo/routing/basic_routing directory \n"
