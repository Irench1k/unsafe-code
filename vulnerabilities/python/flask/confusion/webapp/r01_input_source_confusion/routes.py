from flask import Blueprint

from .e00_baseline.routes import bp as bp_e00
from .e01_dual_parameter.routes import bp as bp_e01
from .e02_delivery_fee.routes import bp as bp_e02
from .e03_order_overwrite.routes import bp as bp_e03
from .e04_negative_tip.routes import bp as bp_e04

bp = Blueprint("input_source_confusion", __name__)


@bp.route("/")
def index():
    return "Input Source vulnerability examples\n"


bp.register_blueprint(bp_e00, url_prefix="v100")
bp.register_blueprint(bp_e01, url_prefix="v101")
bp.register_blueprint(bp_e02, url_prefix="v102")
bp.register_blueprint(bp_e03, url_prefix="v103")
bp.register_blueprint(bp_e04, url_prefix="v104")
