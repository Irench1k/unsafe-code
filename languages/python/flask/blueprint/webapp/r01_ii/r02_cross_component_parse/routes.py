from flask import Blueprint
from .r01_baseline.routes import bp as baseline_bp
from .r02_decorator_drift.routes import bp as decorator_drift_bp
from .r03_middleware_drift.routes import bp as middleware_drift_bp

# Cross-Component Parsing Drift vulnerability examples
bp = Blueprint("cross_component_parse", __name__)

# Register child blueprints
bp.register_blueprint(baseline_bp)
bp.register_blueprint(decorator_drift_bp)
bp.register_blueprint(middleware_drift_bp)


@bp.route("/")
def index():
    return "Cross-Component Parsing Drift vulnerability examples\n"
