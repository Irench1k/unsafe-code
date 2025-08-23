from flask import Blueprint
from .routing import blueprint


bp = Blueprint("demo_bp", __name__)
bp.register_blueprint(blueprint.bp, url_prefix="/routing")


@bp.route("/")
def index():
    return "Blueprint at /demo directory \n"
