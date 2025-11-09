from flask import Blueprint

from .e00_baseline.routes import bp as bp_e00
from .e01_dual_parameters.routes import bp as bp_e01

bp = Blueprint("input_source_confusion", __name__)


@bp.route("/")
def index():
    return "Input Source vulnerability examples\n"


bp.register_blueprint(bp_e00, url_prefix="/e00-baseline")
bp.register_blueprint(bp_e01, url_prefix="/e01-dual-parameters")
