from flask import Blueprint

from .e01_session_hijack import bp as bp_e01

bp = Blueprint("authentication_confusion", __name__)


@bp.route("/")
def index():
    return "Authentication Confusion vulnerability examples\n"


bp.register_blueprint(bp_e01, url_prefix="v201")
