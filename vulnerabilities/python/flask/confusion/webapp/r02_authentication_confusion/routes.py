from flask import Blueprint

from .e01_session_hijack import bp as bp_e01
from .e02_credit_top_ups import bp as bp_e02
from .e03_fake_header_refund import bp as bp_e03

bp = Blueprint("authentication_confusion", __name__)


@bp.route("/")
def index():
    return "Authentication Confusion vulnerability examples\n"


bp.register_blueprint(bp_e01, url_prefix="v201")
bp.register_blueprint(bp_e02, url_prefix="v202")
bp.register_blueprint(bp_e03, url_prefix="v203")
