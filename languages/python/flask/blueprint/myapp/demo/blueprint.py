from flask import Blueprint
from .routing import blueprint as routing_bp
from .request_handling import blueprint as request_handling_bp
from .response_handling import blueprint as response_handling_bp

bp = Blueprint("demo_bp", __name__)
bp.register_blueprint(routing_bp.bp, url_prefix="/routing")
bp.register_blueprint(request_handling_bp.bp, url_prefix="/request-handling")
bp.register_blueprint(response_handling_bp.bp, url_prefix="/response-handling")


@bp.route("/")
def index():
    return "Blueprint at /demo directory \n"
