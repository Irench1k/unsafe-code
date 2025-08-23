from flask import Blueprint
from .confusion import blueprint as confusion_bp
from .type_issues import blueprint as type_issues_bp
from .state_management import blueprint as state_management_bp

bp = Blueprint("vuln_bp", __name__)
bp.register_blueprint(confusion_bp.bp, url_prefix="/confusion")
bp.register_blueprint(type_issues_bp.bp, url_prefix="/type-issues")
bp.register_blueprint(state_management_bp.bp, url_prefix="/state-management")


@bp.route("/")
def index():
    return "Blueprint at /vuln directory \n"
