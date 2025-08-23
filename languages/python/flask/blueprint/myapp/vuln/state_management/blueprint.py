from flask import Blueprint

bp = Blueprint("state_management_bp", __name__)


@bp.route("/")
def index():
    return "Blueprint at /demo/state_management directory \n"
