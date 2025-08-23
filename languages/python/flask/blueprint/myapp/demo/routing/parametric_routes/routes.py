from flask import Blueprint

bp = Blueprint("parametric_bp", __name__)


@bp.route("/")
def index():
    return "Blueprint at /demo/routing/parametric_routes directory \n"
