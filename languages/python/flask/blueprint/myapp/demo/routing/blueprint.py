from flask import Blueprint
from .basic_routes import blueprint_basic
from .parametric_routes import blueprint_parametric
from .route_constraints import blueprint_const

bp = Blueprint("routing_bp", __name__)
bp.register_blueprint(blueprint_basic.bp, url_prefix="/basic")
bp.register_blueprint(blueprint_parametric.bp, url_prefix="/parametric")
bp.register_blueprint(blueprint_const.bp, url_prefix="/constraints")


@bp.route("/")
def index():
    return "2️⃣ Blueprint at /demo/routing directory \n"
