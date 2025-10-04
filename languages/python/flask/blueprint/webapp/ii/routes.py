from flask import Blueprint

from .r01_source_precedence.routes import bp as source_precedence_bp
from .r02_cross_component_parse.routes import bp as cross_component_parse_bp
from .r03_authz_binding.routes import bp as authz_binding_bp
from .r04_multi_value_semantics.routes import bp as multi_value_semantics_bp
from .r05_http_semantics.routes import bp as http_semantics_bp
from .r06_normalization_canonicalization.routes import (
    bp as normalization_canonicalization_bp,
)

# Inconsistent Interpretation vulnerability examples
bp = Blueprint("ii", __name__)


@bp.route("/")
def index():
    return "Inconsistent Interpretation (II) vulnerability examples\n"


# Register child blueprints - explicit but clean
bp.register_blueprint(source_precedence_bp, url_prefix="/source-precedence")
bp.register_blueprint(multi_value_semantics_bp, url_prefix="/multi-value-semantics")
bp.register_blueprint(authz_binding_bp, url_prefix="/authz-binding")
bp.register_blueprint(cross_component_parse_bp, url_prefix="/cross-component-parse")
bp.register_blueprint(http_semantics_bp, url_prefix="/http-semantics")
bp.register_blueprint(
    normalization_canonicalization_bp, url_prefix="/normalization-canonicalization"
)
