from flask import Blueprint

# from .confusion.routes import bp as confusion_bp
from .ii.routes import bp as ii_bp

# Create vulnerability examples blueprint
bp = Blueprint("vuln", __name__)

@bp.route("/")
def index():
    return "Vulnerability examples - try /confusion, /type-issues, /state-management, /ii\n"

bp.register_blueprint(ii_bp, url_prefix="/ii")
