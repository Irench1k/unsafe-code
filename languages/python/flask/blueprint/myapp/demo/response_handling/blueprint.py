from flask import Blueprint

bp = Blueprint("response_handling_bp", __name__)


@bp.route("/")
def index():
    return "Blueprint at /demo/response_handling directory \n"
