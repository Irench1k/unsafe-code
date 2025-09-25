from flask import Blueprint
from .confusion.routes import bp as confusion_bp
from .type_issues.routes import bp as type_issues_bp
from .state_management.routes import bp as state_management_bp

# Create vulnerability examples blueprint
bp = Blueprint("vuln", __name__)

@bp.route("/")
def index():
    return "Vulnerability examples - try /confusion, /type-issues, /state-management\n"

# Register child blueprints - explicit but clean  
bp.register_blueprint(confusion_bp, url_prefix="/confusion")
bp.register_blueprint(type_issues_bp, url_prefix="/type-issues")
bp.register_blueprint(state_management_bp, url_prefix="/state-management")
