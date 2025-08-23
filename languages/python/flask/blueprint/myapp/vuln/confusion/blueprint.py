from flask import Blueprint

bp = Blueprint("confusion_bp", __name__)


@bp.route("/")
def index():
    return "Blueprint at /demo/confusion directory \n"
