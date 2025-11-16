from flask import Blueprint

from .e01_dual_auth_refund import bp as v301

bp = Blueprint("authorization_confusion", __name__)


@bp.route("/")
def index():
    return "Authorization Confusion vulnerability examples\n"


bp.register_blueprint(v301, url_prefix="v301")
