from flask import Blueprint

from .r01_merge_order_and_short_circuit.routes import bp as merge_order_bp

# Policy Composition and Precedence vulnerability examples
bp = Blueprint("policy_composition_and_precedence", __name__)

# Register child blueprints
bp.register_blueprint(merge_order_bp, url_prefix="/merge-order-and-short-circuit")


@bp.route("/")
def index():
    return "Policy Composition and Precedence vulnerability examples\n"
