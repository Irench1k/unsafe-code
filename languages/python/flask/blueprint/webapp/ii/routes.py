from flask import Blueprint

from .behavior_order.routes import bp as behavior_order_bp
from .http_semantics.routes import bp as http_semantics_bp
from .multi_value_semantics.routes import bp as multi_value_semantics_bp
from .normalization_canonicalization.routes import (
    bp as normalization_canonicalization_bp,
)
from .source_precedence.routes import bp as source_precedence_bp

# Inconsistent Interpretation vulnerability examples
bp = Blueprint("ii", __name__)


@bp.route("/")
def index():
    return "Inconsistent Interpretation (II) vulnerability examples\n"


# Register child blueprints - explicit but clean
bp.register_blueprint(source_precedence_bp, url_prefix="/source-precedence")
bp.register_blueprint(multi_value_semantics_bp, url_prefix="/multi-value-semantics")
bp.register_blueprint(behavior_order_bp, url_prefix="/behavior-order")
bp.register_blueprint(http_semantics_bp, url_prefix="/http-semantics")
bp.register_blueprint(
    normalization_canonicalization_bp, url_prefix="/normalization-canonicalization"
)
