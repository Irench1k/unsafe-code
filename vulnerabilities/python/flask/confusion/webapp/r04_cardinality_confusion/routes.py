from flask import Blueprint

from .e01_coupon_stacking import bp as v401
from .e02_zero_quantity import bp as v402
from .e03_duplicate_coupons import bp as v403
from .e04_batch_refund_bypass import bp as v404
from .e05_two_ids_bypass import bp as v405

bp = Blueprint("cardinality_confusion", __name__)


@bp.route("/")
def index():
    return "Cardinality Confusion vulnerability examples\n"


bp.register_blueprint(v401, url_prefix="v401")
bp.register_blueprint(v402, url_prefix="v402")
bp.register_blueprint(v403, url_prefix="v403")
bp.register_blueprint(v404, url_prefix="v404")
bp.register_blueprint(v405, url_prefix="v405")
