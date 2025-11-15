from flask import Blueprint

from .e00_baseline.routes import bp as bp_e00
from .e01_dual_parameter.routes import bp as bp_e01
from .e02_delivery_fee.routes import bp as bp_e02
from .e03_order_overwrite.routes import bp as bp_e03
from .e04_negative_tip.routes import bp as bp_e04
from .e05_unlimited_refund.routes import bp as bp_e05
from .e06_signup_token_swap.routes import bp as bp_e06
from .e07_signup_bonus import bp as bp_e07
from .e08_fixed_final_version import bp as bp_e08

bp = Blueprint("input_source_confusion", __name__)


@bp.route("/")
def index():
    return "Input Source vulnerability examples\n"


bp.register_blueprint(bp_e00, url_prefix="v100")
bp.register_blueprint(bp_e01, url_prefix="v101")
bp.register_blueprint(bp_e02, url_prefix="v102")
bp.register_blueprint(bp_e03, url_prefix="v103")
bp.register_blueprint(bp_e04, url_prefix="v104")
bp.register_blueprint(bp_e05, url_prefix="v105")
bp.register_blueprint(bp_e06, url_prefix="v106")
bp.register_blueprint(bp_e07, url_prefix="v107")
bp.register_blueprint(bp_e08, url_prefix="v108")
