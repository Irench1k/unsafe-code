from flask import Blueprint
from .routing.routes import bp as routing_bp
from .request_handling.routes import bp as request_handling_bp 
from .response_handling.routes import bp as response_handling_bp

# Create demo blueprint
bp = Blueprint("demo", __name__)

@bp.route("/")
def index():
    return "Demo examples - try /routing, /request-handling, /response-handling\n"

# Register child blueprints - explicit but clean
bp.register_blueprint(routing_bp, url_prefix="/routing")
bp.register_blueprint(request_handling_bp, url_prefix="/request-handling")
bp.register_blueprint(response_handling_bp, url_prefix="/response-handling")
