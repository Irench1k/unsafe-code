from flask import Blueprint

bp = Blueprint("request_handling_bp", __name__)


@bp.route("/")
def index():
    return "Blueprint at /demo/request_handling directory \n"
