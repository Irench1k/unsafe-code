from flask import Blueprint
from .basic_routes import routes as basic_routes_bp
from .parametric_routes import routes as parametric_routes_bp
from .route_constraints import routes as route_constraints_bp

bp = Blueprint("routing_bp", __name__)
bp.register_blueprint(basic_routes_bp.bp, url_prefix="/basic-routes")
bp.register_blueprint(parametric_routes_bp.bp, url_prefix="/parametric-routes")
bp.register_blueprint(route_constraints_bp.bp, url_prefix="/route-constraints")


@bp.route("/")
def index():
    return "Blueprint at /demo/routing directory \n"
