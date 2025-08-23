from flask import Blueprint

bp = Blueprint("type_issues_bp", __name__)


@bp.route("/")
def index():
    return "Blueprint at /demo/type_issues directory \n"
