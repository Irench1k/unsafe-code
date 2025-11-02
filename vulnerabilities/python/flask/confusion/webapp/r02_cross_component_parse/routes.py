from flask import Blueprint

from .e01_baseline.routes import bp as baseline_bp
from .e02_middleware.routes import bp as middleware_bp
from .e03_decorator.routes import bp as decorator_bp
from .e04_decorator_2.routes import bp as decorator_2_bp
from .e05_basic_auth.routes import bp as basic_auth_bp
from .e06_error_handler.routes import bp as error_handler_bp

bp = Blueprint("cross_component_parse", __name__)


@bp.route("/")
def index():
    return "Source Precedence vulnerability examples\n"


# Register sub-blueprints
bp.register_blueprint(baseline_bp)
bp.register_blueprint(middleware_bp)
bp.register_blueprint(decorator_bp)
bp.register_blueprint(decorator_2_bp)
bp.register_blueprint(error_handler_bp)
bp.register_blueprint(basic_auth_bp)
