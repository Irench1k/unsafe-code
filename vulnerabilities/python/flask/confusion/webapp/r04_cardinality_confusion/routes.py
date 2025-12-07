from flask import Blueprint

from .e01_coupon_stacking import bp as v401
from .e02_zero_quantity import bp as v402

bp = Blueprint("cardinality_confusion", __name__)


@bp.route("/")
def index():
    return "Cardinality Confusion vulnerability examples\n"


bp.register_blueprint(v401, url_prefix="v401")
bp.register_blueprint(v402, url_prefix="v402")
