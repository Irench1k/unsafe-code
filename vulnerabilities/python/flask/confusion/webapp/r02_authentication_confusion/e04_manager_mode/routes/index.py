from flask import Blueprint

bp = Blueprint("index", __name__)


@bp.route("/")
def index():
    return "R02: Authentication Confusion - Manager Mode\n"
