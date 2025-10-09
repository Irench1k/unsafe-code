from flask import Blueprint

from .e0103_intro.routes import bp as intro_bp
from .e04_cross_module.routes import bp as cross_module_bp
from .e05_mixed_source.routes import bp as mixed_source_bp
from .e06_destructive.routes import bp as destructive_bp
from .e07_form_bypass.routes import bp as form_bypass_bp
from .e08_password_reset.routes import bp as password_reset_bp

bp = Blueprint("source_precedence", __name__)


@bp.route("/")
def index():
    return "Source Precedence vulnerability examples\n"


# Register sub-blueprints
bp.register_blueprint(intro_bp)
bp.register_blueprint(cross_module_bp)
bp.register_blueprint(mixed_source_bp)
bp.register_blueprint(destructive_bp)
bp.register_blueprint(form_bypass_bp)
bp.register_blueprint(password_reset_bp)
