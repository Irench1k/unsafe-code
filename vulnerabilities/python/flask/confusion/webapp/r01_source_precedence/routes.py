from flask import Blueprint

from .e00_intro.routes import bp as intro_bp
from .e04_cross_module.routes import bp as cross_module_bp
from .e05_truthy_or.routes import bp as truthy_or_bp
from .e06_dict_get_default.routes import bp as dict_get_default_bp
from .e07_request_values.routes import bp as request_values_bp
from .e08_inconsistent_adoption.routes import bp as inconsistent_adoption_bp

bp = Blueprint("source_precedence", __name__)


@bp.route("/")
def index():
    return "Source Precedence vulnerability examples\n"


# Register sub-blueprints
bp.register_blueprint(intro_bp)
bp.register_blueprint(cross_module_bp)
bp.register_blueprint(truthy_or_bp)
bp.register_blueprint(dict_get_default_bp)
bp.register_blueprint(request_values_bp)
bp.register_blueprint(inconsistent_adoption_bp)
