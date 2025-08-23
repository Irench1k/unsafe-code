from flask import Blueprint
from .basic_routes.routes import bp as basic_routes_bp
from .parametric_routes.routes import bp as parametric_routes_bp
from .route_constraints.routes import bp as route_constraints_bp

# Create routing examples blueprint
bp = Blueprint("routing", __name__)

@bp.route("/")
def index():
    return "Routing examples - try /basic-routes, /parametric-routes, /route-constraints\n"

# Register child blueprints - explicit but clean
bp.register_blueprint(basic_routes_bp, url_prefix="/basic-routes")
bp.register_blueprint(parametric_routes_bp, url_prefix="/parametric-routes")
bp.register_blueprint(route_constraints_bp, url_prefix="/route-constraints")
