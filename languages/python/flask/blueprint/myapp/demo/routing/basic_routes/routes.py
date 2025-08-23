from flask import Blueprint

bp = Blueprint("basic_bp", __name__)


@bp.route("/")
def index():
    return "Blueprint at /demo/routing/basic_routes directory \n"
